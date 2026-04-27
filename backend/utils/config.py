"""
Global configuration constants for the Smart Parking application.

All tuneable parameters are centralised here so they can be changed
in one place without hunting through the codebase.
"""

from pathlib import Path


class Config:
    """Application-wide configuration values."""

    # ---------------------------------------------------------------------------
    # File paths
    # ---------------------------------------------------------------------------
    BASE_DIR: Path = Path(__file__).parent.parent          # backend/
    DATA_FILE: Path = BASE_DIR / "parking_data.json"
    KNOWLEDGE_FILE: Path = BASE_DIR / "parking_knowledge.json"

    # ---------------------------------------------------------------------------
    # Booking constraints
    # ---------------------------------------------------------------------------
    MIN_DURATION_HOURS: int = 1
    MAX_DURATION_HOURS: int = 24

    # ---------------------------------------------------------------------------
    # Rate limiting  (simple sliding-window, per client IP)
    # ---------------------------------------------------------------------------
    RATE_LIMIT_REQUESTS: int = 30        # max requests allowed
    RATE_LIMIT_WINDOW_SECONDS: int = 60  # per this many seconds

    # ---------------------------------------------------------------------------
    # NLP / MCP thresholds
    # ---------------------------------------------------------------------------
    NLP_MIN_CONFIDENCE: float = 0.4   # minimum confidence to execute an intent

    # ---------------------------------------------------------------------------
    # Logging
    # ---------------------------------------------------------------------------
    LOG_LEVEL: str = "DEBUG"
