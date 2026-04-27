"""
Unit tests — MCP layer
======================
Tests for:
  - IntentEngine  (parse, resolve_location, extract_duration, confidence)
  - IntentValidator (all three intent types)
  - Guardrails (text input, duration, location ID, rate limiting)
  - RAGModule (retrieve_context, get_context_text, enrich_intent)
"""

import pytest

from mcp.guardrails import Guardrails
from mcp.intent_engine import (
    INTENT_BOOK_SLOT,
    INTENT_RELEASE_SLOT,
    INTENT_UNKNOWN,
    INTENT_VIEW_SLOTS,
    IntentEngine,
)
from mcp.rag_module import RAGModule
from mcp.validator import IntentValidator


# ===========================================================================
# IntentEngine
# ===========================================================================

class TestIntentEngineParse:
    """parse() natural-language input tests."""

    @pytest.fixture
    def engine(self):
        return IntentEngine()

    def test_book_intent_detected(self, engine):
        result = engine.parse("Book parking near mall for 2 hours")
        assert result["intent"] == INTENT_BOOK_SLOT

    def test_view_intent_detected(self, engine):
        result = engine.parse("Show available slots at Anna Nagar")
        assert result["intent"] == INTENT_VIEW_SLOTS

    def test_release_intent_detected(self, engine):
        result = engine.parse("Release slot AN-001")
        assert result["intent"] == INTENT_RELEASE_SLOT

    def test_unknown_intent_fallback(self, engine):
        result = engine.parse("Hello there")
        assert result["intent"] == INTENT_UNKNOWN

    def test_location_resolved_anna_nagar(self, engine):
        result = engine.parse("book at anna nagar for 1 hour")
        assert result["params"]["location"] == "anna-nagar"

    def test_location_resolved_alias_anna(self, engine):
        result = engine.parse("park near anna for 2 hours")
        assert result["params"]["location"] == "anna-nagar"

    def test_location_resolved_mall(self, engine):
        result = engine.parse("find parking near mall for 3 hours")
        assert result["params"]["location"] == "mall-parking"

    def test_location_resolved_express_avenue(self, engine):
        result = engine.parse("book at express avenue for 1 hour")
        assert result["params"]["location"] == "mall-parking"

    def test_location_none_when_absent(self, engine):
        result = engine.parse("book parking for 2 hours")
        assert result["params"]["location"] is None

    def test_duration_extracted_hours(self, engine):
        result = engine.parse("I need parking for 3 hours")
        assert result["params"]["duration"] == 3

    def test_duration_extracted_h_abbreviation(self, engine):
        result = engine.parse("book velachery for 5h")
        assert result["params"]["duration"] == 5

    def test_duration_none_when_absent(self, engine):
        result = engine.parse("show slots at t nagar")
        assert result["params"]["duration"] is None

    def test_slot_id_extracted(self, engine):
        result = engine.parse("release slot AN-001 please")
        assert result["params"]["slot_id"] == "AN-001"

    def test_slot_id_none_when_absent(self, engine):
        result = engine.parse("show slots at velachery")
        assert result["params"]["slot_id"] is None

    def test_raw_input_preserved(self, engine):
        text   = "Book parking near mall for 2 hours"
        result = engine.parse(text)
        assert result["raw_input"] == text

    def test_full_confidence_all_fields(self, engine):
        result = engine.parse("book parking near mall for 2 hours")
        assert result["confidence"] == 1.0

    def test_partial_confidence_no_duration(self, engine):
        result = engine.parse("show slots at anna nagar")
        # intent (0.4) + location (0.3) = 0.7
        assert result["confidence"] == pytest.approx(0.7)

    def test_zero_confidence_unknown_intent(self, engine):
        result = engine.parse("hello world")
        assert result["confidence"] == 0.0


class TestIntentEngineResolveLocation:
    """resolve_location() unit tests."""

    @pytest.fixture
    def engine(self):
        return IntentEngine()

    def test_exact_alias_match(self, engine):
        assert engine.resolve_location("t nagar") == "t-nagar"

    def test_partial_alias_match(self, engine):
        assert engine.resolve_location("I am near tnagar") == "t-nagar"

    def test_velachery_direct(self, engine):
        assert engine.resolve_location("velachery") == "velachery"

    def test_unknown_returns_none(self, engine):
        assert engine.resolve_location("unknown place xyz") is None


