"""
Integration tests — REST API endpoints
=======================================
Tests each Flask endpoint through the test client provided by the
``flask_client`` fixture (from conftest.py).

The test client is backed by a fresh ``create_app()`` instance using a
temporary copy of the parking data, so tests are fully isolated from
the production data file.
"""

import json
import pytest


# ===========================================================================
# GET /api/locations
# ===========================================================================

class TestGetLocations:

    def test_returns_200(self, flask_client):
        resp = flask_client.get("/api/locations")
        assert resp.status_code == 200

    def test_response_has_locations_key(self, flask_client):
        data = flask_client.get("/api/locations").get_json()
        assert "locations" in data

    def test_location_has_required_fields(self, flask_client):
        loc  = flask_client.get("/api/locations").get_json()["locations"][0]
        for field in ("id", "name", "address", "totalSlots", "availableSlots", "ratePerHour"):
            assert field in loc, f"Missing field: {field}"

    def test_available_slots_count_is_correct(self, flask_client):
        """SAMPLE_DATA has 3 free slots (TL-001, TL-002, TL-004)."""
        loc = flask_client.get("/api/locations").get_json()["locations"][0]
        assert loc["availableSlots"] == 3


# ===========================================================================
# GET /api/slots
# ===========================================================================

class TestGetSlots:

    def test_returns_200_for_valid_location(self, flask_client):
        resp = flask_client.get("/api/slots?location=test-loc")
        assert resp.status_code == 200

    def test_returns_400_when_location_missing(self, flask_client):
        resp = flask_client.get("/api/slots")
        assert resp.status_code == 400

    def test_returns_404_for_unknown_location(self, flask_client):
        resp = flask_client.get("/api/slots?location=nonexistent")
        assert resp.status_code == 404

    def test_response_contains_slots(self, flask_client):
        data = flask_client.get("/api/slots?location=test-loc").get_json()
        assert "slots" in data
        assert len(data["slots"]) == 4   # SAMPLE_DATA has 4 slots

    def test_occupied_slot_has_booking_id(self, flask_client):
        """TL-003 is pre-occupied in SAMPLE_DATA with booked_by='SEED0001'."""
        data  = flask_client.get("/api/slots?location=test-loc").get_json()
        slots = {s["id"]: s for s in data["slots"]}
        assert slots["TL-003"]["status"] == "occupied"
        assert "booking_id" in slots["TL-003"]


# ===========================================================================
# POST /api/book
# ===========================================================================

