"""Liveness + readiness endpoints (CS-008).

`/health`  — process liveness. Always 200 in <50ms, no DB hits. Container
             healthchecks rely on this.
`/ready`   — process + dependency readiness. Pings DB (SELECT 1) and Redis
             when configured. Returns 503 with `reason` codes on failure.

Both emit structlog records with `correlation_id` already bound by
`CorrelationIdMiddleware`."""

from __future__ import annotations

import socket
from urllib.parse import urlparse

import redis
import structlog
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django.conf import settings
from django.db import OperationalError, connection

from shared.observability.logging import SCHEMA_VERSION, SERVICE_NAME

logger = structlog.get_logger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(_request):
    """Liveness probe. No external dependencies; <50ms target."""
    return Response(
        {
            "status": "ok",
            "service": SERVICE_NAME,
            "schema_version": SCHEMA_VERSION,
            "hostname": socket.gethostname(),
        }
    )


def _check_database() -> tuple[bool, str | None]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, None
    except OperationalError as exc:
        return False, f"db_unreachable: {exc.__class__.__name__}"
    except Exception as exc:  # noqa: BLE001 — readiness must never crash
        return False, f"db_error: {exc.__class__.__name__}"


def _check_redis() -> tuple[bool, str | None]:
    url = getattr(settings, "CELERY_BROKER_URL", "")
    if not url or not url.startswith(("redis://", "rediss://")):
        return True, None  # Redis not configured -> not gating readiness
    try:
        parsed = urlparse(url)
        client = redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            db=int((parsed.path or "/0").lstrip("/") or 0),
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, f"redis_unreachable: {exc.__class__.__name__}"


@api_view(["GET"])
@permission_classes([AllowAny])
def ready(_request):
    """Readiness probe. Returns 503 if any required dependency is unreachable."""
    db_ok, db_reason = _check_database()
    redis_ok, redis_reason = _check_redis()

    reasons: list[str] = []
    if not db_ok and db_reason:
        reasons.append(db_reason)
    if not redis_ok and redis_reason:
        reasons.append(redis_reason)

    overall_ok = db_ok and redis_ok
    payload = {
        "status": "ok" if overall_ok else "not_ready",
        "schema_version": SCHEMA_VERSION,
        "checks": {
            "database": "ok" if db_ok else "fail",
            "redis": "ok" if redis_ok else "fail",
        },
        "reasons": reasons,
    }
    if not overall_ok:
        logger.warning("readiness_check_failed", checks=payload["checks"], reasons=reasons)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(payload)
