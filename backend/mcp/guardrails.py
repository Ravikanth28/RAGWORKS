"""
MCP Guardrails
--------------
Safety and validation layer that sits in front of the intent engine
and booking logic.

Responsibilities
~~~~~~~~~~~~~~~~
* Sanitise free-text input (length, suspicious patterns).
* Enforce duration bounds.
* Validate location-ID format.
* Rate-limit clients via an in-memory sliding-window counter.

All checks return ``(bool, str)`` so callers decide how to respond.
"""

import re
import time
from collections import defaultdict
from typing import Tuple

from utils.config import Config
from utils.logger import get_logger


class Guardrails:
    """
    Input validation and rate-limiting guardrails for the MCP pipeline.

    The rate-limiter state is per-instance (in-memory), so it resets
    whenever the application restarts.  For production use, replace
    ``_rate_store`` with a Redis-backed solution.
    """

    # Patterns that indicate injection or abuse attempts
    _SUSPICIOUS_PATTERNS = [
        r"<[^>]+>",                                         # HTML tags
        r"javascript\s*:",                                  # JS injection
        r"(drop|delete|insert|update|select)\s+\w+",       # SQL keywords
        r"__[a-zA-Z]+__",                                   # Python dunders
        r"\.\./",                                           # Path traversal
    ]

    def __init__(self):
        self.logger = get_logger(__name__)
        # sliding-window store: { client_ip -> [timestamp, ...] }
        self._rate_store: dict = defaultdict(list)

    # ------------------------------------------------------------------
    # Text input
    # ------------------------------------------------------------------

    def validate_text_input(self, text: str) -> Tuple[bool, str]:
        """
        Validate and sanitise a raw text input from the user.

        Checks:
        - Not empty
        - Not longer than 500 characters
        - No suspicious/injection patterns

        Parameters
        ----------
        text:
            Raw user input string.

        Returns
        -------
        (is_valid, message)
        """
        if not text or not text.strip():
            return False, "Input text cannot be empty."

        if len(text) > 500:
            return False, "Input text is too long (max 500 characters)."

        for pattern in self._SUSPICIOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.warning(
                    f"Guardrails: suspicious pattern detected — '{text[:60]}'"
                )
                return False, "Input contains disallowed content."

        return True, "OK"

    # ------------------------------------------------------------------
    # Duration
    # ------------------------------------------------------------------

    def validate_duration(self, duration) -> Tuple[bool, str]:
        """
        Validate that *duration* is an integer within [MIN, MAX] hours.

        Parameters
        ----------
        duration:
            Value to check — may be int, float, or string.

        Returns
        -------
        (is_valid, message)
        """
        try:
            duration = int(duration)
        except (ValueError, TypeError):
            return False, "Duration must be a valid integer."

        if duration < Config.MIN_DURATION_HOURS:
            return False, f"Duration must be at least {Config.MIN_DURATION_HOURS} hour."
        if duration > Config.MAX_DURATION_HOURS:
            return False, f"Duration cannot exceed {Config.MAX_DURATION_HOURS} hours."

        return True, "OK"

    # ------------------------------------------------------------------
    # Location ID
    # ------------------------------------------------------------------

    def sanitize_location_id(self, location_id: str) -> Tuple[bool, str]:
        """
        Validate that *location_id* is a safe, expected format.

        Only alphanumeric characters and hyphens are allowed (max 50 chars).

        Parameters
        ----------
        location_id:
            Location ID string from the request.

        Returns
        -------
        (is_valid, message)
        """
        if not location_id:
            return False, "Location ID is required."

        if not re.match(r"^[a-zA-Z0-9\-]{1,50}$", location_id):
            return False, "Invalid location ID format."

        return True, "OK"

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def check_rate_limit(self, client_ip: str) -> Tuple[bool, str]:
        """
        Check whether *client_ip* has exceeded the configured rate limit.

        Uses a sliding-window algorithm:
        - Maximum ``Config.RATE_LIMIT_REQUESTS`` requests
        - Per ``Config.RATE_LIMIT_WINDOW_SECONDS`` seconds

        Parameters
        ----------
        client_ip:
            Client IP address string.

        Returns
        -------
        (is_allowed, message)
        """
        now          = time.time()
        window_start = now - Config.RATE_LIMIT_WINDOW_SECONDS

        # Evict expired timestamps
        self._rate_store[client_ip] = [
            ts for ts in self._rate_store[client_ip] if ts > window_start
        ]

        if len(self._rate_store[client_ip]) >= Config.RATE_LIMIT_REQUESTS:
            self.logger.warning(f"Guardrails: rate limit exceeded for IP {client_ip}")
            return (
                False,
                f"Rate limit exceeded. Max {Config.RATE_LIMIT_REQUESTS} requests "
                f"per {Config.RATE_LIMIT_WINDOW_SECONDS}s.",
            )

        self._rate_store[client_ip].append(now)
        return True, "OK"
