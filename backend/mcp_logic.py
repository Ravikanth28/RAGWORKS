"""
MCP (Model Context Protocol) Logic Layer
-----------------------------------------
Interprets user actions as structured intents and extracts parameters.
Supports both structured API calls and natural language input.
"""

import re

# Supported intents
INTENT_VIEW_SLOTS = "VIEW_SLOTS"
INTENT_BOOK_SLOT = "BOOK_SLOT"
INTENT_RELEASE_SLOT = "RELEASE_SLOT"
INTENT_UNKNOWN = "UNKNOWN"

# Location aliases for NLP matching
LOCATION_ALIASES = {
    "anna nagar": "anna-nagar",
    "annanagar": "anna-nagar",
    "anna": "anna-nagar",
    "t nagar": "t-nagar",
    "tnagar": "t-nagar",
    "t.nagar": "t-nagar",
    "thyagaraya nagar": "t-nagar",
    "velachery": "velachery",
    "mall": "mall-parking",
    "mall parking": "mall-parking",
    "express avenue": "mall-parking",
    "express": "mall-parking",
}


def resolve_location(text: str) -> str | None:
    """Resolve a location string to a known location ID."""
    text_lower = text.strip().lower()
    # Direct match
    if text_lower in LOCATION_ALIASES:
        return LOCATION_ALIASES[text_lower]
    # Partial match
    for alias, loc_id in LOCATION_ALIASES.items():
        if alias in text_lower or text_lower in alias:
            return loc_id
    return None


def extract_duration(text: str) -> int | None:
    """Extract duration in hours from natural language text."""
    # Match patterns like "2 hours", "3 hrs", "1 hour", "for 2h"
    patterns = [
        r'(\d+)\s*(?:hours?|hrs?|h)\b',
        r'for\s+(\d+)',
        r'duration\s*[:=]?\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def parse_natural_language(text: str) -> dict:
    """
    Parse natural language input into an MCP intent with parameters.
    
    Examples:
        "Book parking near mall for 2 hours"
        "Show slots at Anna Nagar"
        "Release slot AN-001"
        "Find parking in Velachery for 3 hours"
    """
    text_lower = text.strip().lower()

    # Detect intent
    intent = INTENT_UNKNOWN
    if any(word in text_lower for word in ["book", "reserve", "park", "find", "get"]):
        intent = INTENT_BOOK_SLOT
    elif any(word in text_lower for word in ["release", "free", "cancel", "unbook", "vacate"]):
        intent = INTENT_RELEASE_SLOT
    elif any(word in text_lower for word in ["show", "view", "list", "check", "available", "see"]):
        intent = INTENT_VIEW_SLOTS

    # Extract location
    location = None
    for alias, loc_id in sorted(LOCATION_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in text_lower:
            location = loc_id
            break

    # Extract duration
    duration = extract_duration(text)

    # Extract slot ID if mentioned (e.g., "release AN-001")
    slot_id = None
    slot_match = re.search(r'\b([A-Z]{2}-\d{3})\b', text, re.IGNORECASE)
    if slot_match:
        slot_id = slot_match.group(1).upper()

    return {
        "intent": intent,
        "params": {
            "location": location,
            "duration": duration,
            "slot_id": slot_id,
        },
        "raw_input": text,
        "confidence": _calculate_confidence(intent, location, duration),
    }


def _calculate_confidence(intent: str, location, duration) -> float:
    """Calculate confidence score for the parsed intent."""
    score = 0.0
    if intent != INTENT_UNKNOWN:
        score += 0.4
    if location:
        score += 0.3
    if duration:
        score += 0.3
    return round(score, 2)


def create_intent(intent_type: str, **params) -> dict:
    """
    Create a structured MCP intent from API parameters.
    This is used by the structured API endpoints.
    """
    return {
        "intent": intent_type,
        "params": params,
        "confidence": 1.0,  # Structured intents always have full confidence
    }


def validate_intent(intent: dict) -> tuple[bool, str]:
    """Validate that an intent has all required parameters."""
    intent_type = intent.get("intent")
    params = intent.get("params", {})

    if intent_type == INTENT_VIEW_SLOTS:
        if not params.get("location"):
            return False, "Location is required to view slots."
        return True, "Valid"

    elif intent_type == INTENT_BOOK_SLOT:
        if not params.get("location"):
            return False, "Location is required to book a slot."
        if not params.get("duration"):
            return False, "Duration (in hours) is required to book a slot."
        return True, "Valid"

    elif intent_type == INTENT_RELEASE_SLOT:
        if not params.get("slot_id") and not params.get("booking_id"):
            return False, "Slot ID or Booking ID is required to release a slot."
        return True, "Valid"

    return False, f"Unknown intent: {intent_type}"
