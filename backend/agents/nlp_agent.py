"""
NLP Agent & Agent Orchestrator
-------------------------------

NLPAgent
~~~~~~~~
Processes free-text natural language input through the full MCP
pipeline:  Guardrails → IntentEngine → RAGModule → IntentValidator.

AgentOrchestrator
~~~~~~~~~~~~~~~~~
Single entry-point that routes *every* request — NLP or structured —
to the correct specialised agent (SlotAgent or BookingAgent).

    orchestrator.process_nlp_request(text, client_ip)
        → rate-limit check
        → NLPAgent.process()
        → route to SlotAgent / BookingAgent based on intent
        → return enriched response dict
"""

from typing import Optional

from agents.booking_agent import BookingAgent
from agents.slot_agent import SlotAgent
from mcp.guardrails import Guardrails
from mcp.intent_engine import (
    INTENT_BOOK_SLOT,
    INTENT_RELEASE_SLOT,
    INTENT_VIEW_SLOTS,
    IntentEngine,
)
from mcp.rag_module import RAGModule
from mcp.validator import IntentValidator
from utils.config import Config
from utils.logger import generate_trace_id, get_logger


# ===========================================================================
# NLP Agent
# ===========================================================================

class NLPAgent:
    """
    Parses natural-language input into an enriched MCP intent.

    Pipeline (per request):
    1. Guardrails.validate_text_input()
    2. IntentEngine.parse()
    3. RAGModule.enrich_intent()
    4. IntentValidator.validate()

    Parameters
    ----------
    guardrails:
        Injected Guardrails instance.
    rag_module:
        Injected RAGModule instance.
    """

    def __init__(self, guardrails: Guardrails, rag_module: RAGModule):
        self.guardrails = guardrails
        self.rag        = rag_module
        self.logger     = get_logger(__name__)

    def process(self, text: str, trace_id: str = "") -> dict:
        """
        Run the full NLP pipeline on *text*.

        Parameters
        ----------
        text:
            Raw user input string.
        trace_id:
            Request trace ID for log correlation.

        Returns
        -------
        dict
            Parsed intent dict (with ``rag_context``, ``validation_ok``,
            and ``validation_msg`` added), or a minimal error dict if
            guardrails reject the input.
        """
        logger = get_logger(__name__, trace_id)
        logger.info(f"NLPAgent.process — input='{text[:80]}'")

        # Step 1: Safety check
        valid, msg = self.guardrails.validate_text_input(text)
        if not valid:
            logger.warning(f"NLPAgent: guardrails rejected input — {msg}")
            return {
                "intent":     "UNKNOWN",
                "params":     {},
                "confidence": 0.0,
                "error":      msg,
            }

        # Step 2: Intent parsing
        engine = IntentEngine(trace_id)
        parsed = engine.parse(text)

        # Step 3: RAG enrichment
        parsed = self.rag.enrich_intent(parsed, text)

        # Step 4: Validation
        validator        = IntentValidator(trace_id)
        ok, vmsg         = validator.validate(parsed)
        parsed["validation_ok"]  = ok
        parsed["validation_msg"] = vmsg

        logger.info(
            f"NLPAgent: intent={parsed['intent']}, "
            f"confidence={parsed['confidence']}, valid={ok}"
        )
        return parsed


# ===========================================================================
# Agent Orchestrator
# ===========================================================================

