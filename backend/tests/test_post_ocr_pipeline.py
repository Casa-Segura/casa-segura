"""Post-OCR Celery pipeline wiring (ingestion → F2 → rubric → delivery)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ingestion.application.post_ocr_pipeline import schedule_post_ocr_pipeline
from ingestion.domain.enums import ProcessingStatus
from ingestion.infrastructure.celery.pipeline_tasks import process_submission_pipeline
from tests.factories import ContractAnalysisFactory, ContractSubmissionFactory


@pytest.mark.django_db(transaction=True)
def test_schedule_post_ocr_pipeline_claims_and_enqueues(monkeypatch):
    monkeypatch.setattr(
        "ingestion.application.post_ocr_pipeline.store_pipeline_handoff",
        lambda submission_id, envelope: True,
    )

    delayed: list[str] = []

    def _record_delay(submission_id: str) -> None:
        delayed.append(submission_id)

    monkeypatch.setattr(
        "ingestion.infrastructure.celery.pipeline_tasks.process_submission_pipeline.delay",
        _record_delay,
    )

    sub = ContractSubmissionFactory(processing_status=ProcessingStatus.EXTRACTED.value)
    schedule_post_ocr_pipeline(
        submission_id=str(sub.id),
        extracted_text="texto de prueba contractual en español",
        delivery_channel="web_link",
        delivery_target=None,
    )
    sub.refresh_from_db()
    assert sub.processing_status == ProcessingStatus.CLASSIFYING.value
    assert delayed == [str(sub.id)]


@pytest.mark.django_db
def test_process_submission_pipeline_marks_completed(monkeypatch):
    h = "aa" * 32
    sub = ContractSubmissionFactory(
        processing_status=ProcessingStatus.CLASSIFYING.value,
        submission_hash=h,
    )
    analysis = ContractAnalysisFactory(submission_hash=h)

    monkeypatch.setattr(
        "ingestion.infrastructure.celery.pipeline_tasks.load_pipeline_handoff",
        lambda sid: SimpleNamespace(
            extracted_text="contrato en español suficiente para pipeline",
            delivery_channel="web_link",
            delivery_target=None,
        ),
    )

    class _FakeOrchestrator:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def run(self, **kwargs):
            return SimpleNamespace(contract_analysis_id=analysis.pk)

    monkeypatch.setattr(
        "ingestion.infrastructure.celery.pipeline_tasks.F2Orchestrator",
        _FakeOrchestrator,
    )
    monkeypatch.setattr(
        "ingestion.infrastructure.celery.pipeline_tasks.run_rubric_evaluation_sync",
        lambda aid: {"analysis_id": aid, "band": "yellow"},
    )

    dispatch_mock = MagicMock()
    monkeypatch.setattr(
        "ingestion.infrastructure.celery.pipeline_tasks.enqueue_contract_report_delivery",
        dispatch_mock,
    )
    deleted: list[str] = []

    def _record_delete(sid: str) -> None:
        deleted.append(sid)

    monkeypatch.setattr(
        "ingestion.infrastructure.celery.pipeline_tasks.delete_pipeline_handoff",
        _record_delete,
    )

    process_submission_pipeline.apply(args=[str(sub.id)])

    sub.refresh_from_db()
    assert sub.processing_status == ProcessingStatus.COMPLETED.value
    assert sub.analysis_id == analysis.pk
    dispatch_mock.assert_called_once()
    assert deleted == [str(sub.id)]
