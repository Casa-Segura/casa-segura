"""EPIC-12 optional project-verification DRF API (gates + OCR + verdict)."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image
from rest_framework.test import APIClient

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings


def _tiny_png_upload() -> SimpleUploadedFile:
    """Minimal valid PNG (~70 bytes)."""
    buf = BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")
    return SimpleUploadedFile("stub.png", buf.getvalue(), content_type="image/png")


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


_MANUAL_PAYLOAD = {
    "developer": "Torre Alta",
    "project": "Reserva Lomas",
    "permit": "P-2024-001",
    "address": "Zona cercana al redondel ejemplo",
}


@pytest.mark.django_db
@pytest.mark.parametrize("path_suffix", ["manual/", "billboard-upload/", "demo-result/"])
def test_project_verification_forbidden_when_disabled(api_client: APIClient, path_suffix: str):
    urls = {"manual/": "post", "billboard-upload/": "post", "demo-result/": "get"}
    method = urls[path_suffix]

    kwargs: dict = {}
    if path_suffix == "manual/":
        kwargs = dict(data=_MANUAL_PAYLOAD, format="json")
    elif path_suffix == "billboard-upload/":
        kwargs = dict(data={"image": _tiny_png_upload()}, format="multipart")

    with override_settings(PROJECT_VERIFICATION_ENABLED=False):
        resp = getattr(api_client, method)(
            f"/api/v1/project-verification/{path_suffix}",
            **kwargs,
        )

    assert resp.status_code == 403
    body = resp.json()
    assert body["error_code"] == "project_verification_disabled"
    assert body["schema_version"]
    assert "correlation_id" in body


@pytest.mark.django_db
@override_settings(PROJECT_VERIFICATION_ENABLED=True)
def test_manual_returns_verdict_bundle(api_client: APIClient):
    resp = api_client.post(
        "/api/v1/project-verification/manual/",
        _MANUAL_PAYLOAD,
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    ref = data.get("reference_id")
    assert isinstance(ref, str) and len(ref) >= 32
    assert data.get("verdict") in {"green", "yellow", "red"}
    echo = data.get("echo")
    assert isinstance(echo, dict)
    for key in ("developer", "project", "permit", "address"):
        assert echo.get(key) == _MANUAL_PAYLOAD[key]


@pytest.mark.django_db
@override_settings(PROJECT_VERIFICATION_ENABLED=True)
def test_manual_validation_requires_fields(api_client: APIClient):
    resp = api_client.post(
        "/api/v1/project-verification/manual/",
        {
            "developer": "",
            "project": "",
            "permit": "",
            "address": "",
        },
        format="json",
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "validation_error"
    details = body.get("details") or {}
    assert "developer" in details


@pytest.mark.django_db
@override_settings(PROJECT_VERIFICATION_ENABLED=True)
def test_manual_rejects_overflow_fields(api_client: APIClient):
    long_text = "x" * 241
    resp = api_client.post(
        "/api/v1/project-verification/manual/",
        {**_MANUAL_PAYLOAD, "developer": long_text},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.json().get("error_code") == "validation_error"


@pytest.mark.django_db
@override_settings(
    PROJECT_VERIFICATION_ENABLED=True,
    OPENROUTER_API_KEY="",
)
def test_billboard_upload_handles_missing_openrouter_without_500(api_client: APIClient):
    resp = api_client.post(
        "/api/v1/project-verification/billboard-upload/",
        {"image": _tiny_png_upload()},
        format="multipart",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ocr_status") == "failure"
    assert isinstance(data.get("fields"), dict)
    assert isinstance(data.get("manual_prefill"), dict)


@pytest.mark.django_db
@override_settings(PROJECT_VERIFICATION_ENABLED=True)
def test_billboard_rejects_bad_mime(api_client: APIClient):
    bad = SimpleUploadedFile(
        "x.bin",
        b"not-an-image",
        content_type="application/octet-stream",
    )
    resp = api_client.post(
        "/api/v1/project-verification/billboard-upload/",
        {"image": bad},
        format="multipart",
    )
    assert resp.status_code == 415
    assert resp.json().get("error_code") == "unsupported_media"


@pytest.mark.django_db
@override_settings(PROJECT_VERIFICATION_ENABLED=True)
@pytest.mark.parametrize("verdict_key", ["green", "yellow", "red"])
def test_demo_result_returns_fixture_keys(api_client: APIClient, verdict_key: str):
    resp = api_client.get(
        "/api/v1/project-verification/demo-result/",
        {"v": verdict_key},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == verdict_key
    assert data.get("headline_key")
    assert isinstance(data.get("rationale_keys"), list)


@pytest.mark.django_db
@override_settings(PROJECT_VERIFICATION_ENABLED=True)
def test_submission_source_billboard_keeps_evaluation_path(api_client: APIClient):
    payload = {
        **_MANUAL_PAYLOAD,
        "submission_source": "billboard_ocr",
        "ocr_quality": "high",
    }
    resp = api_client.post(
        "/api/v1/project-verification/manual/",
        payload,
        format="json",
    )
    assert resp.status_code == 201

