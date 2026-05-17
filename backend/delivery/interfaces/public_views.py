"""Public report routes — CS-245 / CS-246 / CS-247."""

from __future__ import annotations

import logging

from django.http import HttpResponse
from django.utils import timezone
from django.views import View

from delivery.application.report_html import (
    AnalysisNotReady,
    ReportNotFound,
    ReportRenderFailed,
    generate_report_html_for_analysis,
)
from platform_core.domain.enums import DeliveryStatus
from platform_core.infrastructure.django.models import ContractAnalysis

logger = logging.getLogger(__name__)

_EXPIRED_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Enlace expirado</title>
<style>
body{font-family:system-ui,sans-serif;margin:1rem;max-width:360px;line-height:1.5}
</style>
</head><body>
<p>🔒</p>
<p>Este enlace dejó de estar disponible tras el período de acceso (30 días).</p>
<p>Por privacidad no guardamos copias permanentes del informe en este servidor.</p>
<p><a href="/">Volver al inicio</a></p>
</body></html>"""

_NOT_FOUND_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>No encontrado</title>
<style>body{font-family:system-ui,sans-serif;margin:1rem;max-width:360px}</style>
</head><body><p>Análisis no encontrado.</p><p><a href="/">Inicio</a></p></body></html>"""

_SERVER_ERROR_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Error temporal</title>
<style>body{font-family:system-ui,sans-serif;margin:1rem;max-width:360px;line-height:1.5}</style>
</head><body><p>No pudimos generar el informe en este momento.</p><p><a href="/">Inicio</a></p></body></html>"""


def _privacy_headers(resp: HttpResponse) -> HttpResponse:
    resp["Cache-Control"] = "no-store"
    resp["X-Robots-Tag"] = "noindex, nofollow"
    resp["Pragma"] = "no-cache"
    return resp


def _html_page(body: str, *, status_code: int) -> HttpResponse:
    return HttpResponse(body, status=status_code, content_type="text/html; charset=utf-8")


def _public_report_access_gate(analysis: ContractAnalysis, sid: str) -> HttpResponse | None:
    now = timezone.now()
    if analysis.link_expires_at is not None and analysis.link_expires_at < now:
        return _html_page(_EXPIRED_HTML, status_code=410)

    if analysis.delivery_status not in (
        DeliveryStatus.AVAILABLE_LINK.value,
        DeliveryStatus.SENT_EMAIL.value,
        DeliveryStatus.SENT_SMS.value,
    ):
        logger.info("public_report_not_ready", extra={"public_short_id": sid})
        return _html_page(_NOT_FOUND_HTML, status_code=404)
    return None


def _public_report_body(sid: str, analysis: ContractAnalysis) -> HttpResponse:
    try:
        html, stats = generate_report_html_for_analysis(public_short_id=sid, analysis=analysis)
    except ReportNotFound:
        return _html_page(_NOT_FOUND_HTML, status_code=404)
    except AnalysisNotReady:
        return _html_page(_NOT_FOUND_HTML, status_code=404)
    except ReportRenderFailed as exc:
        logger.error(
            "public_report_render_failed",
            extra={"public_short_id": sid, "code": exc.code},
        )
        return _html_page(_SERVER_ERROR_HTML, status_code=500)

    logger.info(
        "public_report_served",
        extra={"public_short_id": sid, "html_bytes": stats.byte_length},
    )
    return HttpResponse(html, content_type="text/html; charset=utf-8")


def _resolve_public_report(sid: str) -> HttpResponse:
    if not sid:
        return _html_page(_NOT_FOUND_HTML, status_code=404)

    analysis = ContractAnalysis.objects.filter(public_short_id=sid).first()
    if analysis is None:
        return _html_page(_NOT_FOUND_HTML, status_code=404)

    blocked = _public_report_access_gate(analysis, sid)
    if blocked is not None:
        return blocked
    return _public_report_body(sid, analysis)


class PublicReportHtmlView(View):
    """``GET /r/<public_short_id>/`` — TTL gate + on-demand HTML (CS-247)."""

    def get(self, request, public_short_id: str):
        sid = (public_short_id or "").strip()
        return _privacy_headers(_resolve_public_report(sid))
