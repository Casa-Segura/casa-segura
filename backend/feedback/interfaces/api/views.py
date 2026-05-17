"""DRF entry point for CS-336 — user error / discrepancy reports."""

from __future__ import annotations

import structlog
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from feedback.application.services import (
    default_limiter,
    hash_email_or_none,
    hash_ip,
    is_valid_category,
    normalize_short_id,
    truncate_user_agent,
)
from feedback.domain.enums import FeedbackCategory
from feedback.infrastructure.django.models import MAX_DESCRIPTION_CHARS, UserErrorReport

logger = structlog.get_logger(__name__)


class ErrorReportView(APIView):
    """``POST /api/v1/feedback/error-reports/``.

    Accepts the discrepancy payload, rate-limits, hashes PII, persists.
    Returns 201 on success, 400 on validation failure, 429 on rate-limit.
    """

    authentication_classes: tuple = ()
    permission_classes: tuple = ()

    def post(self, request: Request) -> Response:
        payload = request.data if isinstance(request.data, dict) else {}
        category = (payload.get("category") or "").strip()
        if not is_valid_category(category):
            return Response(
                {"error": "invalid_category", "allowed": [c.value for c in FeedbackCategory]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        description = (payload.get("description") or "").strip()
        if not description:
            return Response(
                {"error": "description_required", "max_chars": MAX_DESCRIPTION_CHARS},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(description) > MAX_DESCRIPTION_CHARS:
            return Response(
                {"error": "description_too_long", "max_chars": MAX_DESCRIPTION_CHARS},
                status=status.HTTP_400_BAD_REQUEST,
            )

        short_id_value, short_id_recognized = normalize_short_id(payload.get("public_short_id"))
        consent = bool(payload.get("consent_to_contact"))
        contact_email = (payload.get("contact_email") or "").strip() or None
        if contact_email and not consent:
            return Response(
                {"error": "consent_required_for_contact"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ip_hash = hash_ip(self._client_ip(request))
        decision = default_limiter.check(ip_hash=ip_hash, short_id=short_id_value)
        if not decision.allowed:
            response = Response(
                {"error": "rate_limited", "scope": decision.reason},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(decision.retry_after_seconds)
            return response

        report = UserErrorReport.objects.create(
            public_short_id=short_id_value,
            category=category,
            description_excerpt=description,
            contact_email_hash=hash_email_or_none(contact_email),
            consent_to_contact=consent,
            ip_hash=ip_hash,
            user_agent_excerpt=truncate_user_agent(request.META.get("HTTP_USER_AGENT")),
        )

        tags = []
        if short_id_value and not short_id_recognized:
            tags.append("unverified_id")
        logger.info(
            "feedback.error_report.created",
            report_id=str(report.id),
            category=category,
            short_id_present=bool(short_id_value),
            short_id_recognized=short_id_recognized,
            consent_to_contact=consent,
            tags=tags,
        )
        return Response(
            {"id": str(report.id), "category": category, "tags": tags},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _client_ip(request: Request) -> str:
        # X-Forwarded-For is honored only if the proxy is trusted (Railway sets
        # SECURE_PROXY_SSL_HEADER for that purpose); fall back to REMOTE_ADDR.
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")


__all__ = ["ErrorReportView"]