class AgentOrchestrator:
    """
    Routes incoming requests to the appropriate specialised agent.

    For NLP calls  → NLPAgent parses the text, then SlotAgent /
                     BookingAgent executes or prefills the intent.
    For direct API → SlotAgent / BookingAgent are called directly
                     by the Flask routes (bypassing this orchestrator).

    Parameters
    ----------
    nlp_agent:
        Injected NLPAgent.
    booking_agent:
        Injected BookingAgent.
    slot_agent:
        Injected SlotAgent.
    guardrails:
        Injected Guardrails (used for rate limiting).
    """

    def __init__(
        self,
        nlp_agent: NLPAgent,
        booking_agent: BookingAgent,
        slot_agent: SlotAgent,
        guardrails: Guardrails,
    ):
        self.nlp_agent     = nlp_agent
        self.booking_agent = booking_agent
        self.slot_agent    = slot_agent
        self.guardrails    = guardrails
        self.logger        = get_logger(__name__)

    def process_nlp_request(
        self, text: str, client_ip: str = "unknown"
    ) -> dict:
        """
        Full NLP request pipeline with rate limiting and agent routing.

        Flow:
        1. Rate-limit check per client IP.
        2. NLPAgent.process() — parse + RAG enrich.
        3. Route to SlotAgent / BookingAgent based on detected intent.
        4. Return enriched response dict.

        Parameters
        ----------
        text:
            Raw natural-language user input.
        client_ip:
            Client IP address for rate limiting.

        Returns
        -------
        dict
            Response dict containing at minimum ``"parsed"`` and
            ``"trace_id"`` keys.  Additional keys depend on intent:
            ``"result"``, ``"action"``, ``"prefill"``, ``"message"``,
            ``"context"``, ``"error"``.
        """
        trace_id = generate_trace_id()
        logger   = get_logger(__name__, trace_id)
        logger.info(f"Orchestrator: NLP request from {client_ip}")

        # Rate limit
        allowed, rl_msg = self.guardrails.check_rate_limit(client_ip)
        if not allowed:
            return {"error": rl_msg, "trace_id": trace_id}

        # NLP pipeline
        parsed = self.nlp_agent.process(text, trace_id)

        response: dict = {"parsed": parsed, "trace_id": trace_id}

        # Low-confidence fallback
        if parsed.get("confidence", 0.0) < Config.NLP_MIN_CONFIDENCE:
            response["message"] = (
                "I couldn't understand that. "
                "Try: 'Book parking at Mall for 2 hours'"
            )
            return response

        intent = parsed.get("intent", "UNKNOWN")
        params = parsed.get("params", {})

        # ------------------------------------------------------------------
        # Route: VIEW_SLOTS
        # ------------------------------------------------------------------
        if intent == INTENT_VIEW_SLOTS and params.get("location"):
            result = self.slot_agent.get_slots(params["location"], trace_id)
            if "error" not in result:
                response["result"] = {
                    "location":  result["location"],
                    "available": result["availableSlots"],
                    "total":     result["totalSlots"],
                }
                response["message"] = (
                    f"{result['location']} has "
                    f"{result['availableSlots']}/{result['totalSlots']} "
                    "slots available."
                )
            else:
                response["error"] = result["error"]

        # ------------------------------------------------------------------
        # Route: BOOK_SLOT — return prefill for UI confirmation
        # ------------------------------------------------------------------
        elif (
            intent == INTENT_BOOK_SLOT
            and params.get("location")
            and params.get("duration")
        ):
            loc_result = self.slot_agent.get_slots(params["location"], trace_id)
            response["action"]  = "book"
            response["prefill"] = {
                "location": params["location"],
                "duration": params["duration"],
            }
            if "error" not in loc_result:
                cost = params["duration"] * loc_result.get("ratePerHour", 20)
                response["message"] = (
                    f"Ready to book at {loc_result['location']} "
                    f"for {params['duration']} hour(s). "
                    f"Cost: ₹{cost}. Confirm to proceed."
                )
            else:
                response["message"] = (
                    f"Ready to book at {params['location']} "
                    f"for {params['duration']} hour(s)."
                )

        # ------------------------------------------------------------------
        # Route: RELEASE_SLOT — return prefill for UI confirmation
        # ------------------------------------------------------------------
        elif intent == INTENT_RELEASE_SLOT and params.get("slot_id"):
            response["action"]  = "release"
            response["prefill"] = {"slot_id": params["slot_id"]}
            response["message"] = (
                f"Ready to release slot {params['slot_id']}. "
                "Confirm to proceed."
            )

        # ------------------------------------------------------------------
        # Attach RAG context (if any)
        # ------------------------------------------------------------------
        if parsed.get("rag_context_text"):
            response["context"] = parsed["rag_context_text"]

        return response
