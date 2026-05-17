"""SMS body composition — CS-240 (+ registry validation CS-239)."""

from __future__ import annotations

import unicodedata

from django.conf import settings

from delivery.domain.sms_templates import (
    DISCLAIMER_SHORTHAND_ES,
    SMS_BODY_SUMMARY_TEMPLATE,
)


class SmsCompositionError(ValueError):
    """Raised when required fields are missing or segment budget is exceeded."""


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def compose_sms_summary(
    *,
    public_short_id: str,
    band: str,
    report_url: str,
) -> str:
    """Build UTF-8 SMS body; enforces segment budget and disclaimer presence."""

    sid = _nfc((public_short_id or "").strip())
    b = _nfc((band or "").strip())
    url = _nfc((report_url or "").strip())
    if not sid or not url:
        raise SmsCompositionError("sms_missing_required_fields")
    body = _nfc(
        SMS_BODY_SUMMARY_TEMPLATE.format(public_short_id=sid, band=b or "-", report_url=url),
    )
    if DISCLAIMER_SHORTHAND_ES not in body:
        raise SmsCompositionError("sms_disclaimer_missing")
    budget = int(getattr(settings, "SMS_SEGMENT_CHAR_BUDGET", 480))
    if len(body) > budget:
        raise SmsCompositionError("sms_segment_budget_exceeded")
    return body
