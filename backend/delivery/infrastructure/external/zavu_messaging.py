"""Outbound email (and future channel sends) via Zavu `zavudev` SDK.

Docs: https://docs.zavu.dev/sdks/python/messages
"""

from __future__ import annotations

import html
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def zavu_email_download_link_html(*, url: str, link_text: str) -> str:
    """Minimal HTML body with a single download link (URLs must be verified in Zavu when required)."""
    label = html.escape(link_text)
    href = html.escape(url, quote=True)
    return f"<p>{label}: <a href=\"{href}\">{label}</a></p>"


def _zavu_client():
    """Return configured SDK client or raise :exc:`ValueError` if API key is missing."""
    from zavudev import Zavudev

    key = (getattr(settings, "ZAVUDEV_API_KEY", "") or "").strip()
    if not key:
        raise ValueError("ZAVUDEV_API_KEY / ZAVU_API_KEY is not configured")
    return Zavudev(api_key=key)


def _default_zavu_sender() -> str | None:
    sid = (getattr(settings, "ZAVU_SENDER_ID", "") or "").strip()
    return sid or None


def send_zavu_email(
    *,
    to: str,
    subject: str,
    text: str,
    html_body: str | None = None,
    reply_to: str | None = None,
    idempotency_key: str | None = None,
    zavu_sender: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> str:
    """Send one email via Zavu. Returns provider message id.

    ``attachments`` uses Zavu's shape, e.g.
    ``[{"filename": "x.pdf", "path": "https://..."}]`` or base64 ``content`` per Zavu docs.
    """
    client = _zavu_client()
    sender = (zavu_sender or _default_zavu_sender()) or None

    kwargs: dict[str, Any] = {
        "to": to.strip(),
        "channel": "email",
        "subject": subject,
        "text": text,
    }
    if html_body is not None:
        kwargs["html_body"] = html_body
    if reply_to:
        kwargs["reply_to"] = reply_to
    if idempotency_key:
        kwargs["idempotency_key"] = idempotency_key
    if sender:
        kwargs["zavu_sender"] = sender

    extra_body: dict[str, Any] | None = None
    if attachments:
        extra_body = {"attachments": attachments}

    to_domain = to.strip().split("@")[-1].lower() if "@" in to else ""

    try:
        response = client.messages.send(**kwargs, extra_body=extra_body)
    except Exception:
        logger.exception("zavu_email_send_failed", extra={"to_domain": to_domain})
        raise

    message_id = response.message.id
    logger.info("zavu_email_sent", extra={"message_id": message_id, "to_domain": to_domain})
    return message_id
