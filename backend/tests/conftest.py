"""
Shared pytest fixtures for the Smart Parking test suite.

Provides:
  - temp_data_file   : temporary parking_data.json with minimal test data
  - slot_service     : SlotService backed by the temp file
  - booking_service  : BookingService backed by slot_service
  - guardrails       : fresh Guardrails instance
  - rag_module       : RAGModule with empty knowledge base
  - flask_client     : Flask test client via create_app()
"""

import json
import tempfile
from pathlib import Path

import pytest

from mcp.guardrails import Guardrails
from mcp.rag_module import RAGModule
from services.booking_service import BookingService
from services.slot_service import SlotService
from utils.logger import get_logger

# ---------------------------------------------------------------------------
# Minimal test dataset
# ---------------------------------------------------------------------------
SAMPLE_DATA = {
    "locations": [
        {
            "id": "test-loc",
            "name": "Test Location",
            "address": "123 Test Street, Chennai",
            "totalSlots": 4,
            "ratePerHour": 20,
            "slots": [
                {"id": "TL-001", "status": "free"},
                {"id": "TL-002", "status": "free"},
                {"id": "TL-003", "status": "occupied", "booked_by": "SEED0001"},
                {"id": "TL-004", "status": "free"},
            ],
        }
    ]
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_data_file():
    """
    Write SAMPLE_DATA to a temporary JSON file.

    The file is removed automatically after each test.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as fh:
        json.dump(SAMPLE_DATA, fh, indent=2)
        tmp_path = Path(fh.name)

    yield tmp_path

    tmp_path.unlink(missing_ok=True)


@pytest.fixture
def slot_service(temp_data_file):
    """SlotService instance backed by the temporary data file."""
    return SlotService(temp_data_file)


@pytest.fixture
def booking_service(slot_service):
    """BookingService instance wired to the slot_service fixture."""
    return BookingService(slot_service)


@pytest.fixture
def guardrails():
    """Fresh Guardrails instance (clean rate-limit state)."""
    return Guardrails()


@pytest.fixture
def rag_module():
    """
    RAGModule with an empty knowledge base.

    Constructed without a file so the module gracefully falls back to
    an empty list — avoids any dependency on the real knowledge JSON.
    """
    module = RAGModule.__new__(RAGModule)
    module.knowledge_base = []
    module.knowledge_file = Path("nonexistent.json")
    module.logger = get_logger("rag_test")
    return module


@pytest.fixture
def flask_client(temp_data_file):
    """
    Flask test client backed by a fresh create_app() instance.

    Uses the temporary data file so tests are isolated.
    """
    from app import create_app

    application = create_app(data_file=temp_data_file)
    application.config["TESTING"] = True
    with application.test_client() as client:
        yield client
