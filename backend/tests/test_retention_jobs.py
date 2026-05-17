"""Retention job runners CS-271 / CS-272 / CS-274."""

from __future__ import annotations

from datetime import timedelta

import pytest

from django.core.management import call_command
from django.utils import timezone

from delivery.domain.enums import DeliveryRequestStatus
from ingestion.domain.enums import ProcessingStatus
from ingestion.infrastructure.django.models import ContractSubmission
from platform_core.domain.enums import DeliveryStatus
from platform_core.worker.retention import runners
from tests.factories import ContractAnalysisFactory, ContractSubmissionFactory, DeliveryRequestFactory, expire_in


@pytest.mark.django_db
def test_cleanup_transient_deletes_completed_expired_submission():
    analysis = ContractAnalysisFactory()
    sub = ContractSubmissionFactory(
        analysis=analysis,
        processing_status=ProcessingStatus.COMPLETED.value,
    )
    expire_in(timedelta(days=-1), on=sub)
    deleted = runners.run_cleanup_transient(batch_size=50)
    assert deleted >= 1
    assert not ContractSubmission.objects.filter(pk=sub.pk).exists()


@pytest.mark.django_db
def test_cleanup_transient_no_eligible_returns_zero():
    assert runners.run_cleanup_transient(batch_size=50) == 0


@pytest.mark.django_db
def test_cleanup_transient_skips_open_pipeline_with_analysis():
    analysis = ContractAnalysisFactory()
    sub = ContractSubmissionFactory(
        analysis=analysis,
        processing_status=ProcessingStatus.ANALYZING.value,
    )
    expire_in(timedelta(days=-1), on=sub)
    runners.run_cleanup_transient(batch_size=50)
    sub.refresh_from_db()
    assert sub.pk


@pytest.mark.django_db
def test_cleanup_transient_batches_until_drained():
    for _ in range(5):
        analysis = ContractAnalysisFactory()
        sub = ContractSubmissionFactory(
            analysis=analysis,
            processing_status=ProcessingStatus.COMPLETED.value,
        )
        expire_in(timedelta(days=-1), on=sub)

    total = runners.run_cleanup_transient(batch_size=2)
    assert total == 5


@pytest.mark.django_db
def test_cleanup_delivery_targets_clears_delivered_after_grace():
    dr = DeliveryRequestFactory(
        status=DeliveryRequestStatus.DELIVERED.value,
        delivered_at=timezone.now() - timedelta(minutes=10),
        target_value_encrypted="enc::keep-me-until-job",
    )
    updated = runners.run_cleanup_delivery_targets(grace_seconds=300)
    assert updated == 1
    dr.refresh_from_db()
    assert dr.target_value_encrypted is None
    assert dr.target_hash


@pytest.mark.django_db
def test_cleanup_delivery_targets_respects_grace_window():
    dr = DeliveryRequestFactory(
        status=DeliveryRequestStatus.DELIVERED.value,
        delivered_at=timezone.now() - timedelta(minutes=2),
        target_value_encrypted="enc::grace-active",
    )
    updated = runners.run_cleanup_delivery_targets(grace_seconds=300)
    assert updated == 0
    dr.refresh_from_db()
    assert dr.target_value_encrypted == "enc::grace-active"


@pytest.mark.django_db
def test_cleanup_delivery_targets_expired_rows():
    dr = DeliveryRequestFactory(
        status=DeliveryRequestStatus.QUEUED.value,
        target_value_encrypted="enc::expire-branch",
    )
    expire_in(timedelta(days=-1), on=dr)
    updated = runners.run_cleanup_delivery_targets(grace_seconds=300)
    assert updated == 1
    dr.refresh_from_db()
    assert dr.target_value_encrypted is None


@pytest.mark.django_db
def test_expire_links_marks_available_when_ttl_elapsed():
    analysis = ContractAnalysisFactory(
        delivery_status=DeliveryStatus.AVAILABLE_LINK.value,
        link_expires_at=timezone.now() - timedelta(seconds=30),
    )
    n = runners.run_expire_links()
    assert n == 1
    analysis.refresh_from_db()
    assert analysis.delivery_status == DeliveryStatus.EXPIRED.value


@pytest.mark.django_db
def test_expire_links_idempotent_second_pass():
    analysis = ContractAnalysisFactory(
        delivery_status=DeliveryStatus.AVAILABLE_LINK.value,
        link_expires_at=timezone.now() - timedelta(seconds=30),
    )
    assert runners.run_expire_links() == 1
    assert runners.run_expire_links() == 0
    analysis.refresh_from_db()
    assert analysis.delivery_status == DeliveryStatus.EXPIRED.value


@pytest.mark.django_db
def test_expire_links_skips_failed_and_null_ttl():
    failed = ContractAnalysisFactory(
        delivery_status=DeliveryStatus.FAILED.value,
        link_expires_at=timezone.now() - timedelta(days=1),
    )
    pending = ContractAnalysisFactory(
        delivery_status=DeliveryStatus.PENDING.value,
        link_expires_at=None,
    )
    runners.run_expire_links()
    failed.refresh_from_db()
    pending.refresh_from_db()
    assert failed.delivery_status == DeliveryStatus.FAILED.value
    assert pending.delivery_status == DeliveryStatus.PENDING.value


@pytest.mark.django_db
def test_run_retention_job_management_command_smoke():
    call_command("run_retention_job", "expire_links")
