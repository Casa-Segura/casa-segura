"""Wire ``ContractAnalysis`` delivery fields + enqueue channel workers after rubric."""

from __future__ import annotations

import uuid

from delivery.application.dispatcher import create_and_enqueue_delivery_request
from delivery.application.target_hash import hash_delivery_target
from delivery.application.worker_handlers import process_web_link_delivery
from delivery.infrastructure.django.models import DeliveryRequest
from platform_core.domain.enums import DeliveryChannel
from platform_core.infrastructure.django.models import ContractAnalysis


def enqueue_contract_report_delivery(*, analysis_id: uuid.UUID, channel: str, delivery_target: str | None) -> None:
    """Persist delivery intent on the analysis row and enqueue outbound handling.

    ``web_link`` completes synchronously so polling surfaces ``available_link``
    immediately (SMS/email stay asynchronous Celery tasks).
    """

    normalized = (channel or "").strip().lower()
    allowed = {
        DeliveryChannel.WEB_LINK.value,
        DeliveryChannel.SMS_SUMMARY.value,
        DeliveryChannel.EMAIL_PDF.value,
    }
    if normalized not in allowed:
        normalized = DeliveryChannel.WEB_LINK.value

    if normalized == DeliveryChannel.WEB_LINK.value:
        placeholder = hash_delivery_target(f"web_link:{analysis_id}")
        ContractAnalysis.objects.filter(pk=analysis_id).update(
            delivery_channel=DeliveryChannel.WEB_LINK.value,
            delivery_target_hash=placeholder,
        )
        dr = DeliveryRequest.objects.create(
            analysis_id=analysis_id,
            channel=DeliveryChannel.WEB_LINK.value,
            target_hash=placeholder,
            target_value_encrypted=None,
        )
        process_web_link_delivery(dr)
        return

    raw = (delivery_target or "").strip()
    tgt_hash = hash_delivery_target(raw)

    if normalized == DeliveryChannel.SMS_SUMMARY.value:
        ContractAnalysis.objects.filter(pk=analysis_id).update(
            delivery_channel=DeliveryChannel.SMS_SUMMARY.value,
            delivery_target_hash=tgt_hash,
        )
        create_and_enqueue_delivery_request(
            analysis_id=str(analysis_id),
            channel=DeliveryChannel.SMS_SUMMARY.value,
            target_hash=tgt_hash,
            target_value_encrypted=raw,
        )
        return

    ContractAnalysis.objects.filter(pk=analysis_id).update(
        delivery_channel=DeliveryChannel.EMAIL_PDF.value,
        delivery_target_hash=tgt_hash,
    )
    create_and_enqueue_delivery_request(
        analysis_id=str(analysis_id),
        channel=DeliveryChannel.EMAIL_PDF.value,
        target_hash=tgt_hash,
        target_value_encrypted=raw,
    )


__all__ = ["enqueue_contract_report_delivery"]
