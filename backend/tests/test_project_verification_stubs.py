"""EPIC-12 optional project-verification DRF stubs (CS-356)."""

from __future__ import annotations

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APIClient


def _tiny_png_upload() -> SimpleUploadedFile:
    """Minimal valid PNG (~70 bytes)."""
    buf = BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")
    return SimpleUploadedFile("stub.png", buf.getvalue(), content_type="image/png")


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


_MANUAL_PAYLOAD = {
    "developer": "DevCo",
    "project": "Torre ejemplo",
    "permit": "P-1024",
    "address": "Colonia Escalón, San Salvador",
}


@pytest.mark.django_db
@pytest.mark.parametrize("path_suffix", ["manual/", "billboard-upload/", "demo-result/"])
def test_project_verification_forbidden_when_disabled(
    api_client: APIClient, path_suffix: str
):
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
def test_manual_returns_reference_and_echo(api_client: APIClient):
    resp = api_client.post(
        "/api/v1/project-verification/manual/",
        _MANUAL_PAYLOAD,
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    ref = data.get("reference_id")
    assert isinstance(ref, str) and len(ref) >= 32
    assert data.get("stub") is True
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
@override_settings(PROJECT_VERIFICATION_ENABLED=True)
def test_billboard_upload_returns_202_stub(api_client: APIClient):
    resp = api_client.post(
        "/api/v1/project-verification/billboard-upload/",
        {"image": _tiny_png_upload()},
        format="multipart",
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data.get("stub") is True


@pytest.mark.django_db
@override_settings(PROJECT_VERIFICATION_ENABLED=True)
@pytest.mark.parametrize(
    ("verdict", "headline_kw"),
    [("green", "alentadora"), ("red", "Riesgos")],
)
def test_demo_result_returns_fixture_aligned_json(
    api_client: APIClient, verdict: str, headline_kw: str
):
    resp = api_client.get(
        "/api/v1/project-verification/demo-result/",
        {"v": verdict},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == verdict
    assert headline_kw in data["headline"]
    assert isinstance(data["rationale"], list)
    assert "data_freshness_note" in data
