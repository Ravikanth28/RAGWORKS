"""
Logging utility with request trace-ID injection for full observability.

Every log record carries a `trace_id` field so that all log lines
belonging to a single HTTP request can be correlated across modules.

Usage
-----
    from utils.logger import get_logger, generate_trace_id

    logger = get_logger(__name__, trace_id="ABC123")
    logger.info("Something happened")
    # → 2026-04-27 10:00:00 [services.booking_service] [INFO] [trace=ABC123] Something happened
"""

import logging
import sys
import uuid
from typing import Optional


# ---------------------------------------------------------------------------
# Trace-ID filter
# ---------------------------------------------------------------------------

class _TraceFilter(logging.Filter):
    """Injects ``trace_id`` into every LogRecord."""

    def __init__(self, trace_id: str = ""):
        super().__init__()
        self.trace_id = trace_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = self.trace_id
        return True


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def generate_trace_id() -> str:
    """
    Generate a short, unique trace ID for one HTTP request.

    Returns
    -------
    str
        8-character uppercase hex string, e.g. ``"A3F9BC12"``.
    """
    return str(uuid.uuid4())[:8].upper()


def get_logger(name: str, trace_id: Optional[str] = None) -> logging.Logger:
    """
    Return a configured logger that stamps every record with *trace_id*.

    If the logger for *name* has no handlers yet, a ``StreamHandler``
    writing to stdout is added.  Subsequent calls with the same *name*
    reuse the existing logger but update its trace filter.

    Parameters
    ----------
    name:
        Logger name — typically ``__name__`` of the calling module.
    trace_id:
        Optional request-scoped trace identifier for log correlation.

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(name)

    # Attach a handler only once per logger
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(name)s] [%(levelname)s] [trace=%(trace_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

    # Replace any existing trace filter with a fresh one
    for f in list(logger.filters):
        logger.removeFilter(f)
    logger.addFilter(_TraceFilter(trace_id or ""))

    return logger
