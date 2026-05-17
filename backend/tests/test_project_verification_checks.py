"""Django deployment checks for optional project verification (CS-356 / CS-353)."""

from __future__ import annotations

import pytest

from django.test import override_settings

from project_verification.checks import reputation_http_adapter_requires_ready_flag


@pytest.mark.django_db
@override_settings(
    PROJECT_REPUTATION_PROVIDER="http",
    PROJECT_REPUTATION_ADAPTER_READY=False,
)
def test_http_adapter_requires_explicit_ready():

    errs = reputation_http_adapter_requires_ready_flag(None)

    assert any(e.id == "project_verification.E001" for e in errs)


@pytest.mark.django_db
@override_settings(
    PROJECT_REPUTATION_PROVIDER="http",
    PROJECT_REPUTATION_ADAPTER_READY=True,
)
def test_http_adapter_allowed_when_explicit_ready():

    errs = reputation_http_adapter_requires_ready_flag(None)

    assert errs == []


@pytest.mark.django_db
@override_settings(PROJECT_REPUTATION_PROVIDER="nope")
def test_unknown_adapter_name_is_error():

    errs = reputation_http_adapter_requires_ready_flag(None)

    assert any(e.id == "project_verification.E002" for e in errs)
