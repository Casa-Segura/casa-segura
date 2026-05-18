"""Celery tasks for delivery — discovered via Django app ``delivery`` (CS-233)."""

from __future__ import annotations

import time

import structlog
from celery import shared_task

from delivery.application.worker_handlers import process_delivery_request_by_id

logger = structlog.get_logger(__name__)


@shared_task(name="delivery.deliver_channel", bind=False)
def deliver_channel_task(delivery_request_id: str) -> None:
    """Fan-out dispatcher invoked via Celery."""

    wall_start = time.perf_counter()
    logger.info("delivery.deliver_channel.started", delivery_request_id=delivery_request_id)
    try:
        process_delivery_request_by_id(delivery_request_id)
    except Exception:
        elapsed_ms = round((time.perf_counter() - wall_start) * 1000)
        logger.exception(
            "delivery.deliver_channel.failed",
            delivery_request_id=delivery_request_id,
            elapsed_ms=elapsed_ms,
        )
        raise
    elapsed_ms = round((time.perf_counter() - wall_start) * 1000)
    logger.info(
        "delivery.deliver_channel.completed",
        delivery_request_id=delivery_request_id,
        elapsed_ms=elapsed_ms,
    )


@shared_task(name="delivery.deliver_sms_stub")
def deliver_sms_stub_task(delivery_request_id: str) -> None:
    """Reserved for CS-241 — keeps Celery route catalog stable."""

    _ = delivery_request_id


@shared_task(name="delivery.retry_scheduler_stub")
def retry_scheduler_stub_task() -> None:
    """Beat-driven backlog scanner placeholder."""
