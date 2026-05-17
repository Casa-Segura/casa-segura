"""Synchronous delivery processors invoked by Celery tasks."""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from delivery.application.email_composer import compose_delivery_email
from delivery.application.metrics import (
    DELIVERY_ATTEMPT_TOTAL,
    DELIVERY_FAILED_TOTAL,
    DELIVERY_SEND_LATENCY_SECONDS,
)
from delivery.application.provider_errors import ClassifiedDeliveryError, classify_generic
from delivery.application.retry_policy import next_attempt_not_before
from delivery.application.stub_pdf import StubReportPdfGenerator
from delivery.application.target_plaintext import plaintext_email
from delivery.domain.enums import DeliveryRequestStatus, ErrorClassification
from delivery.infrastructure.django.models import DeliveryRequest
from delivery.infrastructure.external.zavu_email_transport import ZavuEmailTransport
from platform_core.domain.enums import DeliveryChannel, DeliveryStatus
from platform_core.infrastructure.django.models import ContractAnalysis

logger = logging.getLogger(__name__)


def process_delivery_request_by_id(delivery_request_id: str) -> None:
    dr = DeliveryRequest.objects.select_related("analysis").filter(pk=delivery_request_id).first()
    if dr is None:
        logger.warning("delivery_request_missing", extra={"delivery_request_id": delivery_request_id})
        return

    if dr.channel == DeliveryChannel.EMAIL_PDF.value:
        process_email_pdf_delivery(dr)
    elif dr.channel == DeliveryChannel.WEB_LINK.value:
        process_web_link_delivery(dr)
    elif dr.channel == DeliveryChannel.SMS_SUMMARY.value:
        process_sms_summary_stub(dr)
    else:
        _terminal_failure(dr, reason_code="unknown_channel", message="unsupported channel", permanent=True)


def process_web_link_delivery(dr: DeliveryRequest) -> None:
    """Mark analysis link-available — no SMTP/Zavu."""

    ttl_days = int(getattr(settings, "PUBLIC_REPORT_LINK_TTL_DAYS", 30))

    with transaction.atomic():
        locked = DeliveryRequest.objects.select_for_update().get(pk=dr.pk)
        if locked.status != DeliveryRequestStatus.QUEUED.value:
            return
        now = timezone.now()
        locked.status = DeliveryRequestStatus.DELIVERED.value
        locked.delivered_at = now
        locked.target_value_encrypted = None
        locked.provider_message_id = ""
        locked.last_error = ""
        locked.last_error_classification = None
        locked.save(
            update_fields=[
                "status",
                "delivered_at",
                "target_value_encrypted",
                "provider_message_id",
                "last_error",
                "last_error_classification",
            ]
        )
        ContractAnalysis.objects.filter(pk=locked.analysis_id).update(
            delivery_status=DeliveryStatus.AVAILABLE_LINK.value,
            link_expires_at=now + timedelta(days=ttl_days),
        )

    DELIVERY_ATTEMPT_TOTAL.labels(channel="web_link").inc()


def process_sms_summary_stub(dr: DeliveryRequest) -> None:
    """SMS handler placeholder until CS-241 lands."""

    _terminal_failure(
        dr,
        reason_code="sms_not_implemented",
        message="SMS delivery worker not enabled",
        permanent=True,
    )


def _finalize_email_pdf_delivery(dr: DeliveryRequest, *, msg_id: str) -> None:
    with transaction.atomic():
        locked = DeliveryRequest.objects.select_for_update().get(pk=dr.pk)
        locked.status = DeliveryRequestStatus.DELIVERED.value
        locked.delivered_at = timezone.now()
        locked.provider_message_id = msg_id
        locked.target_value_encrypted = None
        locked.last_error = ""
        locked.last_error_classification = None
        locked.save(
            update_fields=[
                "status",
                "delivered_at",
                "provider_message_id",
                "target_value_encrypted",
                "last_error",
                "last_error_classification",
            ]
        )
        ContractAnalysis.objects.filter(pk=locked.analysis_id).update(delivery_status=DeliveryStatus.SENT_EMAIL.value)

    logger.info(
        "delivery_email_sent",
        extra={"delivery_request_id": str(dr.pk), "provider_message_id": msg_id},
    )


