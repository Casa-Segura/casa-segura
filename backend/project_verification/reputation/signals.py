"""Shared dataclasses for optional reputation hints (EPIC-12 / CS-353)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class ReputationSignals:
    """Bounded evidence for synthesis (never adjudication)."""

    outcome: str
    positive: bool
    negative: bool
    degraded: bool
    fetched_at: datetime | None
    freshness_note_key: str | None
