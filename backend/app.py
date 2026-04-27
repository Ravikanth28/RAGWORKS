"""
Smart Parking Slot Booker MCP — Flask Backend (v2 Refactored)
--------------------------------------------------------------
Main application entry point.

All business logic is delegated to the agent / service layers:
  • SlotAgent      — location & slot queries
  • BookingAgent   — booking & release operations
  • AgentOrchestrator + NLPAgent — natural-language endpoint

Use ``create_app()`` to obtain a configured Flask instance.
This factory pattern makes the app fully testable without touching
the real data file.

Usage (development):
    python app.py
    # → http://localhost:5000

Usage (tests):
    from app import create_app
    app = create_app(data_file=Path("tmp_data.json"))
"""

from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

from agents.booking_agent import BookingAgent
from agents.nlp_agent import AgentOrchestrator, NLPAgent
from agents.slot_agent import SlotAgent
from mcp.guardrails import Guardrails
from mcp.rag_module import RAGModule
from services.booking_service import BookingService
from services.slot_service import SlotService
from utils.config import Config
from utils.logger import generate_trace_id, get_logger


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(
    data_file: Optional[Path] = None,
    knowledge_file: Optional[Path] = None,
) -> Flask:
    """
    Create and configure a Flask application instance.

    Dependency injection via parameters makes the application
    fully testable — pass temporary files in tests.

    Parameters
    ----------
    data_file:
        Path to ``parking_data.json``.  Defaults to ``Config.DATA_FILE``.
    knowledge_file:
        Path to ``parking_knowledge.json``.  Defaults to
        ``Config.KNOWLEDGE_FILE``.

    Returns
    -------
    Flask
        Configured Flask application.
    """
    app = Flask(__name__)
    CORS(app)

    logger = get_logger("app")

    # ------------------------------------------------------------------
    # Wire up services, guardrails, and agents
    # ------------------------------------------------------------------
    _slot_service    = SlotService(data_file or Config.DATA_FILE)
    _booking_service = BookingService(_slot_service)
    _guardrails      = Guardrails()
    _rag             = RAGModule(knowledge_file)

    _slot_agent    = SlotAgent(_slot_service, _guardrails)
    _booking_agent = BookingAgent(_booking_service, _slot_service, _guardrails)
    _nlp_agent     = NLPAgent(_guardrails, _rag)
    _orchestrator  = AgentOrchestrator(
        _nlp_agent, _booking_agent, _slot_agent, _guardrails
    )

    # ------------------------------------------------------------------
    # API Routes
    # ------------------------------------------------------------------

    @app.route("/api/locations", methods=["GET"])
    def api_get_locations():
        """GET /api/locations — Return all locations with availability."""
        trace_id = generate_trace_id()
        get_logger("app", trace_id).info("GET /api/locations")
        return jsonify(_slot_agent.get_locations(trace_id))

    @app.route("/api/slots", methods=["GET"])
    def api_get_slots():
        """GET /api/slots?location=<id> — Return slots for a location."""
        trace_id    = generate_trace_id()
        location_id = request.args.get("location")
        get_logger("app", trace_id).info(f"GET /api/slots?location={location_id}")

        if not location_id:
            return jsonify({"error": "Missing 'location' query parameter"}), 400

        result = _slot_agent.get_slots(location_id, trace_id)
        if "error" in result:
            return jsonify(result), 404
        return jsonify(result)

    @app.route("/api/book", methods=["POST"])
    def api_book_slot():
        """POST /api/book — Book an available parking slot."""
        trace_id = generate_trace_id()
        data     = request.get_json() or {}

        location_id = data.get("location")
        duration    = data.get("duration")
        slot_id     = data.get("slot_id")

        get_logger("app", trace_id).info(
            f"POST /api/book — location={location_id}, "
            f"duration={duration}, slot={slot_id}"
        )

        if not location_id or duration is None:
            return jsonify({"error": "Both 'location' and 'duration' are required"}), 400

        # Rate limit check
        client_ip = request.remote_addr or "unknown"
        allowed, rl_msg = _guardrails.check_rate_limit(client_ip)
        if not allowed:
            return jsonify({"error": rl_msg}), 429

        result = _booking_agent.book(location_id, duration, slot_id, trace_id)
        if "error" in result:
            err = result["error"].lower()
            status = 409 if ("not available" in err or "no slots" in err) else 400
            return jsonify(result), status

        result["message"]   = f"Slot {result['booking']['slot_id']} booked successfully!"
        result["trace_id"]  = trace_id
        return jsonify(result), 201

    @app.route("/api/release", methods=["POST"])
    def api_release_slot():
        """POST /api/release — Release a booked slot."""
        trace_id = generate_trace_id()
        data     = request.get_json() or {}

        booking_id = data.get("booking_id")
        slot_id    = data.get("slot_id")

        get_logger("app", trace_id).info(
            f"POST /api/release — booking_id={booking_id}, slot_id={slot_id}"
        )

        if not booking_id and not slot_id:
            return jsonify({"error": "Either 'booking_id' or 'slot_id' is required"}), 400

        result = _booking_agent.release(booking_id, slot_id, trace_id)
        if "error" in result:
            return jsonify(result), 404

        result["trace_id"] = trace_id
        return jsonify(result)

    @app.route("/api/bookings", methods=["GET"])
    def api_get_bookings():
        """GET /api/bookings — Return all active bookings."""
        trace_id = generate_trace_id()
        get_logger("app", trace_id).info("GET /api/bookings")
        active = _booking_service.get_active_bookings()
        return jsonify({"bookings": active})

    @app.route("/api/booking/<booking_id>", methods=["GET"])
    def api_get_booking(booking_id):
        """GET /api/booking/<id> — Return a specific booking."""
        trace_id = generate_trace_id()
        get_logger("app", trace_id).info(f"GET /api/booking/{booking_id}")
        booking = _booking_service.get_booking(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404
        return jsonify({"booking": booking})

    @app.route("/api/nlp", methods=["POST"])
    def api_nlp():
        """
        POST /api/nlp — Natural language interface.

        Accepts a free-text query, runs it through the full MCP agent
        pipeline (guardrails → NLPAgent → RAG → routing), and returns
        a structured response.
        """
        data = request.get_json() or {}
        text = data.get("text", "").strip()

        if not text:
            return jsonify({"error": "No text provided"}), 400

        client_ip = request.remote_addr or "unknown"
        response  = _orchestrator.process_nlp_request(text, client_ip)
        return jsonify(response)

    # ------------------------------------------------------------------
    # Return the configured app
    # ------------------------------------------------------------------
    logger.info("create_app(): application configured and ready")
    return app


# ---------------------------------------------------------------------------
# Module-level app instance + entry-point
# ---------------------------------------------------------------------------

# Instantiated once when the module is loaded (e.g. by `python app.py`
# or a WSGI server).  Tests call create_app() directly to get a fresh
# instance backed by a temporary data file.
app = create_app()

if __name__ == "__main__":
    get_logger("app").info("Smart Parking Slot Booker MCP — starting on port 5000")
    app.run(debug=True, port=5000)
