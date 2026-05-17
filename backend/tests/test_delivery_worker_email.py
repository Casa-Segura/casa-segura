"""Email worker happy path — CS-237."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from delivery.application.worker_handlers import process_email_pdf_delivery
from delivery.domain.enums import DeliveryRequestStatus
from platform_core.domain.enums import DeliveryStatus
from tests.factories import ContractAnalysisFactory, DeliveryRequestFactory


@pytest.mark.django_db
@patch("delivery.infrastructure.external.zavu_email_transport.send_zavu_email")
def test_email_delivery_worker_success_updates_rows(mock_send: MagicMock):
    mock_send.return_value = "msg_integration_worker"
    analysis = ContractAnalysisFactory()
    dr = DeliveryRequestFactory(
        analysis=analysis,
        channel="email_pdf",
        target_value_encrypted="enc::owner@example.com",
        status=DeliveryRequestStatus.QUEUED.value,
    )

    process_email_pdf_delivery(dr)

    dr.refresh_from_db()
    analysis.refresh_from_db()
    assert dr.status == DeliveryRequestStatus.DELIVERED.value
    assert dr.provider_message_id == "msg_integration_worker"
    assert dr.target_value_encrypted is None
    assert analysis.delivery_status == DeliveryStatus.SENT_EMAIL.value
