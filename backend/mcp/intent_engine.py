"""
MCP Intent Engine
-----------------
Converts raw natural-language text into a structured *MCP intent* dict
that the rest of the pipeline can validate and execute.

Supports:
  • Intent detection  (book / view / release / unknown)
  • Location resolution from aliases
  • Duration extraction via regex
  • Slot-ID extraction
  • Confidence scoring

This module is intentionally free of I/O side-effects so it can be
unit-tested without any external dependencies.
"""

import re
from typing import Optional

from utils.logger import get_logger

# ---------------------------------------------------------------------------
# Intent type constants
# ---------------------------------------------------------------------------
INTENT_VIEW_SLOTS   = "VIEW_SLOTS"
INTENT_BOOK_SLOT    = "BOOK_SLOT"
INTENT_RELEASE_SLOT = "RELEASE_SLOT"
INTENT_UNKNOWN      = "UNKNOWN"

# ---------------------------------------------------------------------------
# Location alias map  →  canonical location ID
# ---------------------------------------------------------------------------
LOCATION_ALIASES: dict[str, str] = {
    "anna nagar":      "anna-nagar",
    "annanagar":       "anna-nagar",
    "anna":            "anna-nagar",
    "t nagar":         "t-nagar",
    "tnagar":          "t-nagar",
    "t.nagar":         "t-nagar",
    "thyagaraya nagar":"t-nagar",
    "velachery":       "velachery",
    "mall":            "mall-parking",
    "mall parking":    "mall-parking",
    "express avenue":  "mall-parking",
    "express":         "mall-parking",
}


class IntentEngine:
    """
    Parses natural-language text into structured MCP intents.

    Parameters
    ----------
    trace_id:
        Optional request trace ID passed down for log correlation.
    """

    def __init__(self, trace_id: str = ""):
        self.logger = get_logger(__name__, trace_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, text: str) -> dict:
        """
        Parse a natural-language string into an MCP intent dict.

        The returned dict has the shape::

            {
                "intent":     "BOOK_SLOT",
                "params": {
                    "location": "mall-parking",
                    "duration": 2,
                    "slot_id":  None,
                },
                "raw_input":  "Book parking near mall for 2 hours",
                "confidence": 1.0,
            }

        Parameters
        ----------
        text:
            Raw user input string.

        Returns
        -------
        dict
            Parsed intent with confidence score.
        """
        self.logger.debug(f"IntentEngine.parse — input='{text[:80]}'")

        text_lower = text.strip().lower()

        intent   = self._detect_intent(text_lower)
        location = self.resolve_location(text_lower)
        duration = self.extract_duration(text)
        slot_id  = self._extract_slot_id(text)
        confidence = self._calculate_confidence(intent, location, duration)

        self.logger.debug(
            f"IntentEngine.parse — intent={intent}, location={location}, "
            f"duration={duration}, confidence={confidence}"
        )

        return {
            "intent": intent,
            "params": {
                "location": location,
                "duration": duration,
                "slot_id":  slot_id,
            },
            "raw_input":  text,
            "confidence": confidence,
        }

    def create_structured_intent(self, intent_type: str, **params) -> dict:
        """
        Build a structured MCP intent from typed API parameters.

        Structured intents come from validated API calls and therefore
        always receive a confidence of ``1.0``.

        Parameters
        ----------
        intent_type:
            One of the ``INTENT_*`` constants.
        **params:
            Arbitrary intent parameters (location, duration, slot_id …).

        Returns
        -------
        dict
            Intent dict with ``confidence=1.0``.
        """
        return {
            "intent":     intent_type,
            "params":     params,
            "confidence": 1.0,
        }

    # ------------------------------------------------------------------
    # Location helpers (also used externally by RAG module)
    # ------------------------------------------------------------------

    def resolve_location(self, text: str) -> Optional[str]:
        """
        Resolve a location phrase or alias to its canonical location ID.

        Tries exact match first, then longest-prefix partial match.

        Parameters
        ----------
        text:
            Lowercased input text or bare location phrase.

        Returns
        -------
        str or None
            Canonical location ID (e.g. ``"anna-nagar"``) or ``None``.
        """
        text_lower = text.strip().lower()

        if text_lower in LOCATION_ALIASES:
            return LOCATION_ALIASES[text_lower]

        # Longest alias first to avoid short alias swallowing longer ones
        for alias, loc_id in sorted(LOCATION_ALIASES.items(), key=lambda x: -len(x[0])):
            if alias in text_lower:
                return loc_id

        return None

    def extract_duration(self, text: str) -> Optional[int]:
        """
        Extract a booking duration (hours) from natural language.

        Handled patterns: ``"2 hours"``, ``"3 hrs"``, ``"1 hour"``,
        ``"for 2h"``, ``"duration: 3"``.

        Parameters
        ----------
        text:
            Raw input text (case-insensitive).

        Returns
        -------
        int or None
            Duration in hours, or ``None`` if not found.
        """
        patterns = [
            r"(\d+)\s*(?:hours?|hrs?|h)\b",
            r"for\s+(\d+)",
            r"duration\s*[:=]?\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_intent(self, text_lower: str) -> str:
        """Identify the user's intent from keyword patterns."""
        if any(w in text_lower for w in ["book", "reserve", "park", "find", "get", "need"]):
            return INTENT_BOOK_SLOT
        if any(w in text_lower for w in ["release", "free", "cancel", "unbook", "vacate", "leave"]):
            return INTENT_RELEASE_SLOT
        if any(w in text_lower for w in ["show", "view", "list", "check", "available", "see", "how many"]):
            return INTENT_VIEW_SLOTS
        return INTENT_UNKNOWN

    def _extract_slot_id(self, text: str) -> Optional[str]:
        """Extract a slot ID like ``AN-001`` or ``TN-003`` from text."""
        match = re.search(r"\b([A-Z]{2}-\d{3})\b", text, re.IGNORECASE)
        return match.group(1).upper() if match else None

    def _calculate_confidence(
        self,
        intent: str,
        location: Optional[str],
        duration: Optional[int],
    ) -> float:
        """
        Score NLP parsing quality on a 0–1 scale.

        +0.4  intent is not UNKNOWN
        +0.3  a location was resolved
        +0.3  a duration was extracted
        """
        score = 0.0
        if intent != INTENT_UNKNOWN:
            score += 0.4
        if location:
            score += 0.3
        if duration:
            score += 0.3
        return round(score, 2)
