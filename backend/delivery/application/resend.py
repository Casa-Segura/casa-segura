"""Guarded resend — CS-248."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from delivery.application.dispatcher import create_and_enqueue_delivery_request
from delivery.application.target_hash import hash_delivery_target
from platform_core.infrastructure.django.models import ContractAnalysis


class ResendError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def enqueue_resend(*, public_short_id: str, target_raw: str) -> str:
    """Validate hash, caps, TTL; enqueue new ``DeliveryRequest``.

    Returns the analysis's delivery channel (for 202 JSON echo).
    """

    sid = (public_short_id or "").strip()
    if not sid:
        raise ResendError("NOT_FOUND", "missing id")

    enc_payload = f"enc::{target_raw.strip()}"

    with transaction.atomic():
        analysis = ContractAnalysis.objects.select_for_update().filter(public_short_id=sid).first()
        if analysis is None:
            raise ResendError("NOT_FOUND", "analysis missing")

        if analysis.anonymized_at is not None or not analysis.delivery_target_hash:
            raise ResendError("NOT_FOUND", "resend unavailable")

        now = timezone.now()
        if analysis.link_expires_at and analysis.link_expires_at <= now:
            raise ResendError("LINK_EXPIRED", "link expired")

        if analysis.resend_count >= 3:
            raise ResendError("RESEND_LIMIT_EXCEEDED", "limit")

        supplied_hash = hash_delivery_target(target_raw)
        if supplied_hash != analysis.delivery_target_hash:
            raise ResendError("TARGET_MISMATCH", "hash mismatch")

        channel = analysis.delivery_channel
        if not channel:
            raise ResendError("NOT_FOUND", "channel unknown")

        analysis.resend_count += 1
        analysis.save(update_fields=["resend_count"])

        create_and_enqueue_delivery_request(
            analysis_id=str(analysis.pk),
            channel=channel,
            target_hash=analysis.delivery_target_hash,
            target_value_encrypted=enc_payload,
            is_resend=True,
        )
        return channel
