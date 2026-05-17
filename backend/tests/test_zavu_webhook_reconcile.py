"""CS-357 webhook reconciliation."""

from __future__ import annotations

import pytest

from delivery.application.zavu_webhook import process_zavu_webhook_dict
from delivery.domain.enums import DeliveryRequestStatus
from tests.factories import ContractAnalysisFactory, DeliveryRequestFactory


@pytest.mark.django_db
def test_zavu_webhook_marks_failed_when_provider_failed_event():
    analysis = ContractAnalysisFactory()
    dr = DeliveryRequestFactory(
        analysis=analysis,
        channel="email_pdf",
        provider_message_id="msg_fail",
        status=DeliveryRequestStatus.SENDING.value,
    )

    process_zavu_webhook_dict({"type": "message.failed", "data": {"message": {"id": "msg_fail"}}})

    dr.refresh_from_db()
    assert dr.status == DeliveryRequestStatus.FAILED.value


@pytest.mark.django_db
def test_zavu_webhook_delivered_idempotent():
    analysis = ContractAnalysisFactory()
    dr = DeliveryRequestFactory(
        analysis=analysis,
        channel="email_pdf",
        provider_message_id="msg_ok",
        status=DeliveryRequestStatus.DELIVERED.value,
    )

    process_zavu_webhook_dict({"type": "message.delivered", "data": {"message": {"id": "msg_ok"}}})

    dr.refresh_from_db()
    assert dr.status == DeliveryRequestStatus.DELIVERED.value
