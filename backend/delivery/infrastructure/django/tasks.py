"""Celery tasks for delivery — discovered via Django app ``delivery`` (CS-233)."""

from __future__ import annotations

import logging

from celery import shared_task

from delivery.application.worker_handlers import process_delivery_request_by_id

logger = logging.getLogger(__name__)


@shared_task(name="delivery.deliver_channel", bind=False)
def deliver_channel_task(delivery_request_id: str) -> None:
    """Fan-out dispatcher invoked via Celery."""

    try:
        process_delivery_request_by_id(delivery_request_id)
    except Exception:
        logger.exception("delivery_channel_task_failed", extra={"delivery_request_id": delivery_request_id})
        raise


@shared_task(name="delivery.deliver_sms_stub")
def deliver_sms_stub_task(delivery_request_id: str) -> None:
    """Reserved for CS-241 — keeps Celery route catalog stable."""

    _ = delivery_request_id


@shared_task(name="delivery.retry_scheduler_stub")
def retry_scheduler_stub_task() -> None:
    """Beat-driven backlog scanner placeholder."""
