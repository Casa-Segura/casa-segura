"""Service layer for CS-336.

Encapsulates hashing, validation, and rate-limit checks so the DRF view
stays thin.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock

from feedback.domain.enums import FeedbackCategory

PUBLIC_SHORT_ID_RX = re.compile(r"^CS-\d{4}-[A-Z0-9]{6}$")
RATE_LIMIT_WINDOW_SECONDS = 3600
RATE_LIMIT_PER_IP_PER_HOUR = 5
RATE_LIMIT_PER_SHORT_ID_PER_HOUR = 3
USER_AGENT_CAP = 200


def _hash_str(value: str | None) -> str | None:
    if not value:
        return None
    salt = os.environ.get("FEEDBACK_HASH_SALT", "casa-segura-feedback")
    digest = hashlib.sha256()
    digest.update(salt.encode("utf-8"))
    digest.update(b"|")
    digest.update(value.encode("utf-8"))
    return digest.hexdigest()


def hash_ip(ip: str) -> str:
    """Hash the IP for rate-limit + dedupe. Always returns a string."""

    return _hash_str(ip) or _hash_str("unknown")  # type: ignore[return-value]


def hash_email_or_none(email: str | None) -> str | None:
    if not email:
        return None
    return _hash_str(email.strip().lower())


def truncate_user_agent(ua: str | None) -> str | None:
    if not ua:
        return None
    return ua[:USER_AGENT_CAP]


def normalize_short_id(short_id: str | None) -> tuple[str | None, bool]:
    """Return ``(value, recognized_format)`` for a public short id.

    Unrecognized formats are stored as-is (CS-336 AC: "accepted with
    tag `unverified_id`") so the operator can triage later.
    """

    if not short_id:
        return None, False
    cleaned = short_id.strip().upper()
    return cleaned, bool(PUBLIC_SHORT_ID_RX.match(cleaned))


def is_valid_category(value: str | None) -> bool:
    if not value:
        return False
    try:
        FeedbackCategory(value)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int
    reason: str


class FeedbackRateLimiter:
    """In-process sliding-window rate limiter.

    Keyed by ``(ip_hash, short_id)`` — each axis enforces its own cap so
    a single user can't spam either path.
    """

    def __init__(
        self,
        *,
        per_ip_per_hour: int = RATE_LIMIT_PER_IP_PER_HOUR,
        per_short_id_per_hour: int = RATE_LIMIT_PER_SHORT_ID_PER_HOUR,
        window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
    ) -> None:
        self.per_ip = max(1, per_ip_per_hour)
        self.per_short_id = max(1, per_short_id_per_hour)
        self.window = window_seconds
        self._ip_window: dict[str, deque[float]] = {}
        self._short_id_window: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, *, ip_hash: str, short_id: str | None) -> RateLimitDecision:
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            ip_bucket = self._ip_window.setdefault(ip_hash, deque())
            while ip_bucket and ip_bucket[0] < cutoff:
                ip_bucket.popleft()
            if len(ip_bucket) >= self.per_ip:
                retry = int(self.window - (now - ip_bucket[0]))
                return RateLimitDecision(False, max(1, retry), "ip")

            if short_id:
                sid_bucket = self._short_id_window.setdefault(short_id, deque())
                while sid_bucket and sid_bucket[0] < cutoff:
                    sid_bucket.popleft()
                if len(sid_bucket) >= self.per_short_id:
                    retry = int(self.window - (now - sid_bucket[0]))
                    return RateLimitDecision(False, max(1, retry), "short_id")

            ip_bucket.append(now)
            if short_id:
                self._short_id_window.setdefault(short_id, deque()).append(now)
            return RateLimitDecision(True, 0, "ok")


# Process-wide instance used by the DRF view. Tests can construct their
# own limiter to assert window behavior in isolation.
default_limiter = FeedbackRateLimiter()


__all__ = [
    "PUBLIC_SHORT_ID_RX",
    "RATE_LIMIT_PER_IP_PER_HOUR",
    "RATE_LIMIT_PER_SHORT_ID_PER_HOUR",
    "RATE_LIMIT_WINDOW_SECONDS",
    "USER_AGENT_CAP",
    "FeedbackRateLimiter",
    "RateLimitDecision",
    "default_limiter",
    "hash_email_or_none",
    "hash_ip",
    "is_valid_category",
    "normalize_short_id",
    "truncate_user_agent",
]
