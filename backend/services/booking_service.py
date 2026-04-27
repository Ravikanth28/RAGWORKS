"""
Booking Service
---------------
Business logic for creating and releasing parking bookings.

Booking records are kept in an in-memory dict (lost on restart).
Slot *occupancy* is persisted via SlotService → parking_data.json.

Auto-release: every booking schedules a ``threading.Timer`` that
automatically calls ``release_booking`` when the booking duration expires.
"""

import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from services.slot_service import SlotService
from utils.logger import get_logger


class BookingService:
    """
    Manages parking-slot bookings.

    Parameters
    ----------
    slot_service:
        Injected SlotService instance used for slot persistence.
    """

    def __init__(self, slot_service: SlotService):
        self.slot_service = slot_service
        self.logger       = get_logger(__name__)

        # In-memory stores (reset on restart)
        self._bookings: Dict[str, dict] = {}   # booking_id → booking dict
        self._timers:   Dict[str, threading.Timer] = {}  # booking_id → Timer

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_booking(
        self,
        location_id: str,
        duration: int,
        slot_id: Optional[str] = None,
    ) -> dict:
        """
        Create a new parking booking.

        Steps:
        1. Verify the location exists.
        2. Find / validate the target slot.
        3. Build the booking record.
        4. Mark the slot occupied via SlotService (persisted).
        5. Schedule an auto-release timer.

        Parameters
        ----------
        location_id:
            Canonical location ID.
        duration:
            Booking duration in hours (1–24).
        slot_id:
            Optional specific slot ID.  When ``None``, the first
            available slot is used.

        Returns
        -------
        dict
            Complete booking record.

        Raises
        ------
        ValueError
            If the location is not found, the requested slot is
            unavailable, or no free slots remain.
        """
        loc = self.slot_service.get_location(location_id)
        if not loc:
            raise ValueError(f"Location '{location_id}' not found.")

        # Resolve target slot
        if slot_id:
            target = self.slot_service.find_slot_by_id(location_id, slot_id)
            if not target:
                raise ValueError(f"Slot '{slot_id}' not found.")
            if target["status"] != "free":
                raise ValueError(f"Slot '{slot_id}' is not available.")
        else:
            target = self.slot_service.find_first_available_slot(location_id)
            if not target:
                raise ValueError("No slots available at this location.")

        # Build booking record
        booking_id = str(uuid.uuid4())[:8].upper()
        now        = datetime.now()
        expires_at = now + timedelta(hours=duration)
        cost       = duration * loc["ratePerHour"]

        booking: dict = {
            "booking_id":   booking_id,
            "location_id":  location_id,
            "location_name": loc["name"],
            "slot_id":      target["id"],
            "duration":     duration,
            "cost":         cost,
            "currency":     "₹",
            "booked_at":    now.isoformat(),
            "expires_at":   expires_at.isoformat(),
            "status":       "active",
        }

        # Persist slot state
        self.slot_service.mark_slot_occupied(location_id, target["id"], booking_id)
        self._bookings[booking_id] = booking

        # Schedule auto-release
        self._schedule_auto_release(booking_id, duration * 3600)

        self.logger.info(
            f"BookingService: created booking {booking_id} | "
            f"slot={target['id']} | location={location_id} | "
            f"duration={duration}h | cost=₹{cost}"
        )
        return booking

    # ------------------------------------------------------------------
    # Release
    # ------------------------------------------------------------------

    def release_booking(self, booking_id: str, auto: bool = False) -> bool:
        """
        Release an active booking and free its slot.

        Parameters
        ----------
        booking_id:
            ID of the booking to release.
        auto:
            ``True`` when triggered by the auto-release timer.

        Returns
        -------
        bool
            ``True`` on success, ``False`` if not found or already released.
        """
        booking = self._bookings.get(booking_id)
        if not booking or booking["status"] != "active":
            return False

        self.slot_service.mark_slot_free(booking["location_id"], booking["slot_id"])

        booking["status"]       = "released"
        booking["released_at"]  = datetime.now().isoformat()
        booking["auto_released"] = auto

        self._cancel_timer(booking_id)

        release_type = "auto" if auto else "manual"
        self.logger.info(
            f"BookingService: released ({release_type}) booking {booking_id} | "
            f"slot={booking['slot_id']}"
        )
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_booking(self, booking_id: str) -> Optional[dict]:
        """
        Retrieve a booking record by ID.

        Parameters
        ----------
        booking_id:
            Booking ID string.

        Returns
        -------
        dict or None
        """
        return self._bookings.get(booking_id)

    def get_active_bookings(self) -> List[dict]:
        """
        Return all currently active bookings.

        Returns
        -------
        List[dict]
        """
        return [b for b in self._bookings.values() if b["status"] == "active"]

    def find_booking_by_slot(self, slot_id: str) -> Optional[dict]:
        """
        Find the active booking that holds a given slot.

        Parameters
        ----------
        slot_id:
            Slot ID to search for.

        Returns
        -------
        dict or None
        """
        for booking in self._bookings.values():
            if booking["slot_id"] == slot_id and booking["status"] == "active":
                return booking
        return None

    # ------------------------------------------------------------------
    # Auto-release helpers
    # ------------------------------------------------------------------

    def _schedule_auto_release(self, booking_id: str, seconds: float) -> None:
        """Start a daemon timer that releases *booking_id* after *seconds*."""
        def _fire():
            self.logger.info(f"BookingService: auto-releasing booking {booking_id}")
            self.release_booking(booking_id, auto=True)

        timer = threading.Timer(seconds, _fire)
        timer.daemon = True
        timer.start()
        self._timers[booking_id] = timer

    def _cancel_timer(self, booking_id: str) -> None:
        """Cancel the pending auto-release timer for *booking_id* if any."""
        timer = self._timers.pop(booking_id, None)
        if timer:
            timer.cancel()
