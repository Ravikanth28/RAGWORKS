"""
Slot Agent
----------
Handles all parking-location and slot-availability queries.

Wraps SlotService with MCP intent validation and guardrail checks,
returning structured response dicts ready for JSON serialisation.
"""

from mcp.guardrails import Guardrails
from mcp.intent_engine import INTENT_VIEW_SLOTS, IntentEngine
from mcp.validator import IntentValidator
from services.slot_service import SlotService
from utils.logger import get_logger


class SlotAgent:
    """
    Agent responsible for slot and location availability queries.

    Parameters
    ----------
    slot_service:
        Injected SlotService for data access.
    guardrails:
        Injected Guardrails instance for input validation.
    """

    def __init__(self, slot_service: SlotService, guardrails: Guardrails):
        self.slot_service = slot_service
        self.guardrails   = guardrails
        self.logger       = get_logger(__name__)

    def get_locations(self, trace_id: str = "") -> dict:
        """
        Return all parking locations with real-time availability counts.

        Parameters
        ----------
        trace_id:
            Request trace ID for log correlation.

        Returns
        -------
        dict
            ``{"locations": [...]}``
        """
        logger = get_logger(__name__, trace_id)
        logger.info("SlotAgent.get_locations()")

        locations = self.slot_service.get_all_locations()
        return {"locations": locations}

    def get_slots(self, location_id: str, trace_id: str = "") -> dict:
        """
        Return detailed slot status for a single location.

        Validates the location ID format via guardrails and the resulting
        VIEW_SLOTS intent via IntentValidator before querying the service.

        Parameters
        ----------
        location_id:
            Canonical location ID.
        trace_id:
            Request trace ID for log correlation.

        Returns
        -------
        dict
            Full slot payload on success, or ``{"error": "..."}`` on failure.
        """
        logger = get_logger(__name__, trace_id)
        logger.info(f"SlotAgent.get_slots(location={location_id})")

        # Guardrail: validate ID format
        valid, msg = self.guardrails.sanitize_location_id(location_id)
        if not valid:
            logger.warning(f"SlotAgent: guardrail rejected location_id — {msg}")
            return {"error": msg}

        # MCP: build + validate intent
        engine    = IntentEngine(trace_id)
        intent    = engine.create_structured_intent(INTENT_VIEW_SLOTS, location=location_id)
        validator = IntentValidator(trace_id)
        ok, vmsg  = validator.validate(intent)
        if not ok:
            logger.warning(f"SlotAgent: intent validation failed — {vmsg}")
            return {"error": vmsg}

        result = self.slot_service.get_slots_for_location(location_id)
        if not result:
            logger.warning(f"SlotAgent: location '{location_id}' not found")
            return {"error": f"Location '{location_id}' not found."}

        logger.info(
            f"SlotAgent: returning {result['totalSlots']} slots "
            f"({result['availableSlots']} free) for '{location_id}'"
        )
        return result
