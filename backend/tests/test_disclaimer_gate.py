"""CS-058 — strict disclaimer parsing + multipart aliases."""

from __future__ import annotations

import pytest

from ingestion.interfaces.api.disclaimer_gate import (
    merge_submission_upload_aliases,
    require_disclaimer_accepted_or_raise,
)
from shared.domain.exceptions import DomainException


def test_merge_maps_frontend_aliases():
    raw = {
        "file": "x",
        "disclaimer_acceptance_method": "checkbox",
        "submission_source": "web",
        "disclaimer_accepted": "true",
    }
    merged = merge_submission_upload_aliases(raw)
    assert merged["disclaimer_method"] == "checkbox"
    assert merged["source"] == "web"
    assert merged["disclaimer_accepted"] == "true"


def test_merge_prefers_canonical_keys_when_present():
    raw = {
        "disclaimer_method": "checkbox",
        "disclaimer_acceptance_method": "checkbox",
        "source": "web",
        "submission_source": "web",
    }
    merged = merge_submission_upload_aliases(raw)
    assert merged["disclaimer_method"] == "checkbox"
    assert merged["source"] == "web"


@pytest.mark.parametrize(
    "accept_val",
    [True, "true", "True", "1"],
)
def test_require_disclaimer_accepts_canonical_true(accept_val):
    require_disclaimer_accepted_or_raise({"disclaimer_accepted": accept_val})


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param({}, id="missing"),
        pytest.param({"disclaimer_accepted": False}, id="false_bool"),
        pytest.param({"disclaimer_accepted": "false"}, id="false_str"),
        pytest.param({"disclaimer_accepted": "yes"}, id="yes_str"),
        pytest.param({"disclaimer_accepted": ""}, id="empty_str"),
    ],
)
def test_require_disclaimer_rejects_bad_values(bad):
    with pytest.raises(DomainException) as exc:
        require_disclaimer_accepted_or_raise(bad)
    assert exc.value.code == "DISCLAIMER_REQUIRED"
