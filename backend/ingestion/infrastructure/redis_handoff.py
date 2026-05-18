"""Ephemeral Redis JSON handoff from OCR (web worker) to Celery (pipeline worker).

Privacy: contract text is never logged. Keys use a fixed prefix and TTL.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import redis
import structlog
from django.conf import settings

logger = structlog.get_logger(__name__)

_KEY_PREFIX = "casasegura:ingest_handoff:"


def _handoff_redis_url() -> str:
    return getattr(settings, "INGEST_HANDOFF_REDIS_URL", None) or settings.CELERY_BROKER_URL


def _redis_client() -> redis.Redis:
    return redis.Redis.from_url(
        _handoff_redis_url(),
        socket_connect_timeout=2,
        socket_timeout=5,
    )


@dataclass(frozen=True)
class PipelineHandoffEnvelope:
    extracted_text: str
    delivery_channel: str
    delivery_target: str | None


def _key(submission_id: str) -> str:
    return f"{_KEY_PREFIX}{submission_id}"


def store_pipeline_handoff(submission_id: str, envelope: PipelineHandoffEnvelope) -> bool:
    """Serialize envelope to Redis with TTL. Returns False on Redis failure."""

    ttl = int(getattr(settings, "INGEST_HANDOFF_TTL_SECONDS", 300))
    payload = {
        "delivery_channel": envelope.delivery_channel,
        "delivery_target": envelope.delivery_target,
        "extracted_text": envelope.extracted_text,
    }
    try:
        raw = json.dumps(payload, ensure_ascii=False)
        client = _redis_client()
        client.set(_key(submission_id), raw.encode("utf-8"), ex=ttl)
        return True
    except Exception as exc:
        logger.error(
            "ingest.handoff_store_failed",
            submission_id=submission_id,
            error_class=exc.__class__.__name__,
        )
        return False


def delete_pipeline_handoff(submission_id: str) -> None:
    """Best-effort cleanup (e.g. claim race)."""

    try:
        _redis_client().delete(_key(submission_id))
    except Exception as exc:
        logger.warning(
            "ingest.handoff_delete_failed",
            submission_id=submission_id,
            error_class=exc.__class__.__name__,
        )


def _decode_handoff(raw: bytes | str | None) -> PipelineHandoffEnvelope | None:
    if raw is None:
        return None
    text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    extracted = (data.get("extracted_text") or "").strip()
    if not extracted:
        return None
    channel = (data.get("delivery_channel") or "web_link").strip().lower()
    target = data.get("delivery_target")
    tgt = target.strip() if isinstance(target, str) and target.strip() else None
    return PipelineHandoffEnvelope(
        extracted_text=extracted,
        delivery_channel=channel,
        delivery_target=tgt,
    )


def load_pipeline_handoff(submission_id: str) -> PipelineHandoffEnvelope | None:
    """Read handoff without deleting (supports Celery retries)."""

    try:
        client = _redis_client()
        raw = client.get(_key(submission_id))
        return _decode_handoff(raw)
    except Exception as exc:
        logger.error(
            "ingest.handoff_load_failed",
            submission_id=submission_id,
            error_class=exc.__class__.__name__,
        )
        return None


def pop_pipeline_handoff(submission_id: str) -> PipelineHandoffEnvelope | None:
    """Atomically read and remove handoff (tests / tooling)."""

    try:
        client = _redis_client()
        raw = client.getdel(_key(submission_id))
        return _decode_handoff(raw)
    except Exception as exc:
        logger.error(
            "ingest.handoff_pop_failed",
            submission_id=submission_id,
            error_class=exc.__class__.__name__,
        )
        return None


__all__ = [
    "PipelineHandoffEnvelope",
    "delete_pipeline_handoff",
    "load_pipeline_handoff",
    "pop_pipeline_handoff",
    "store_pipeline_handoff",
]
