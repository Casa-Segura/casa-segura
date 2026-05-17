"""Reputation façade wired from Django settings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

import structlog
from django.conf import settings

from project_verification.infrastructure.metrics import PROJECT_VERIFICATION_REPUTATION_OUTCOMES
from project_verification.reputation import adapters as rep_adapters
from project_verification.reputation.signals import ReputationSignals

logger = structlog.get_logger(__name__)


@runtime_checkable
class ReputationProvider(Protocol):
    def lookup(self, *, developer_slug: str, project_slug: str) -> ReputationSignals: ...


def _normalize_slug(fragment: str) -> str:
    alnum = "".join(ch if ch.isalnum() else " " for ch in (fragment or "").lower())
    return "-".join(p for p in alnum.split() if p)


def lookup_reputation_signals(*, developer: str, project: str) -> ReputationSignals:
    """Dispatch adapter from settings; SSRF defenses live inside adapters."""

    provider = getattr(settings, "PROJECT_REPUTATION_PROVIDER", "none") or "none"
    slug_dev = _normalize_slug(developer)[:96]
    slug_proj = _normalize_slug(project)[:96]

    if provider in ("none", ""):
        adapter_inst = rep_adapters.NoneReputationProvider()
    elif provider == "stub":
        adapter_inst = rep_adapters.StubReputationProvider()
    elif provider == "http":
        adapter_inst = rep_adapters.HttpReputationProvider()
    else:
        PROJECT_VERIFICATION_REPUTATION_OUTCOMES.labels(outcome="configuration_error").inc()
        logger.error("project_verification.reputation.unknown_adapter", stub=True)
        return ReputationSignals(
            outcome="failure",
            positive=False,
            negative=False,
            degraded=True,
            fetched_at=None,
            freshness_note_key=None,
        )

    try:
        out = adapter_inst.lookup(developer_slug=slug_dev, project_slug=slug_proj)
    except TimeoutError:
        PROJECT_VERIFICATION_REPUTATION_OUTCOMES.labels(outcome="timeout").inc()
        return ReputationSignals(
            outcome="timeout",
            positive=False,
            negative=False,
            degraded=True,
            fetched_at=datetime.now(tz=UTC),
            freshness_note_key="pv.reputation.timeout_note",
        )
    except Exception as exc:
        logger.warning(
            "project_verification.reputation.adapter_error",
            error_type=type(exc).__name__,
        )
        PROJECT_VERIFICATION_REPUTATION_OUTCOMES.labels(outcome="failure").inc()
        return ReputationSignals(
            outcome="failure",
            positive=False,
            negative=False,
            degraded=True,
            fetched_at=None,
            freshness_note_key=None,
        )

    outcome_label = (
        out.outcome if out.outcome in ("skipped_disabled", "success") else out.outcome[:16]
    )
    PROJECT_VERIFICATION_REPUTATION_OUTCOMES.labels(outcome=outcome_label[:16]).inc()

    return out


__all__ = ["ReputationProvider", "ReputationSignals", "lookup_reputation_signals"]
