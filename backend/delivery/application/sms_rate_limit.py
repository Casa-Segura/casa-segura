"""Shared token-bucket style limiter for outbound SMS — CS-241."""

from __future__ import annotations

import time

from django.conf import settings
from django.core.cache import cache


def sms_send_allowed() -> bool:
    """Return False when this process/instance exceeds per-second SMS cap."""

    cap = int(getattr(settings, "SMS_MAX_SENDS_PER_SECOND", 5))
    if cap <= 0:
        return True
    slot = int(time.time())
    key = f"sms:rate:{slot}"
    try:
        n = cache.incr(key)
    except ValueError:
        cache.add(key, 1, timeout=2)
        n = 1
    return n <= cap
