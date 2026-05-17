"""Backoff schedule — CS-234."""

from __future__ import annotations

import random
from datetime import timedelta
from typing import Final

from django.utils import timezone

# Ordered backoff tiers between attempts (seconds), ±20% jitter.
_DELAY_SECONDS: Final[tuple[int, ...]] = (30, 300, 1800)
_JITTER_LOW: Final[float] = 0.8
_JITTER_HIGH: Final[float] = 1.2


def jitter_multiplier(rng: random.Random) -> float:
    return rng.uniform(_JITTER_LOW, _JITTER_HIGH)


def delay_seconds_for_completed_attempts(completed_attempt_count: int, rng: random.Random | None = None) -> int:
    """Return delay before the next retry after `completed_attempt_count` failures."""
    # Randomness is for retry jitter only (not cryptographic).
    r = rng or random.Random()  # noqa: S311
    if completed_attempt_count < 1:
        tier_idx = 0
    else:
        tier_idx = min(completed_attempt_count - 1, len(_DELAY_SECONDS) - 1)
    base = _DELAY_SECONDS[tier_idx]
    jittered = int(base * jitter_multiplier(r))
    return max(jittered, 1)


def next_attempt_not_before(*, completed_attempt_count: int, rng: random.Random | None = None):
    delta_s = delay_seconds_for_completed_attempts(completed_attempt_count, rng=rng)
    return timezone.now() + timedelta(seconds=delta_s)
