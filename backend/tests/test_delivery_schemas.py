"""CS-230 — enum parity + webhook payload helpers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from delivery.domain.schemas import (
    CHANNEL_VALUES,
    DELIVERY_REQUEST_STATUS_VALUES,
    ERROR_CLASSIFICATION_VALUES,
    StrictDeliveryChannel,
    ZavuWebhookPayload,
)
from delivery.domain.enums import DeliveryRequestStatus, ErrorClassification
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
    p = ZavuWebhookPayload.model_validate(
        {"type": "message.delivered", "data": {"message": {"id": "msg_x"}}}
    )
    assert p.resolve_message_id() == "msg_x"