class TestIntentEngineExtractDuration:
    """extract_duration() unit tests."""

    @pytest.fixture
    def engine(self):
        return IntentEngine()

    def test_hours_keyword(self, engine):
        assert engine.extract_duration("park for 2 hours") == 2

    def test_hr_abbreviation(self, engine):
        assert engine.extract_duration("3 hrs") == 3

    def test_h_abbreviation(self, engine):
        assert engine.extract_duration("4h") == 4

    def test_for_n_pattern(self, engine):
        assert engine.extract_duration("book for 6") == 6

    def test_no_duration_returns_none(self, engine):
        assert engine.extract_duration("show slots at anna nagar") is None


class TestIntentEngineCreateStructured:
    """create_structured_intent() always has confidence=1.0."""

    def test_structured_intent_confidence(self):
        engine = IntentEngine()
        intent = engine.create_structured_intent(INTENT_BOOK_SLOT, location="anna-nagar", duration=2)
        assert intent["confidence"] == 1.0
        assert intent["intent"]     == INTENT_BOOK_SLOT
        assert intent["params"]["location"] == "anna-nagar"


# ===========================================================================
# IntentValidator
# ===========================================================================

class TestIntentValidator:
    """validate() for each intent type."""

    @pytest.fixture
    def validator(self):
        return IntentValidator()

    # VIEW_SLOTS
    def test_view_slots_valid(self, validator):
        intent = {"intent": INTENT_VIEW_SLOTS, "params": {"location": "anna-nagar"}}
        ok, msg = validator.validate(intent)
        assert ok is True

    def test_view_slots_missing_location(self, validator):
        intent = {"intent": INTENT_VIEW_SLOTS, "params": {}}
        ok, msg = validator.validate(intent)
        assert ok is False
        assert "location" in msg.lower()

    # BOOK_SLOT
    def test_book_slot_valid(self, validator):
        intent = {"intent": INTENT_BOOK_SLOT, "params": {"location": "velachery", "duration": 2}}
        ok, _  = validator.validate(intent)
        assert ok is True

    def test_book_slot_missing_location(self, validator):
        intent = {"intent": INTENT_BOOK_SLOT, "params": {"duration": 2}}
        ok, msg = validator.validate(intent)
        assert ok is False

    def test_book_slot_missing_duration(self, validator):
        intent = {"intent": INTENT_BOOK_SLOT, "params": {"location": "velachery"}}
        ok, msg = validator.validate(intent)
        assert ok is False

    def test_book_slot_duration_out_of_range(self, validator):
        intent = {"intent": INTENT_BOOK_SLOT, "params": {"location": "velachery", "duration": 25}}
        ok, msg = validator.validate(intent)
        assert ok is False

    def test_book_slot_duration_zero(self, validator):
        intent = {"intent": INTENT_BOOK_SLOT, "params": {"location": "velachery", "duration": 0}}
        ok, msg = validator.validate(intent)
        assert ok is False

    def test_book_slot_duration_string_valid(self, validator):
        """Duration may arrive as a string from JSON."""
        intent = {"intent": INTENT_BOOK_SLOT, "params": {"location": "velachery", "duration": "3"}}
        ok, _  = validator.validate(intent)
        assert ok is True

    # RELEASE_SLOT
    def test_release_slot_valid_booking_id(self, validator):
        intent = {"intent": INTENT_RELEASE_SLOT, "params": {"booking_id": "ABCD1234"}}
        ok, _  = validator.validate(intent)
        assert ok is True

    def test_release_slot_valid_slot_id(self, validator):
        intent = {"intent": INTENT_RELEASE_SLOT, "params": {"slot_id": "AN-001"}}
        ok, _  = validator.validate(intent)
        assert ok is True

    def test_release_slot_missing_both(self, validator):
        intent = {"intent": INTENT_RELEASE_SLOT, "params": {}}
        ok, _  = validator.validate(intent)
        assert ok is False

    # Unknown intent
    def test_unknown_intent(self, validator):
        intent = {"intent": "NONEXISTENT", "params": {}}
        ok, _  = validator.validate(intent)
        assert ok is False


# ===========================================================================
# Guardrails
# ===========================================================================

class TestGuardrailsTextInput:
    """validate_text_input() tests."""

    @pytest.fixture
    def g(self):
        return Guardrails()

    def test_valid_text(self, g):
        ok, _ = g.validate_text_input("Book parking near mall for 2 hours")
        assert ok is True

    def test_empty_string(self, g):
        ok, msg = g.validate_text_input("")
        assert ok is False

    def test_whitespace_only(self, g):
        ok, _ = g.validate_text_input("   ")
        assert ok is False

    def test_too_long(self, g):
        ok, _ = g.validate_text_input("a" * 501)
        assert ok is False

    def test_html_injection(self, g):
        ok, _ = g.validate_text_input("<script>alert(1)</script>")
        assert ok is False

    def test_sql_injection(self, g):
        ok, _ = g.validate_text_input("drop table users")
        assert ok is False