def process_email_pdf_delivery(dr: DeliveryRequest) -> None:
    """Full path: PDF stub + Zavu transport."""

    analysis = dr.analysis
    public_short_id = analysis.public_short_id
    band_label = analysis.band or ""

    now_gate = timezone.now()
    with transaction.atomic():
        locked = DeliveryRequest.objects.select_for_update().get(pk=dr.pk)
        if locked.status == DeliveryRequestStatus.DELIVERED.value:
            return
        if locked.next_attempt_not_before and locked.next_attempt_not_before > now_gate:
            return
        if locked.attempt_count >= locked.max_attempts:
            locked.status = DeliveryRequestStatus.FAILED.value
            locked.last_error_classification = ErrorClassification.PERMANENT.value
            locked.last_error = "max_attempts_exhausted"
            locked.save(update_fields=["status", "last_error", "last_error_classification"])
            DELIVERY_FAILED_TOTAL.labels(channel="email_pdf", reason="exhausted").inc()
            ContractAnalysis.objects.filter(pk=locked.analysis_id).update(delivery_status=DeliveryStatus.FAILED.value)
            return

        locked.attempt_count += 1
        locked.status = DeliveryRequestStatus.SENDING.value
        locked.save(update_fields=["attempt_count", "status"])

    DELIVERY_ATTEMPT_TOTAL.labels(channel="email_pdf").inc()

    composed = compose_delivery_email(public_short_id=public_short_id, band_label=band_label)
    pdf_gen = StubReportPdfGenerator()
    transport = ZavuEmailTransport()

    try:
        to_email = plaintext_email(dr.target_value_encrypted)
    except ValueError as exc:
        _record_failure_and_maybe_retry(dr, ClassifiedDeliveryError(ErrorClassification.PERMANENT.value, "bad_destination", str(exc)))
        return

    start = time.perf_counter()
    try:
        msg_id = transport.send_pdf_email(
            to_email=to_email,
            composed=composed,
            pdf_bytes=pdf_gen.generate_pdf_bytes(analysis_id=str(analysis.pk)),
            idempotency_key=str(dr.pk),
        )
    except ClassifiedDeliveryError as exc:
        elapsed = time.perf_counter() - start
        DELIVERY_SEND_LATENCY_SECONDS.labels(channel="email_pdf").observe(elapsed)
        _record_failure_and_maybe_retry(dr, exc)
        return
    except Exception as exc:
        elapsed = time.perf_counter() - start
        DELIVERY_SEND_LATENCY_SECONDS.labels(channel="email_pdf").observe(elapsed)
        _record_failure_and_maybe_retry(dr, classify_generic(exc))
        return

    elapsed = time.perf_counter() - start
    DELIVERY_SEND_LATENCY_SECONDS.labels(channel="email_pdf").observe(elapsed)

    _finalize_email_pdf_delivery(dr, msg_id=msg_id)


def _record_failure_and_maybe_retry(dr: DeliveryRequest, err: ClassifiedDeliveryError) -> None:
    permanent = err.classification == ErrorClassification.PERMANENT.value
    DELIVERY_FAILED_TOTAL.labels(channel=dr.channel, reason=err.reason_code).inc()

    with transaction.atomic():
        locked = DeliveryRequest.objects.select_for_update().get(pk=dr.pk)
        locked.last_error = err.message[:1024]
        locked.last_error_classification = err.classification

        if permanent or locked.attempt_count >= locked.max_attempts:
            locked.status = DeliveryRequestStatus.FAILED.value
            locked.next_attempt_not_before = None
            locked.save(
                update_fields=[
                    "status",
                    "last_error",
                    "last_error_classification",
                    "next_attempt_not_before",
                ]
            )
            ContractAnalysis.objects.filter(pk=locked.analysis_id).update(delivery_status=DeliveryStatus.FAILED.value)
            return

        locked.status = DeliveryRequestStatus.QUEUED.value
        locked.next_attempt_not_before = next_attempt_not_before(completed_attempt_count=locked.attempt_count)
        locked.save(
            update_fields=[
                "status",
                "last_error",
                "last_error_classification",
                "next_attempt_not_before",
            ]
        )


def _terminal_failure(dr: DeliveryRequest, *, reason_code: str, message: str, permanent: bool) -> None:
    DELIVERY_FAILED_TOTAL.labels(channel=dr.channel, reason=reason_code).inc()
    with transaction.atomic():
        locked = DeliveryRequest.objects.select_for_update().get(pk=dr.pk)
        locked.status = DeliveryRequestStatus.FAILED.value
        locked.last_error = message[:1024]
        locked.last_error_classification = (
            ErrorClassification.PERMANENT.value if permanent else ErrorClassification.TRANSIENT.value
        )
        locked.save(update_fields=["status", "last_error", "last_error_classification"])
        ContractAnalysis.objects.filter(pk=locked.analysis_id).update(delivery_status=DeliveryStatus.FAILED.value)
