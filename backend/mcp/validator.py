"""
MCP Intent Validator
--------------------
Validates a structured MCP intent dict before it is executed.

Each intent type has a required set of parameters.  The validator
checks those requirements and returns a ``(bool, str)`` result tuple
so callers can decide how to respond.
"""

from typing import Tuple

from mcp.intent_engine import (
    INTENT_BOOK_SLOT,
    INTENT_RELEASE_SLOT,
    INTENT_VIEW_SLOTS,
)
from utils.logger import get_logger


class IntentValidator:
    """
    Validates MCP intent dicts before execution.

    Parameters
    ----------
    trace_id:
        Optional request trace ID for log correlation.
    """

    def __init__(self, trace_id: str = ""):
        self.logger = get_logger(__name__, trace_id)

    def validate(self, intent: dict) -> Tuple[bool, str]:
        """
        Validate an MCP intent dict.

        Parameters
        ----------
        intent:
            Dict with at least ``"intent"`` and ``"params"`` keys.

        Returns
        -------
        (is_valid, message)
            ``is_valid`` is ``True`` when all required fields are present
            and in-range.  ``message`` is ``"Valid"`` on success or an
            error description on failure.
        """
        intent_type = intent.get("intent")
        params      = intent.get("params", {})

        self.logger.debug(f"Validating intent type='{intent_type}' params={params}")

        if intent_type == INTENT_VIEW_SLOTS:
            return self._validate_view_slots(params)
        if intent_type == INTENT_BOOK_SLOT:
            return self._validate_book_slot(params)
        if intent_type == INTENT_RELEASE_SLOT:
            return self._validate_release_slot(params)

        self.logger.warning(f"Unknown intent type: '{intent_type}'")
        return False, f"Unknown intent type: '{intent_type}'"

    # ------------------------------------------------------------------
    # Private per-intent validators
    # ------------------------------------------------------------------

    def _validate_view_slots(self, params: dict) -> Tuple[bool, str]:
        """VIEW_SLOTS requires a location."""
        if not params.get("location"):
            return False, "Location is required to view slots."
        return True, "Valid"

    def _validate_book_slot(self, params: dict) -> Tuple[bool, str]:
        """BOOK_SLOT requires location + valid duration."""
        if not params.get("location"):
            return False, "Location is required to book a slot."

        duration = params.get("duration")
        if duration is None:
            return False, "Duration (in hours) is required to book a slot."

        try:
            duration = int(duration)
        except (ValueError, TypeError):
            return False, "Duration must be a valid integer."

        if duration < 1 or duration > 24:
            return False, "Duration must be between 1 and 24 hours."

        return True, "Valid"

    def _validate_release_slot(self, params: dict) -> Tuple[bool, str]:
        """RELEASE_SLOT requires either slot_id or booking_id."""
        if not params.get("slot_id") and not params.get("booking_id"):
            return False, "Slot ID or Booking ID is required to release a slot."
        return True, "Valid"