class TestGuardrailsDuration:
    """validate_duration() tests."""

    @pytest.fixture
    def g(self):
        return Guardrails()

    def test_valid_duration(self, g):
        ok, _ = g.validate_duration(3)
        assert ok is True

    def test_min_boundary(self, g):
        ok, _ = g.validate_duration(1)
        assert ok is True

    def test_max_boundary(self, g):
        ok, _ = g.validate_duration(24)
        assert ok is True

    def test_zero_rejected(self, g):
        ok, _ = g.validate_duration(0)
        assert ok is False

    def test_negative_rejected(self, g):
        ok, _ = g.validate_duration(-1)
        assert ok is False

    def test_over_max_rejected(self, g):
        ok, _ = g.validate_duration(25)
        assert ok is False

    def test_string_coercion(self, g):
        ok, _ = g.validate_duration("5")
        assert ok is True

    def test_non_numeric_rejected(self, g):
        ok, _ = g.validate_duration("two")
        assert ok is False


class TestGuardrailsLocationId:
    """sanitize_location_id() tests."""

    @pytest.fixture
    def g(self):
        return Guardrails()

    def test_valid_id(self, g):
        ok, _ = g.sanitize_location_id("anna-nagar")
        assert ok is True

    def test_path_traversal_rejected(self, g):
        ok, _ = g.sanitize_location_id("../etc/passwd")
        assert ok is False

    def test_empty_rejected(self, g):
        ok, _ = g.sanitize_location_id("")
        assert ok is False

    def test_too_long_rejected(self, g):
        ok, _ = g.sanitize_location_id("a" * 51)
        assert ok is False


class TestGuardrailsRateLimit:
    """check_rate_limit() tests."""

    def test_first_request_allowed(self):
        g = Guardrails()
        ok, _ = g.check_rate_limit("1.2.3.4")
        assert ok is True

    def test_rate_limit_exceeded(self):
        from utils.config import Config
        g = Guardrails()
        ip = "9.9.9.9"
        # Exhaust the limit
        for _ in range(Config.RATE_LIMIT_REQUESTS):
            g.check_rate_limit(ip)
        ok, msg = g.check_rate_limit(ip)
        assert ok is False
        assert "rate limit" in msg.lower()


# ===========================================================================
# RAGModule
# ===========================================================================

class TestRAGModule:
    """RAGModule retrieval tests using an in-memory knowledge base."""

    @pytest.fixture
    def rag(self):
        module = RAGModule.__new__(RAGModule)
        module.knowledge_base = [
            {
                "id": "pricing-1",
                "category": "pricing",
                "keywords": ["price", "cost", "rate"],
                "content": "Rate is ₹20 per hour.",
            },
            {
                "id": "policy-1",
                "category": "policy",
                "keywords": ["book", "booking", "reserve"],
                "content": "Booking is instant.",
            },
            {
                "id": "location-1",
                "category": "location",
                "keywords": ["anna", "nagar", "anna nagar"],
                "content": "Anna Nagar has 8 slots.",
            },
        ]
        from utils.logger import get_logger
        module.logger = get_logger("rag_test")
        return module

    def test_retrieve_relevant_entry(self, rag):
        results = rag.retrieve_context("what is the price")
        assert len(results) == 1
        assert results[0]["id"] == "pricing-1"

    def test_retrieve_multiple_entries(self, rag):
        results = rag.retrieve_context("book at anna nagar")
        ids = [r["id"] for r in results]
        assert "policy-1" in ids
        assert "location-1" in ids

    def test_retrieve_empty_on_no_match(self, rag):
        results = rag.retrieve_context("completely unrelated xyz")
        assert results == []

    def test_get_context_text_format(self, rag):
        text = rag.get_context_text("what is the price")
        assert "[PRICING]" in text
        assert "₹20" in text

    def test_enrich_intent_adds_keys(self, rag):
        intent = {"intent": INTENT_VIEW_SLOTS, "params": {}}
        enriched = rag.enrich_intent(intent, "what is the price")
        assert "rag_context"      in enriched
        assert "rag_context_text" in enriched

    def test_enrich_intent_empty_on_no_match(self, rag):
        intent = {"intent": INTENT_VIEW_SLOTS, "params": {}}
        enriched = rag.enrich_intent(intent, "zzzzzz")
        assert enriched["rag_context"]      == []
        assert enriched["rag_context_text"] == ""