class TestBookSlot:

    def _book(self, client, location="test-loc", duration=1, slot_id=None):
        payload = {"location": location, "duration": duration}
        if slot_id:
            payload["slot_id"] = slot_id
        return client.post(
            "/api/book",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_book_returns_201(self, flask_client):
        resp = self._book(flask_client)
        assert resp.status_code == 201

    def test_book_response_has_booking(self, flask_client):
        data = self._book(flask_client).get_json()
        assert "booking" in data

    def test_book_booking_id_in_response(self, flask_client):
        data = self._book(flask_client).get_json()
        assert "booking_id" in data["booking"]

    def test_book_specific_slot(self, flask_client):
        data = self._book(flask_client, slot_id="TL-002").get_json()
        assert data["booking"]["slot_id"] == "TL-002"

    def test_book_returns_400_missing_location(self, flask_client):
        resp = flask_client.post(
            "/api/book",
            data=json.dumps({"duration": 1}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_book_returns_400_missing_duration(self, flask_client):
        resp = flask_client.post(
            "/api/book",
            data=json.dumps({"location": "test-loc"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_book_invalid_duration_rejected(self, flask_client):
        resp = self._book(flask_client, duration=0)
        assert resp.status_code in (400, 409)

    def test_book_occupied_slot_returns_409(self, flask_client):
        """TL-003 is already occupied."""
        resp = self._book(flask_client, slot_id="TL-003")
        assert resp.status_code == 409

    def test_book_reduces_available_slots(self, flask_client):
        before = flask_client.get("/api/locations").get_json()["locations"][0]["availableSlots"]
        self._book(flask_client)
        after  = flask_client.get("/api/locations").get_json()["locations"][0]["availableSlots"]
        assert after == before - 1

    def test_book_mcp_intent_in_response(self, flask_client):
        data = self._book(flask_client).get_json()
        assert "mcp_intent" in data


# ===========================================================================
# POST /api/release
# ===========================================================================

class TestReleaseSlot:

    def _book(self, client):
        resp = client.post(
            "/api/book",
            data=json.dumps({"location": "test-loc", "duration": 1}),
            content_type="application/json",
        )
        return resp.get_json()["booking"]

    def test_release_by_booking_id_returns_200(self, flask_client):
        booking = self._book(flask_client)
        resp = flask_client.post(
            "/api/release",
            data=json.dumps({"booking_id": booking["booking_id"]}),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_release_returns_message(self, flask_client):
        booking = self._book(flask_client)
        data = flask_client.post(
            "/api/release",
            data=json.dumps({"booking_id": booking["booking_id"]}),
            content_type="application/json",
        ).get_json()
        assert "message" in data

    def test_release_increases_available_slots(self, flask_client):
        booking = self._book(flask_client)
        before  = flask_client.get("/api/locations").get_json()["locations"][0]["availableSlots"]
        flask_client.post(
            "/api/release",
            data=json.dumps({"booking_id": booking["booking_id"]}),
            content_type="application/json",
        )
        after = flask_client.get("/api/locations").get_json()["locations"][0]["availableSlots"]
        assert after == before + 1

    def test_release_unknown_booking_returns_404(self, flask_client):
        resp = flask_client.post(
            "/api/release",
            data=json.dumps({"booking_id": "ZZZZZZZZ"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_release_missing_ids_returns_400(self, flask_client):
        resp = flask_client.post(
            "/api/release",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ===========================================================================
# GET /api/bookings
# ===========================================================================

class TestGetBookings:

    def test_returns_200(self, flask_client):
        resp = flask_client.get("/api/bookings")
        assert resp.status_code == 200

    def test_empty_initially(self, flask_client):
        data = flask_client.get("/api/bookings").get_json()
        assert data["bookings"] == []

    def test_booking_appears_after_create(self, flask_client):
        flask_client.post(
            "/api/book",
            data=json.dumps({"location": "test-loc", "duration": 1}),
            content_type="application/json",
        )
        data = flask_client.get("/api/bookings").get_json()
        assert len(data["bookings"]) == 1


# ===========================================================================
# GET /api/booking/<id>
# ===========================================================================

class TestGetBookingById:

    def test_returns_booking_for_valid_id(self, flask_client):
        created = flask_client.post(
            "/api/book",
            data=json.dumps({"location": "test-loc", "duration": 1}),
            content_type="application/json",
        ).get_json()["booking"]

        resp = flask_client.get(f"/api/booking/{created['booking_id']}")
        assert resp.status_code == 200
        assert resp.get_json()["booking"]["booking_id"] == created["booking_id"]

    def test_returns_404_for_unknown_id(self, flask_client):
        resp = flask_client.get("/api/booking/ZZZZZZZZ")
        assert resp.status_code == 404


# ===========================================================================
# POST /api/nlp
# ===========================================================================

class TestNLPEndpoint:

    def _nlp(self, client, text):
        return client.post(
            "/api/nlp",
            data=json.dumps({"text": text}),
            content_type="application/json",
        )

    def test_returns_200(self, flask_client):
        resp = self._nlp(flask_client, "Show slots at test-loc")
        assert resp.status_code == 200

    def test_returns_400_empty_text(self, flask_client):
        resp = flask_client.post(
            "/api/nlp",
            data=json.dumps({"text": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_parsed_field_in_response(self, flask_client):
        data = self._nlp(flask_client, "Book parking near mall for 2 hours").get_json()
        assert "parsed" in data

    def test_book_intent_returns_prefill(self, flask_client):
        data = self._nlp(flask_client, "Book parking near mall for 2 hours").get_json()
        assert data.get("action") == "book"
        assert "prefill" in data

    def test_trace_id_present(self, flask_client):
        data = self._nlp(flask_client, "Show slots at anna nagar").get_json()
        assert "trace_id" in data

    def test_low_confidence_returns_fallback_message(self, flask_client):
        data = self._nlp(flask_client, "hello world goodbye").get_json()
        assert "message" in data
