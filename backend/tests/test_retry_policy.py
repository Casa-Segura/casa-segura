"""CS-234 jitter tiers."""

from __future__ import annotations

import random

import pytest

from delivery.application.retry_policy import delay_seconds_for_completed_attempts


@pytest.mark.parametrize(
    ("completed_attempts", "expected_base"),
    [(1, 30), (2, 300), (3, 1800), (9, 1800)],
)
def test_retry_delay_tier_within_jitter_window(completed_attempts: int, expected_base: int):
    rng = random.Random(42)
    delay = delay_seconds_for_completed_attempts(completed_attempts, rng=rng)
    low = int(expected_base * 0.8)
    high = int(expected_base * 1.2)
    assert low <= delay <= high


def test_retry_delay_ordering_across_tiers():
    rng = random.Random(99)
    d1 = delay_seconds_for_completed_attempts(1, rng=rng)
    rng = random.Random(99)
    d2 = delay_seconds_for_completed_attempts(2, rng=rng)
    rng = random.Random(99)
    d3 = delay_seconds_for_completed_attempts(3, rng=rng)
    assert d1 < d2 < d3
