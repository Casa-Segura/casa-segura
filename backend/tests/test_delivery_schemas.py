"""CS-230 — enum parity + webhook payload helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr, ValidationError

from delivery.domain.enums import DeliveryRequestStatus, ErrorClassification
from delivery.domain.schemas import (
    CHANNEL_VALUES,
    DELIVERY_REQUEST_STATUS_VALUES,
    ERROR_CLASSIFICATION_VALUES,
    DeliveryChannelDTO,
    DeliveryRequestDTO,
    DeliveryRequestStatusDTO,
    EnqueueDeliveryPayload,
    StrictDeliveryChannel,
    ZavuWebhookPayload,
)
from platform_core.domain.enums import DeliveryChannel


def test_channel_literals_match_platform_enum():
    db_vals = {c.value for c in DeliveryChannel}
    assert CHANNEL_VALUES == db_vals


def test_delivery_request_status_literals_match_enum():
    db_vals = {s.value for s in DeliveryRequestStatus}
    assert DELIVERY_REQUEST_STATUS_VALUES == db_vals


def test_error_classification_literals_match_enum():
    db_vals = {e.value for e in ErrorClassification}
    assert ERROR_CLASSIFICATION_VALUES == db_vals


def test_strict_delivery_channel_rejects_whatsapp_alias():
    with pytest.raises(ValidationError):
        StrictDeliveryChannel.model_validate({"channel": "whatsapp_summary"})


def test_zavu_webhook_resolves_message_id_from_nested_dict():
    p = ZavuWebhookPayload.model_validate({"type": "message.delivered", "data": {"message": {"id": "msg_x"}}})
    assert p.resolve_message_id() == "msg_x"


def test_enqueue_payload_allows_web_link_without_target_hash():
    p = EnqueueDeliveryPayload(
        analysis_id="a1",
        channel=DeliveryChannelDTO.WEB_LINK,
        target_hash="",
    )
    assert p.channel == DeliveryChannelDTO.WEB_LINK


def test_enqueue_payload_requires_target_hash_for_email():
    with pytest.raises(ValidationError):
        EnqueueDeliveryPayload(
            analysis_id="a1",
            channel=DeliveryChannelDTO.EMAIL_PDF,
            target_hash="",
        )


def test_enqueue_payload_rejects_attempt_when_no_retries_remain():
    with pytest.raises(ValidationError):
        EnqueueDeliveryPayload(
            analysis_id="a1",
            channel=DeliveryChannelDTO.SMS_SUMMARY,
            target_hash="ab",
            attempt_count=3,
            max_attempts=3,
        )


def test_delivery_request_dto_excludes_encrypted_target_from_dump():
    exp = datetime.now(UTC) + timedelta(days=7)
    dto = DeliveryRequestDTO(
        id="00000000-0000-0000-0000-000000000001",
        analysis_id="00000000-0000-0000-0000-000000000002",
        channel=DeliveryChannelDTO.EMAIL_PDF,
        target_hash="abc",
        status=DeliveryRequestStatusDTO.QUEUED,
        attempt_count=0,
        max_attempts=3,
        expires_at=exp,
        target_value_encrypted=SecretStr("enc::secret"),
    )
    dumped = dto.model_dump()
    assert "target_value_encrypted" not in dumped
