"""Schedule Celery continuation after OCR lands on ``extracted`` (Post-OCR pipeline)."""

from __future__ import annotations

import sys

import structlog
from django.db import transaction

from ingestion.domain.enums import ProcessingStatus
from ingestion.infrastructure.celery.pipeline_tasks import process_submission_pipeline
from ingestion.infrastructure.django.models import ContractSubmission
from ingestion.infrastructure.redis_handoff import (
    PipelineHandoffEnvelope,
    store_pipeline_handoff,
)

logger = structlog.get_logger(__name__)


def _banner(submission_id: str, message: str, **fields) -> None:
    extras = "  ".join(f"{k}={v}" for k, v in fields.items() if v is not None)
    line = f"  [WEB→Q]  sub={submission_id[:8]}  {message:<28}  {extras}".rstrip()
    print(line, file=sys.stdout, flush=True)


def schedule_post_ocr_pipeline(
    *,
    submission_id: str,
    extracted_text: str,
    delivery_channel: str,
    delivery_target: str | None,
) -> None:
    """Stash handoff in Redis, atomically claim ``extracted→classifying``, enqueue Celery."""

    envelope = PipelineHandoffEnvelope(
        extracted_text=extracted_text,
        delivery_channel=delivery_channel,
        delivery_target=delivery_target,
    )
    if not store_pipeline_handoff(submission_id, envelope):
        _banner(submission_id, "SKIP redis handoff already stored")
        return

    _banner(submission_id, "redis ✔ handoff stored", text_len=len(extracted_text), channel=delivery_channel)

    with transaction.atomic():
        updated = ContractSubmission.objects.filter(
            pk=submission_id,
            processing_status=ProcessingStatus.EXTRACTED.value,
            analysis__isnull=True,
        ).update(processing_status=ProcessingStatus.CLASSIFYING.value)
        if updated == 0:
            logger.info("ingest.pipeline_claim_skipped", submission_id=submission_id)
            _banner(submission_id, "SKIP could not claim extracted→classifying")
            return

        _banner(submission_id, "DB ✔ extracted → classifying")

        def _enqueue() -> None:
            process_submission_pipeline.delay(submission_id)
            _banner(submission_id, "ENQUEUE ✔ process_submission_pipeline")

        transaction.on_commit(_enqueue)


__all__ = ["schedule_post_ocr_pipeline"]
