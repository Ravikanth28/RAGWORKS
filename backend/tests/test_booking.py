"""
Unit tests — Booking logic
==========================
Tests for BookingService and BookingAgent covering:

- Successful booking creation
- Auto-assigned vs. specific slot selection
- Duplicate / unavailable slot rejection
- Location-not-found error
- Booking release (manual)
- Active-bookings query
- BookingAgent guardrail enforcement (bad duration, bad location ID)
"""

import pytest

from agents.booking_agent import BookingAgent
from services.booking_service import BookingService


# ===========================================================================
# BookingService unit tests
# ===========================================================================

class TestBookingServiceCreate:
    """create_booking() happy-path and error cases."""

    def test_create_booking_returns_correct_fields(self, booking_service):
        """A successful booking has all expected fields."""
        booking = booking_service.create_booking("test-loc", 2)

        assert booking["status"]      == "active"
        assert booking["location_id"] == "test-loc"
        assert booking["duration"]    == 2
        assert booking["cost"]        == 40          # 2h × ₹20
        assert booking["currency"]    == "₹"
        assert "booking_id"  in booking
        assert "booked_at"   in booking
        assert "expires_at"  in booking

    def test_create_booking_picks_first_free_slot(self, booking_service, slot_service):
        """When no slot_id is specified, the first free slot is chosen."""
        booking = booking_service.create_booking("test-loc", 1)
        # TL-001 is the first free slot in SAMPLE_DATA
        assert booking["slot_id"] == "TL-001"

    def test_create_booking_specific_slot(self, booking_service):
        """Passing slot_id='TL-002' books that exact slot."""
        booking = booking_service.create_booking("test-loc", 1, slot_id="TL-002")
        assert booking["slot_id"] == "TL-002"

    def test_create_booking_marks_slot_occupied(self, booking_service, slot_service):
        """The slot's status is flipped to 'occupied' after booking."""
        booking_service.create_booking("test-loc", 1, slot_id="TL-001")
        slot = slot_service.find_slot_by_id("test-loc", "TL-001")
        assert slot["status"] == "occupied"

    def test_create_booking_unknown_location_raises(self, booking_service):
        """Booking at a non-existent location raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            booking_service.create_booking("nonexistent", 1)

    def test_create_booking_occupied_slot_raises(self, booking_service):
        """Requesting an already-occupied slot raises ValueError."""
        # TL-003 is pre-occupied in SAMPLE_DATA
        with pytest.raises(ValueError, match="not available"):
            booking_service.create_booking("test-loc", 1, slot_id="TL-003")

    def test_create_booking_no_free_slots_raises(self, booking_service):
        """Booking when all slots are occupied raises ValueError."""
        # Book all three free slots first
        booking_service.create_booking("test-loc", 1, slot_id="TL-001")
        booking_service.create_booking("test-loc", 1, slot_id="TL-002")
        booking_service.create_booking("test-loc", 1, slot_id="TL-004")

        with pytest.raises(ValueError, match="No slots available"):
            booking_service.create_booking("test-loc", 1)


class TestBookingServiceRelease:
    """release_booking() tests."""

    def test_release_booking_success(self, booking_service, slot_service):
        """Released booking has status='released' and slot becomes free."""
        booking = booking_service.create_booking("test-loc", 1)
        bid     = booking["booking_id"]

        assert booking_service.release_booking(bid) is True

        released = booking_service.get_booking(bid)
        assert released["status"] == "released"
        assert "released_at" in released

        slot = slot_service.find_slot_by_id("test-loc", booking["slot_id"])
        assert slot["status"] == "free"

    def test_release_nonexistent_booking_returns_false(self, booking_service):
        """Releasing an unknown booking ID returns False."""
        assert booking_service.release_booking("ZZZZZZZZ") is False

    def test_release_already_released_returns_false(self, booking_service):
        """Releasing a booking twice returns False on the second call."""
        booking = booking_service.create_booking("test-loc", 1)
        bid     = booking["booking_id"]
        booking_service.release_booking(bid)
        assert booking_service.release_booking(bid) is False

    def test_auto_release_flag(self, booking_service):
        """auto=True is stored in the booking record."""
        booking = booking_service.create_booking("test-loc", 1)
        booking_service.release_booking(booking["booking_id"], auto=True)
        released = booking_service.get_booking(booking["booking_id"])
        assert released["auto_released"] is True


class TestBookingServiceQueries:
    """get_active_bookings() and find_booking_by_slot()."""

    def test_get_active_bookings_empty_initially(self, booking_service):
        assert booking_service.get_active_bookings() == []

    def test_get_active_bookings_after_create(self, booking_service):
        booking_service.create_booking("test-loc", 1)
        active = booking_service.get_active_bookings()
        assert len(active) == 1
        assert active[0]["status"] == "active"

    def test_released_booking_not_in_active(self, booking_service):
        booking = booking_service.create_booking("test-loc", 1)
        booking_service.release_booking(booking["booking_id"])
        assert booking_service.get_active_bookings() == []

    def test_find_booking_by_slot(self, booking_service):
        booking = booking_service.create_booking("test-loc", 1, slot_id="TL-001")
        found   = booking_service.find_booking_by_slot("TL-001")
        assert found is not None
        assert found["booking_id"] == booking["booking_id"]

    def test_find_booking_by_slot_none_when_free(self, booking_service):
        assert booking_service.find_booking_by_slot("TL-001") is None


# ===========================================================================
# BookingAgent unit tests
# ===========================================================================

class TestBookingAgent:
    """BookingAgent guardrail and delegation tests."""

    @pytest.fixture
    def agent(self, booking_service, slot_service, guardrails):
        return BookingAgent(booking_service, slot_service, guardrails)

    def test_book_success(self, agent):
        result = agent.book("test-loc", 2)
        assert "booking" in result
        assert result["booking"]["duration"] == 2

    def test_book_invalid_duration_zero(self, agent):
        result = agent.book("test-loc", 0)
        assert "error" in result

    def test_book_invalid_duration_too_long(self, agent):
        result = agent.book("test-loc", 25)
        assert "error" in result

    def test_book_invalid_location_id_format(self, agent):
        result = agent.book("../etc/passwd", 1)
        assert "error" in result

    def test_book_nonexistent_location(self, agent):
        result = agent.book("nowhere", 1)
        assert "error" in result

    def test_release_by_booking_id(self, agent):
        booking = agent.book("test-loc", 1)["booking"]
        result  = agent.release(booking_id=booking["booking_id"])
        assert "message" in result
        assert "error"   not in result

    def test_release_by_slot_id(self, agent):
        agent.book("test-loc", 1, slot_id="TL-002")
        result = agent.release(slot_id="TL-002")
        assert "message" in result

    def test_release_unknown_booking(self, agent):
        result = agent.release(booking_id="ZZZZZZZZ")
        assert "error" in result
