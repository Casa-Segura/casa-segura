"""Apply verified Zavu webhook bodies — CS-357."""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from delivery.domain.enums import DeliveryRequestStatus
from delivery.domain.schemas import ZavuWebhookPayload
from delivery.infrastructure.django.models import DeliveryRequest

logger = logging.getLogger(__name__)


def process_zavu_webhook_dict(payload: dict) -> None:
    """Idempotent status alignment keyed by provider ``provider_message_id``."""

    try:
        envelope = ZavuWebhookPayload.model_validate(payload)
    except Exception:
        logger.warning("zavu_webhook_payload_invalid_shape")
        return

    message_id = envelope.resolve_message_id()
    if not message_id:
        logger.info("zavu_webhook_no_message_id", extra={"event_type": envelope.type})
        return

    event = envelope.type.lower()
    with transaction.atomic():
        row = DeliveryRequest.objects.select_for_update().filter(provider_message_id=message_id).first()
        if row is None:
            logger.info(
                "zavu_webhook_orphan_event",
                extra={"event_type": envelope.type, "message_id": message_id},
            )
            return

        if "failed" in event:
            if row.status == DeliveryRequestStatus.DELIVERED.value:
                logger.warning(
                    "zavu_webhook_failed_after_delivered",
                    extra={"delivery_request_id": str(row.pk)},
                )
                return
            row.status = DeliveryRequestStatus.FAILED.value
            row.last_error = "provider_failed_event"
            row.save(update_fields=["status", "last_error"])
            logger.info(
                "zavu_webhook_marked_failed",
                extra={"delivery_request_id": str(row.pk)},
            )
            return

        if "delivered" in event:
            if row.status == DeliveryRequestStatus.DELIVERED.value:
                return
            row.delivered_at = row.delivered_at or timezone.now()
            row.status = DeliveryRequestStatus.DELIVERED.value
            row.save(update_fields=["delivered_at", "status"])
            logger.info(
                "zavu_webhook_marked_delivered",
                extra={"delivery_request_id": str(row.pk)},
            )
