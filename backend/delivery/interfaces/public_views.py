"""Public report routes — CS-245 / CS-246 / CS-247 stubs."""

from __future__ import annotations

import logging

from django.http import Http404, HttpResponse
from django.utils import timezone
from django.views import View

from platform_core.domain.enums import DeliveryStatus
from platform_core.infrastructure.django.models import ContractAnalysis

logger = logging.getLogger(__name__)


class PublicReportHtmlView(View):
    """``GET /r/<public_short_id>/`` — TTL gate + HTML stub (regeneration wired in CS-247)."""

    def get(self, request, public_short_id: str):
        sid = (public_short_id or "").strip()
        if not sid:
            raise Http404

        analysis = ContractAnalysis.objects.filter(public_short_id=sid).first()
        if analysis is None:
            raise Http404

        now = timezone.now()
        if analysis.link_expires_at and analysis.link_expires_at < now:
            return HttpResponse(
                "Este enlace expiró o ya no está disponible.",
                status=410,
                content_type="text/plain; charset=utf-8",
            )

        if analysis.delivery_status not in (
            DeliveryStatus.AVAILABLE_LINK.value,
            DeliveryStatus.SENT_EMAIL.value,
            DeliveryStatus.SENT_SMS.value,
        ):
            logger.info("public_report_not_ready", extra={"public_short_id": sid})
            raise Http404

        html = (
            "<!DOCTYPE html><html lang=\"es\"><head><meta charset=\"utf-8\"/>"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>"
            "<title>Casa Segura</title></head><body>"
            f"<main><h1>Informe {analysis.public_short_id}</h1>"
            "<p>Banda: "
            f"{analysis.band or 'pendiente'}"
            ". "
            "La regeneración completa del HTML llegará con CS-247.</p>"
            "</main></body></html>"
        )
        return HttpResponse(html, content_type="text/html; charset=utf-8")
