"""Unit tests for Zavu outbound email helper (mocked SDK)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from django.test import override_settings

from delivery.infrastructure.external.zavu_messaging import send_zavu_email, zavu_email_download_link_html


def test_zavu_email_download_link_html_escapes():
    html_out = zavu_email_download_link_html(
        url="https://example.com/a?x=1&y=2",
        link_text="Click <report>",
    )
    assert "Click &lt;report&gt;" in html_out or "&lt;report&gt;" in html_out
    assert 'href="https://example.com/a?x=1&amp;y=2"' in html_out


@override_settings(ZAVUDEV_API_KEY="zk_test_x", ZAVU_SENDER_ID="snd_default")
@patch("delivery.infrastructure.external.zavu_messaging.Zavudev")
def test_send_zavu_email_passes_channel_and_merges_attachments(mock_zavu_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.message.id = "msg_integration_test"
    mock_client.messages.send.return_value = mock_response
    mock_zavu_cls.return_value = mock_client

    mid = send_zavu_email(
        to="user@example.com",
        subject="Hi",
        text="Hello",
        html_body="<p>Hello</p>",
        attachments=[{"filename": "a.pdf", "path": "https://cdn.example.com/a.pdf"}],
    )

    assert mid == "msg_integration_test"
    mock_zavu_cls.assert_called_once_with(api_key="zk_test_x")
    mock_client.messages.send.assert_called_once()
    call_kw = mock_client.messages.send.call_args.kwargs
    assert call_kw["to"] == "user@example.com"
    assert call_kw["channel"] == "email"
    assert call_kw["subject"] == "Hi"
    assert call_kw["zavu_sender"] == "snd_default"
    assert call_kw["extra_body"] == {"attachments": [{"filename": "a.pdf", "path": "https://cdn.example.com/a.pdf"}]}


@override_settings(ZAVUDEV_API_KEY="", ZAVU_API_KEY="")
def test_send_zavu_email_requires_key() -> None:
    with pytest.raises(ValueError, match="ZAVUDEV_API_KEY"):
        send_zavu_email(to="u@example.com", subject="s", text="t")
