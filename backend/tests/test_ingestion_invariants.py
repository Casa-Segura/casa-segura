"""CS-057: discard-after-extract invariant.

The extracted contract text MUST NEVER be persisted. We enforce this in
three ways:

  1. Model-level: no model declares an `extracted_text` field.
  2. Service-level: `_persist_success` only writes metadata columns.
  3. Test-level (this file): a meta-test scans the Django model registry
     and fails CI if anyone adds a column matching the disallowed names.
"""

from __future__ import annotations

import pytest

from django.apps import apps

FORBIDDEN_FIELD_NAMES = {
    "extracted_text",
    "ocr_text",
    "raw_text",
    "contract_text",
    "document_text",
}


@pytest.mark.django_db(transaction=False)
def test_no_model_persists_extracted_text():
    """No table may carry the full extracted contract text."""

    offenders: list[str] = []
    for model in apps.get_models():
        for field in model._meta.get_fields():
            name = getattr(field, "name", "")
            if name in FORBIDDEN_FIELD_NAMES:
                offenders.append(f"{model.__module__}.{model.__name__}.{name}")

    assert not offenders, (
        "CS-057 invariant violation: extracted contract text must not be persisted. Offenders: " + ", ".join(offenders)
    )


@pytest.mark.django_db
def test_contract_submission_has_no_text_column():
    """Spot-check: ContractSubmission only carries token_count + language."""

    from ingestion.infrastructure.django.models import ContractSubmission

    field_names = {f.name for f in ContractSubmission._meta.get_fields()}
    assert "extracted_text" not in field_names
    assert "extracted_text_token_count" in field_names
    assert "extracted_text_language" in field_names
