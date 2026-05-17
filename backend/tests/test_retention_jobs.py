"""Retention job runners CS-271 / CS-272 / CS-274 / CS-273 / CS-275."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from django.core.management import call_command
from django.test.utils import override_settings
from django.utils import timezone

from delivery.domain.enums import DeliveryRequestStatus
from ingestion.domain.enums import ProcessingStatus
from ingestion.infrastructure.django.models import ContractSubmission
from platform_core.domain.enums import Band, DeliveryStatus, PrivacyAuditEvent
from platform_core.infrastructure.django.models import PrivacyAuditLog
from platform_core.worker.retention import runners
from tests.factories import (
    ContractAnalysisFactory,
    ContractSubmissionFactory,
    DeliveryRequestFactory,
    ProjectFactory,
    age_to,
    expire_in,
)

ANCHOR = datetime(2026, 5, 17, 18, 0, 0, tzinfo=UTC)


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


# ─── CS-273 / CS-276 anonymization ─────────────────────────────────────────


@pytest.mark.django_db
def test_anonymize_eligible_when_older_than_threshold():
    with patch("django.utils.timezone.now", return_value=ANCHOR):
        cutoff = ANCHOR - timedelta(days=90)
        analysis = ContractAnalysisFactory(
            delivery_target_hash="salt-hash",
            criterion_evaluations=[
                {
                    "criterion_id": "A1",
                    "category": "A",
                    "applicable": True,
                    "evaluated": True,
                    "unverifiable": False,
                    "score": 5.0,
                    "weight_in_category": 10.0,
                    "justification": "j",
                }
            ],
            findings=[
                {
                    "id": "f1",
                    "severity": "yellow",
                    "title": "t",
                    "description": "d",
                    "recommendation": "r",
                    "related_criterion_id": "A1",
                    "legal_basis": [],
                    "tags": [],
                }
            ],
            scores_by_category=[
                {
                    "category": "A",
                    "score": 8.0,
                    "category_name": "Legal",
                    "weight_global": 0.2,
                    "weight_effective": 0.2,
                    "criteria_count_total": 1,
                    "criteria_count_applicable": 1,
                    "criteria_count_unverifiable": 0,
                }
            ],
            economic_summary={
                "fields_extracted": {"price_cash": "35000"},
                "benchmark_comparisons": [],
                "benchmark_version": "bv",
                "contract_type": "CVP",
            },
            executive_summary="keep narrative",
        )
        age_to(cutoff - timedelta(seconds=1), on=analysis)
        assert runners.run_anonymize_old_analyses(batch_size=50, policy_days=90) == 1
        analysis.refresh_from_db()
        assert analysis.anonymized_at is not None
        assert analysis.delivery_target_hash is None
        assert analysis.criterion_evaluations == []
        assert analysis.findings == []
        assert analysis.executive_summary == "keep narrative"
        assert analysis.scores_by_category == [{"category": "A", "score": 8.0}]
        assert analysis.economic_summary["anonymized"] is True
        assert analysis.economic_summary["price_cash_bucket"] == "30k-60k"


@pytest.mark.django_db
def test_anonymize_skips_when_younger_than_threshold():
    with patch("django.utils.timezone.now", return_value=ANCHOR):
        cutoff = ANCHOR - timedelta(days=90)
        analysis = ContractAnalysisFactory(delivery_target_hash="keep")
        age_to(cutoff + timedelta(seconds=1), on=analysis)
        assert runners.run_anonymize_old_analyses(batch_size=50, policy_days=90) == 0
        analysis.refresh_from_db()
        assert analysis.anonymized_at is None
        assert analysis.delivery_target_hash == "keep"


@pytest.mark.django_db
def test_anonymize_idempotent_second_pass():
    with patch("django.utils.timezone.now", return_value=ANCHOR):
        cutoff = ANCHOR - timedelta(days=90)
        analysis = ContractAnalysisFactory()
        age_to(cutoff - timedelta(seconds=1), on=analysis)
        assert runners.run_anonymize_old_analyses(batch_size=50, policy_days=90) == 1
        assert runners.run_anonymize_old_analyses(batch_size=50, policy_days=90) == 0
        assert (
            PrivacyAuditLog.objects.filter(
                event_type=PrivacyAuditEvent.ANALYSIS_ANONYMIZED.value, related_id=analysis.pk
            ).count()
            == 1
        )


@pytest.mark.django_db
def test_anonymize_writes_privacy_audit_without_pii_literals():
    with patch("django.utils.timezone.now", return_value=ANCHOR):
        cutoff = ANCHOR - timedelta(days=90)
        analysis = ContractAnalysisFactory(
            economic_summary={
                "fields_extracted": {"price_cash": "50000"},
                "benchmark_comparisons": [],
                "benchmark_version": "bv",
                "contract_type": "CVP",
            }
        )
        age_to(cutoff - timedelta(seconds=1), on=analysis)
        runners.run_anonymize_old_analyses(batch_size=50, policy_days=60)
        row = PrivacyAuditLog.objects.get(related_id=analysis.pk)
        assert row.event_type == PrivacyAuditEvent.ANALYSIS_ANONYMIZED.value
        assert row.triggered_by == "job:anonymize_old_analyses"
        assert row.event_data["policy_days"] == 60
        blob = str(row.event_data)
        assert "50000" not in blob
        assert "@" not in blob


@pytest.mark.django_db
def test_anonymize_audit_insert_failure_does_not_commit_analysis():
    with patch("django.utils.timezone.now", return_value=ANCHOR):
        cutoff = ANCHOR - timedelta(days=90)
        analysis = ContractAnalysisFactory(delivery_target_hash="x")
        age_to(cutoff - timedelta(seconds=1), on=analysis)
        with patch(
            "platform_core.worker.retention.runners.PrivacyAuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            assert runners.run_anonymize_old_analyses(batch_size=50, policy_days=90) == 0
        analysis.refresh_from_db()
        assert analysis.anonymized_at is None
        assert analysis.delivery_target_hash == "x"


@pytest.mark.django_db
@override_settings(ANONYMIZATION_AFTER_DAYS=60)
def test_run_retention_job_anonymize_respects_settings():
    cutoff = ANCHOR - timedelta(days=60)
    analysis = ContractAnalysisFactory()
    age_to(cutoff - timedelta(seconds=1), on=analysis)
    with patch("django.utils.timezone.now", return_value=ANCHOR):
        call_command("run_retention_job", "anonymize_old_analyses")
    analysis.refresh_from_db()
    assert analysis.anonymized_at is not None


# ─── CS-275 project metrics ──────────────────────────────────────────────────


@pytest.mark.django_db
def test_recompute_project_metrics_avg_and_distribution():
    proj = ProjectFactory(last_recomputed_at=None, score_distribution={"green": 0, "yellow": 0, "red": 0})
    proj.last_analyzed = timezone.now() - timedelta(hours=2)
    proj.save(update_fields=["last_analyzed"])
    ContractAnalysisFactory(project=proj, score_total=Decimal("7.0"), band=Band.YELLOW.value)
    ContractAnalysisFactory(project=proj, score_total=Decimal("8.0"), band=Band.YELLOW.value)
    ContractAnalysisFactory(project=proj, score_total=Decimal("9.0"), band=Band.GREEN.value)

    assert runners.run_recompute_project_metrics(batch_size=50) == 1
    proj.refresh_from_db()
    assert proj.avg_score == Decimal("8.0")
    assert proj.total_analyses == 3
    assert proj.score_distribution["green"] == 1
    assert proj.score_distribution["yellow"] == 2
    assert proj.score_distribution["red"] == 0
    assert proj.score_distribution["not_analyzable"] == 0


@pytest.mark.django_db
def test_recompute_includes_anonymized_analysis():
    proj = ProjectFactory(last_recomputed_at=None)
    proj.last_analyzed = timezone.now() - timedelta(hours=1)
    proj.save(update_fields=["last_analyzed"])
    ContractAnalysisFactory(project=proj, score_total=Decimal("6.0"), band=Band.RED.value)
    ContractAnalysisFactory(
        project=proj,
        score_total=Decimal("10.0"),
        band=Band.GREEN.value,
        anonymized_at=timezone.now() - timedelta(days=1),
    )

    assert runners.run_recompute_project_metrics(batch_size=50) == 1
    proj.refresh_from_db()
    assert proj.total_analyses == 2
    assert proj.avg_score == Decimal("8.0")


@pytest.mark.django_db
def test_recompute_skips_placeholder_projects():
    ph = ProjectFactory(last_recomputed_at=None, metadata={"placeholder": True})
    ph.last_analyzed = timezone.now()
    ph.save(update_fields=["last_analyzed"])
    ContractAnalysisFactory(project=ph, score_total=Decimal("9.0"), band=Band.GREEN.value)

    assert runners.run_recompute_project_metrics(batch_size=50) == 0
    ph.refresh_from_db()
    assert ph.avg_score is None

    assert runners.recompute_metrics_for_project(ph.pk, force=True) == 1
    ph.refresh_from_db()
    assert ph.avg_score == Decimal("9.0")


@pytest.mark.django_db
def test_recompute_second_global_pass_is_noop():
    proj = ProjectFactory(last_recomputed_at=None)
    proj.last_analyzed = timezone.now()
    proj.save(update_fields=["last_analyzed"])
    ContractAnalysisFactory(project=proj, score_total=Decimal("8.0"), band=Band.GREEN.value)

    assert runners.run_recompute_project_metrics(batch_size=50) == 1
    assert runners.run_recompute_project_metrics(batch_size=50) == 0


@pytest.mark.django_db
def test_recompute_not_selected_when_last_recomputed_equals_last_analyzed():
    proj = ProjectFactory()
    ts = timezone.now()
    proj.last_recomputed_at = ts
    proj.last_analyzed = ts
    proj.save(update_fields=["last_recomputed_at", "last_analyzed"])
    ContractAnalysisFactory(project=proj, score_total=Decimal("9.0"), band=Band.GREEN.value)

    assert runners.run_recompute_project_metrics(batch_size=50) == 0
