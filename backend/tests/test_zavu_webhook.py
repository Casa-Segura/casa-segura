"""Zavu webhook signature + endpoint (docs.zavu.dev receiving-messages/security)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from rest_framework.test import APIClient

from django.test import override_settings

from delivery.interfaces.api.zavu_signature import verify_zavu_signature


def _sign(*, secret: str, raw_body: bytes, ts: int) -> str:
    signed_payload = f"{ts}.{raw_body.decode('utf-8')}"
    digest = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"t={ts},v1={digest}"


@pytest.mark.django_db
def test_zavu_webhook_rejects_when_secret_not_configured():
    client = APIClient()
    with override_settings(ZAVU_WEBHOOK_SECRET=""):
        resp = client.post(
            "/api/v1/webhooks/zavu/",
            data=b"{}",
            content_type="application/json",
            HTTP_X_ZAVU_SIGNATURE="t=1,v1=ab",
        )
    assert resp.status_code == 503


@pytest.mark.django_db
def test_zavu_webhook_rejects_bad_signature():
    client = APIClient()
    body = json.dumps({"type": "message.delivered"}).encode()
    ts = int(time.time())
    with override_settings(ZAVU_WEBHOOK_SECRET="whsec_test"):
        resp = client.post(
            "/api/v1/webhooks/zavu/",
            data=body,
            content_type="application/json",
            HTTP_X_ZAVU_SIGNATURE=_sign(secret="wrong", raw_body=body, ts=ts),
        )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_zavu_webhook_accepts_valid_signature():
    client = APIClient()
    secret = "whsec_verify_ok"
    ts = int(time.time())
    body = json.dumps({"type": "message.delivered"}).encode()
    hdr = _sign(secret=secret, raw_body=body, ts=ts)

    with override_settings(ZAVU_WEBHOOK_SECRET=secret):
        resp = client.generic(
            "POST",
            "/api/v1/webhooks/zavu/",
            data=body,
            content_type="application/json",
            HTTP_X_ZAVU_SIGNATURE=hdr,
        )

    assert resp.status_code == 200
    assert resp.json() == {"status": "received"}


def test_verify_zavu_signature_true_for_docs_shape():
    secret = "whsec_x"
    raw = b'{"type":"ping"}'
    ts = int(time.time())
    hdr = _sign(secret=secret, raw_body=raw, ts=ts)
    assert verify_zavu_signature(
        signature_header=hdr,
        raw_body=raw,
        secret=secret,
        now=ts,
    )


def test_verify_zavu_signature_rejects_expired_timestamp():
    secret = "whsec_x"
    raw = b"{}"
    ts = int(time.time()) - 400
    hdr = _sign(secret=secret, raw_body=raw, ts=ts)
    assert not verify_zavu_signature(
        signature_header=hdr,
        raw_body=raw,
        secret=secret,
        now=ts + 400,
    )
