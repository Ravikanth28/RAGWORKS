"""
Booking Agent
-------------
Handles all slot-booking and booking-release operations.

Applies guardrail validation, builds MCP intents, validates them via
IntentValidator, then delegates to BookingService for data mutations.
Every step is logged with the request trace ID.
"""

from typing import Optional

from mcp.guardrails import Guardrails
from mcp.intent_engine import INTENT_BOOK_SLOT, INTENT_RELEASE_SLOT, IntentEngine
from mcp.validator import IntentValidator
from services.booking_service import BookingService
from services.slot_service import SlotService
from utils.logger import get_logger


class BookingAgent:
    """
    Agent responsible for booking and releasing parking slots.

    Parameters
    ----------
    booking_service:
        Injected BookingService for business logic.
    slot_service:
        Injected SlotService for location lookups.
    guardrails:
        Injected Guardrails instance for input validation.
    """

    def __init__(
        self,
        booking_service: BookingService,
        slot_service: SlotService,
        guardrails: Guardrails,
    ):
        self.booking_service = booking_service
        self.slot_service    = slot_service
        self.guardrails      = guardrails
        self.logger          = get_logger(__name__)

    # ------------------------------------------------------------------
    # Book
    # ------------------------------------------------------------------

    def book(
        self,
        location_id: str,
        duration: int,
        slot_id: Optional[str] = None,
        trace_id: str = "",
    ) -> dict:
        """
        Book a parking slot.

        Pipeline:
        1. Guardrail: validate duration range.
        2. Guardrail: validate location ID format.
        3. MCP: create + validate BOOK_SLOT intent.
        4. BookingService: create_booking().

        Parameters
        ----------
        location_id:
            Canonical location ID.
        duration:
            Booking duration in hours.
        slot_id:
            Optional specific slot; first available used when ``None``.
        trace_id:
            Request trace ID for log correlation.

        Returns
        -------
        dict
            ``{"booking": ..., "mcp_intent": ...}`` on success, or
            ``{"error": "..."}`` on failure.
        """
        logger = get_logger(__name__, trace_id)
        logger.info(
            f"BookingAgent.book(location={location_id}, "
            f"duration={duration}, slot={slot_id})"
        )

        # Guardrail checks
        valid, msg = self.guardrails.validate_duration(duration)
        if not valid:
            logger.warning(f"BookingAgent: duration rejected — {msg}")
            return {"error": msg}

        valid, msg = self.guardrails.sanitize_location_id(location_id)
        if not valid:
            logger.warning(f"BookingAgent: location_id rejected — {msg}")
            return {"error": msg}

        # MCP intent
        engine    = IntentEngine(trace_id)
        intent    = engine.create_structured_intent(
            INTENT_BOOK_SLOT, location=location_id, duration=duration
        )
        validator = IntentValidator(trace_id)
        ok, vmsg  = validator.validate(intent)
        if not ok:
            logger.warning(f"BookingAgent: intent invalid — {vmsg}")
            return {"error": vmsg}

        # Execute booking
        try:
            booking = self.booking_service.create_booking(location_id, duration, slot_id)
            logger.info(f"BookingAgent: booking created — {booking['booking_id']}")
            return {"booking": booking, "mcp_intent": intent}
        except ValueError as exc:
            logger.warning(f"BookingAgent: booking failed — {exc}")
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Release
    # ------------------------------------------------------------------

    def release(
        self,
        booking_id: Optional[str] = None,
        slot_id: Optional[str] = None,
        trace_id: str = "",
    ) -> dict:
        """
        Release an active booking.

        At least one of *booking_id* or *slot_id* must be provided.

        Parameters
        ----------
        booking_id:
            Booking ID to release (preferred).
        slot_id:
            Slot ID to release (alternative lookup).
        trace_id:
            Request trace ID for log correlation.

        Returns
        -------
        dict
            Success message dict or ``{"error": "..."}`` on failure.
        """
        logger = get_logger(__name__, trace_id)
        logger.info(
            f"BookingAgent.release(booking_id={booking_id}, slot_id={slot_id})"
        )

        # Resolve the booking record
        target: Optional[dict] = None
        if booking_id:
            target = self.booking_service.get_booking(booking_id)
        elif slot_id:
            target = self.booking_service.find_booking_by_slot(slot_id)

        if not target:
            return {"error": "Booking not found or already released."}

        if target["status"] != "active":
            return {"error": "Booking is not active."}

        bid = target["booking_id"]

        # MCP intent (for auditability / response)
        engine = IntentEngine(trace_id)
        intent = engine.create_structured_intent(
            INTENT_RELEASE_SLOT, booking_id=bid, slot_id=target["slot_id"]
        )

        success = self.booking_service.release_booking(bid)
        if not success:
            return {"error": "Failed to release booking."}

        logger.info(f"BookingAgent: released booking {bid}")
        return {
            "message":    f"Slot {target['slot_id']} released successfully!",
            "booking_id": bid,
            "mcp_intent": intent,
        }
