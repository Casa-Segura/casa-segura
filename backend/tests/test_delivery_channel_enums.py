from __future__ import annotations

import pytest

from platform_core.domain.enums import DeliveryChannel, DeliveryStatus


def test_delivery_channels_are_sms_email_link_only():
    assert [channel.value for channel in DeliveryChannel] == [
        "sms_summary",
        "email_pdf",
        "web_link",
    ]
    assert "whatsapp_summary" not in {channel.value for channel in DeliveryChannel}


def test_contract_analysis_delivery_status_uses_sms_terminal_state():
    assert DeliveryStatus.SENT_SMS.value == "sent_sms"
    assert "sent_whatsapp" not in {status.value for status in DeliveryStatus}


@pytest.mark.django_db
def test_delivery_request_channel_constraint_matches_enum():
    from delivery.infrastructure.django.models import DeliveryRequest

    constraint = next(
        c
        for c in DeliveryRequest._meta.constraints
        if c.name == "ck_delivery_channel_enum"
    )
    assert "sms_summary" in str(constraint.condition)
    assert "whatsapp_summary" not in str(constraint.condition)
