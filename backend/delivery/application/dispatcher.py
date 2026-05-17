"""Channel orchestration — CS-231."""

from __future__ import annotations

import logging

from django.db import transaction

from delivery.infrastructure.django.models import DeliveryRequest
from delivery.infrastructure.django.tasks import deliver_channel_task

logger = logging.getLogger(__name__)


def create_and_enqueue_delivery_request(
    *,
    analysis_id,
    channel: str,
    target_hash: str,
    target_value_encrypted: str | None = None,
    is_resend: bool = False,
):
    """Persist queued DeliveryRequest and schedule Celery after transaction commits."""

    dr = DeliveryRequest.objects.create(
        analysis_id=analysis_id,
        channel=channel,
        target_hash=target_hash,
        target_value_encrypted=target_value_encrypted,
        is_resend=is_resend,
    )

    dr_id = str(dr.id)

    def _enqueue() -> None:
        deliver_channel_task.delay(dr_id)

    transaction.on_commit(_enqueue)
    logger.info(
        "delivery_request_created",
        extra={"delivery_request_id": dr_id, "channel": channel},
    )
    return dr
