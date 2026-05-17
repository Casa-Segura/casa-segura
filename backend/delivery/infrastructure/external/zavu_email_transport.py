"""Outbound email adapter — CS-235 (Zavu primary)."""

from __future__ import annotations

import base64
import logging
from typing import Any

from delivery.application.email_composer import EmailComposeResult
from delivery.application.provider_errors import classify_zavu_exception
from delivery.infrastructure.external.zavu_messaging import send_zavu_email

logger = logging.getLogger(__name__)


class ZavuEmailTransport:
    """Transactional PDF email via Zavu SDK."""

    def send_pdf_email(
        self,
        *,
        to_email: str,
        composed: EmailComposeResult,
        pdf_bytes: bytes,
        idempotency_key: str | None,
    ) -> str:
        attachments: list[dict[str, Any]] = [
            {
                "filename": composed.attachment_filename,
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        ]
        try:
            return send_zavu_email(
                to=to_email,
                subject=composed.subject,
                text=composed.text_body,
                html_body=composed.html_body,
                idempotency_key=idempotency_key,
                attachments=attachments,
            )
        except Exception as exc:
            classified = classify_zavu_exception(exc)
            logger.warning(
                "zavu_email_transport_failed",
                extra={
                    "classification": classified.classification,
                    "reason_code": classified.reason_code,
                },
            )
            raise classified from exc
