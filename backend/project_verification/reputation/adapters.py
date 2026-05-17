"""Concrete reputation adapters."""

from __future__ import annotations

import ipaddress
import json
import socket
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from django.conf import settings

from project_verification.reputation.signals import ReputationSignals

logger = structlog.get_logger(__name__)


class NoneReputationProvider:
    def lookup(self, *, developer_slug: str, project_slug: str) -> ReputationSignals:
        del developer_slug, project_slug
        return ReputationSignals(
            outcome="skipped_disabled",
            positive=False,
            negative=False,
            degraded=False,
            fetched_at=None,
            freshness_note_key=None,
        )


class StubReputationProvider:
    """Deterministic excerpt for QA — bounded, no outbound I/O."""

    def lookup(self, *, developer_slug: str, project_slug: str) -> ReputationSignals:
        neg = developer_slug.endswith("risk") or "alerta" in project_slug
        pos = developer_slug.endswith("confiable")
        fetched = datetime.now(tz=UTC)
        return ReputationSignals(
            outcome="success",
            positive=bool(pos),
            negative=bool(neg),
            degraded=False,
            fetched_at=fetched,
            freshness_note_key="pv.reputation.freshness.stub",
        )


class HttpReputationProvider:
    """Optional HTTP enrichment with host allowlisting + SSRF guard (CS-353)."""

    def lookup(self, *, developer_slug: str, project_slug: str) -> ReputationSignals:
        base_raw = getattr(settings, "PROJECT_REPUTATION_HTTP_BASE_URL", "") or ""
        base = base_raw.strip()
        if not base:
            raise RuntimeError("PROJECT_REPUTATION_HTTP_BASE_URL is required for provider=http")

        allow_raw = getattr(settings, "PROJECT_REPUTATION_HTTP_ALLOW_HOSTS", "") or ""
        allow_hosts = frozenset(h.strip().lower() for h in allow_raw.split(",") if h.strip())

        url = base.rstrip("/") + "/project-verification/reputation-snippet/"
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()

        if not host or host not in allow_hosts:
            raise RuntimeError("reputation_http_host_denied")

        self._guard_resolved_ips(host)

        timeout = float(getattr(settings, "PROJECT_REPUTATION_HTTP_TIMEOUT_SECONDS", 5.0))
        params = {"d": developer_slug[:64], "p": project_slug[:64]}
        logger.info(
            "project_verification.reputation.http_request",
            host=host,
            path=parsed.path,
        )
        resp = httpx.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()

        fetched = datetime.now(tz=UTC)
        outcome = payload.get("outcome") or "success"

        signals = dict(payload.get("signals") or {})

        fk = payload.get("freshness_note_key")
        return ReputationSignals(
            outcome=str(outcome),
            positive=bool(signals.get("positive")),
            negative=bool(signals.get("negative")),
            degraded=False,
            fetched_at=fetched,
            freshness_note_key=str(fk) if fk else None,
        )

    @staticmethod
    def _guard_resolved_ips(host: str) -> None:
        try:
            infos = socket.getaddrinfo(host, None)
        except OSError as exc:
            raise RuntimeError("reputation_dns_failed") from exc

        for info in infos:
            sockaddr = info[4]
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                raise RuntimeError("ssrf_blocked_resolved") from None

            if bool(getattr(ip, "is_global", False)) is False:
                raise RuntimeError("ssrf_blocked_resolved") from None


def safe_json_hints(payload_text: str) -> dict[str, Any]:
    """Parse bounded snippets for stubs/testing."""

    trimmed = payload_text.strip()[:2000]
    try:
        return dict(json.loads(trimmed))
    except json.JSONDecodeError:
        return {}
