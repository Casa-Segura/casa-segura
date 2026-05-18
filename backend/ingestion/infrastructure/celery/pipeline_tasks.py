"""Post-OCR Celery pipeline — F2 classification, rubric, delivery, submission completion."""

from __future__ import annotations

import time

import structlog
from celery import shared_task

from django.db import transaction

from classification.application.orchestrator import F2Orchestrator, F2OrchestratorError
from delivery.application.post_analysis_delivery import enqueue_contract_report_delivery
from ingestion.domain.enums import ProcessingStatus
from ingestion.infrastructure.django.models import ContractSubmission
from ingestion.infrastructure.redis_handoff import delete_pipeline_handoff, load_pipeline_handoff
from rubric.infrastructure.celery.rubric_tasks import run_rubric_evaluation_sync

logger = structlog.get_logger(__name__)


def _submission_hash12(submission_hash: str) -> str:
    return submission_hash.strip()[:12]


def _mark_pipeline_failed(submission_id: str, *, code: str, message: str) -> None:
    ContractSubmission.objects.filter(pk=submission_id).update(
        processing_status=ProcessingStatus.FAILED_ANALYSIS.value,
        error_code=(code or "pipeline_failed")[:64],
        error_reason=message[:1000],
    )


@shared_task(
    bind=True,
    name="ingestion.process_submission_pipeline",
    max_retries=4,
    default_retry_delay=30,
)
def process_submission_pipeline(self, submission_id: str) -> None:
    """Load Redis handoff, run F2 + rubric + delivery, mark submission completed."""

    t0 = time.perf_counter()
    logger.info("pipeline.task.started", submission_id=submission_id)

    envelope = load_pipeline_handoff(submission_id)
    if envelope is None:
        logger.warning("pipeline.handoff_missing", submission_id=submission_id)
        return

    try:
        submission = ContractSubmission.objects.get(pk=submission_id)
    except ContractSubmission.DoesNotExist:
        logger.warning("pipeline.submission_missing", submission_id=submission_id)
        delete_pipeline_handoff(submission_id)
        return

    if submission.processing_status != ProcessingStatus.CLASSIFYING.value:
        logger.info(
            "pipeline.skipped_wrong_status",
            submission_id=submission_id,
            status=submission.processing_status,
        )
        delete_pipeline_handoff(submission_id)
        return

    sub_hash12 = _submission_hash12(submission.submission_hash)

    try:
        with F2Orchestrator() as orchestrator:
            f2_result = orchestrator.run(
                submission_hash=submission.submission_hash,
                extracted_text=envelope.extracted_text,
            )
    except F2OrchestratorError as exc:
        if exc.code == "LLM_TRANSIENT_FAILURE" and self.request.retries < self.max_retries:
            logger.warning(
                "pipeline.f2_retry",
                submission_id=submission_id,
                submission_hash12=sub_hash12,
                code=exc.code,
                retry=self.request.retries,
            )
            raise self.retry(exc=exc, countdown=30 * (int(self.request.retries) + 1)) from exc
        logger.error(
            "pipeline.f2_failed",
            submission_id=submission_id,
            submission_hash12=sub_hash12,
            code=exc.code,
            error_class=exc.__class__.__name__,
        )
        if exc.code != "FAILED_CLASSIFICATION":
            _mark_pipeline_failed(submission_id, code=exc.code or "f2_failed", message=str(exc))
        delete_pipeline_handoff(submission_id)
        return
    except Exception as exc:
        if self.request.retries < self.max_retries:
            logger.warning(
                "pipeline.f2_retry_unexpected",
                submission_id=submission_id,
                submission_hash12=sub_hash12,
                error_class=exc.__class__.__name__,
                retry=self.request.retries,
            )
            raise self.retry(exc=exc, countdown=45 * (int(self.request.retries) + 1)) from exc
        logger.exception(
            "pipeline.f2_unexpected_failed",
            submission_id=submission_id,
            submission_hash12=sub_hash12,
        )
        _mark_pipeline_failed(submission_id, code="f2_unexpected", message=str(exc))
        delete_pipeline_handoff(submission_id)
        return

    analysis_uuid = f2_result.contract_analysis_id

    try:
        with transaction.atomic():
            ContractSubmission.objects.filter(pk=submission_id).update(
                analysis_id=analysis_uuid,
                processing_status=ProcessingStatus.ANALYZING.value,
            )
            run_rubric_evaluation_sync(str(analysis_uuid))
            enqueue_contract_report_delivery(
                analysis_id=analysis_uuid,
                channel=envelope.delivery_channel,
                delivery_target=envelope.delivery_target,
            )
            ContractSubmission.objects.filter(pk=submission_id).update(
                processing_status=ProcessingStatus.COMPLETED.value,
            )
    except Exception:
        logger.exception(
            "pipeline.post_f2_failed",
            submission_id=submission_id,
            submission_hash12=sub_hash12,
            analysis_id=str(analysis_uuid),
        )
        _mark_pipeline_failed(submission_id, code="post_f2_failed", message="post_f2_failed")
        delete_pipeline_handoff(submission_id)
        return

    delete_pipeline_handoff(submission_id)

    elapsed_ms = round((time.perf_counter() - t0) * 1000)
    logger.info(
        "pipeline.task.completed",
        submission_id=submission_id,
        submission_hash12=sub_hash12,
        analysis_id=str(analysis_uuid),
        elapsed_ms=elapsed_ms,
    )


__all__ = ["process_submission_pipeline"]
