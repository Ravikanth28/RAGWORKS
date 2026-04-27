"""
Slot Service
------------
Data-access layer for parking locations and their slots.

All file I/O is concentrated here so the rest of the application
never touches ``parking_data.json`` directly.  A threading lock
protects concurrent writes from racing.
"""

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

from utils.logger import get_logger


class SlotService:
    """
    Manages parking slot data backed by a JSON file.

    Parameters
    ----------
    data_file:
        Path to the ``parking_data.json`` persistence file.
    """

    def __init__(self, data_file: Path):
        self.data_file = data_file
        self.logger    = get_logger(__name__)
        self._lock     = threading.Lock()
        self._data: Dict = {}
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load parking data from the JSON file into memory."""
        with open(self.data_file, "r", encoding="utf-8") as f:
            self._data = json.load(f)
        self.logger.info(f"SlotService: loaded data from '{self.data_file.name}'")

    def save(self) -> None:
        """Persist the current in-memory state back to the JSON file."""
        with self._lock:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)

    # ------------------------------------------------------------------
    # Location queries
    # ------------------------------------------------------------------

    def get_all_locations(self) -> List[dict]:
        """
        Return all locations with real-time available-slot counts.

        Returns
        -------
        List[dict]
            Each dict contains: id, name, address, totalSlots,
            availableSlots, ratePerHour.
        """
        result = []
        for loc in self._data.get("locations", []):
            free = sum(1 for s in loc["slots"] if s["status"] == "free")
            result.append(
                {
                    "id":             loc["id"],
                    "name":           loc["name"],
                    "address":        loc["address"],
                    "totalSlots":     loc["totalSlots"],
                    "availableSlots": free,
                    "ratePerHour":    loc["ratePerHour"],
                }
            )
        return result

    def get_location(self, location_id: str) -> Optional[dict]:
        """
        Find a location by its ID.

        Parameters
        ----------
        location_id:
            Canonical location ID (e.g. ``"anna-nagar"``).

        Returns
        -------
        dict or None
        """
        for loc in self._data.get("locations", []):
            if loc["id"] == location_id:
                return loc
        return None

    def get_slots_for_location(self, location_id: str) -> Optional[dict]:
        """
        Build the full slot-detail response payload for one location.

        Parameters
        ----------
        location_id:
            Canonical location ID.

        Returns
        -------
        dict or None
            Dict ready to be returned as a JSON response, or ``None``
            if the location does not exist.
        """
        loc = self.get_location(location_id)
        if not loc:
            return None

        free  = sum(1 for s in loc["slots"] if s["status"] == "free")
        slots = []
        for slot in loc["slots"]:
            entry: dict = {"id": slot["id"], "status": slot["status"]}
            if slot["status"] == "occupied" and "booked_by" in slot:
                entry["booking_id"] = slot["booked_by"]
            slots.append(entry)

        return {
            "location":       loc["name"],
            "location_id":    loc["id"],
            "address":        loc["address"],
            "ratePerHour":    loc["ratePerHour"],
            "totalSlots":     loc["totalSlots"],
            "availableSlots": free,
            "mapImageUrl":    loc.get("mapImageUrl", ""),
            "slots":          slots,
        }

    # ------------------------------------------------------------------
    # Slot queries
    # ------------------------------------------------------------------

    def find_first_available_slot(self, location_id: str) -> Optional[dict]:
        """
        Return the first slot with ``status == "free"`` in a location.

        Parameters
        ----------
        location_id:
            Canonical location ID.

        Returns
        -------
        dict or None
        """
        loc = self.get_location(location_id)
        if not loc:
            return None
        for slot in loc["slots"]:
            if slot["status"] == "free":
                return slot
        return None

    def find_slot_by_id(self, location_id: str, slot_id: str) -> Optional[dict]:
        """
        Look up a specific slot by its ID within a location.

        Parameters
        ----------
        location_id:
            Canonical location ID.
        slot_id:
            Slot ID (e.g. ``"AN-001"``).

        Returns
        -------
        dict or None
        """
        loc = self.get_location(location_id)
        if not loc:
            return None
        for slot in loc["slots"]:
            if slot["id"] == slot_id:
                return slot
        return None

    # ------------------------------------------------------------------
    # Slot mutations
    # ------------------------------------------------------------------

    def mark_slot_occupied(
        self, location_id: str, slot_id: str, booking_id: str
    ) -> bool:
        """
        Mark a slot as *occupied* and record which booking holds it.

        Parameters
        ----------
        location_id:
            Canonical location ID.
        slot_id:
            Target slot ID.
        booking_id:
            Booking ID to associate with the slot.

        Returns
        -------
        bool
            ``True`` on success, ``False`` if the slot was not found.
        """
        slot = self.find_slot_by_id(location_id, slot_id)
        if not slot:
            return False
        slot["status"]    = "occupied"
        slot["booked_by"] = booking_id
        self.save()
        self.logger.debug(
            f"SlotService: slot {slot_id} marked occupied by booking {booking_id}"
        )
        return True

    def mark_slot_free(self, location_id: str, slot_id: str) -> bool:
        """
        Mark a slot as *free* and remove any booking reference.

        Parameters
        ----------
        location_id:
            Canonical location ID.
        slot_id:
            Target slot ID.

        Returns
        -------
        bool
            ``True`` on success, ``False`` if the slot was not found.
        """
        slot = self.find_slot_by_id(location_id, slot_id)
        if not slot:
            return False
        slot["status"] = "free"
        slot.pop("booked_by", None)
        self.save()
        self.logger.debug(f"SlotService: slot {slot_id} marked free")
        return True
