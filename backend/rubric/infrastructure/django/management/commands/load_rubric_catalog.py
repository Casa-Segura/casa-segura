"""CS-033: idempotent loader for the 38/42-criterion rubric catalog.

Reads the canonical YAML transcription of RUBRICA_CONTRATO.md §16 and
upserts a `RubricVersion` row plus its `Criterion` rows into the database.

Re-runs are safe: rows are looked up by `(code, rubric_version)` and updated
in place; the `RubricVersion` row is looked up by `version` and its mutable
fields are refreshed each run. Both inserts and updates happen inside a
single transaction so partial loads never leak into the database.

Default fixture path: `backend/fixtures/rubric_v1.yaml`.

Usage:
    python manage.py load_rubric_catalog
    python manage.py load_rubric_catalog --rubric-version 1.0.0
    python manage.py load_rubric_catalog --fixture path/to/file.yaml --activate

Companion to `seed_rubric_version`, which only bootstraps the `RubricVersion`
row. This command additionally seeds the per-criterion catalog so
AC1 (count == 38) and AC2 (per-category weights) of CS-033 can be met.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from rubric.domain.enums import Category
from rubric.infrastructure.django.models import Criterion, RubricVersion

DEFAULT_VERSION = "1.0.0"
DEFAULT_FIXTURE = "fixtures/rubric_v1.yaml"

# Per Django model: ArrayField CharFields cap at max_length=16 / 64.
APPLICABLE_TYPE_MAX = 16
LEGAL_ANCHOR_MAX = 64

REQUIRED_CRITERION_KEYS = {
    "code",
    "category",
    "title",
    "description",
    "weight_in_category",
    "applicable_types",
    "evaluation_prompt",
    "scoring_scale",
}


class Command(BaseCommand):
    help = (
        "Idempotently load the RubricVersion + Criterion catalog from a YAML fixture. "
        "Reads docs/Casa Segura Formal PRDs/RUBRICA_CONTRATO.md transcribed under "
        "backend/fixtures/rubric_v1.yaml by default."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--rubric-version",
            default=DEFAULT_VERSION,
            dest="rubric_version",
            help="Semver of the rubric to load (default 1.0.0).",
        )
        parser.add_argument(
            "--fixture",
            default=None,
            dest="fixture",
            help=(
                "Path to the YAML fixture. Defaults to "
                "<BASE_DIR>/fixtures/rubric_v1.yaml."
            ),
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            help="After loading, mark this version is_active=True (deactivates any other).",
        )

    # ------------------------------------------------------------------ handle

    def handle(self, *args: Any, **opts: Any) -> None:  # noqa: PLR0912 — sequential orchestration: load → validate → drift-warn → upsert → activate; splitting bloats more than it clarifies.
        rubric_version: str = opts["rubric_version"]
        fixture_arg: str | None = opts["fixture"]
        activate: bool = opts["activate"]

        fixture_path = self._resolve_fixture_path(fixture_arg)
        if not fixture_path.exists():
            raise CommandError(f"Fixture not found: {fixture_path}")

        data = self._load_yaml(fixture_path)
        self._validate_payload(data, fixture_path, rubric_version)

        criteria_payload: list[dict[str, Any]] = data["criteria"]
        categories_payload: dict[str, Any] = data["categories"]

        released_at = _parse_released_at(data.get("released_at"))
        changelog = (data.get("changelog") or "").strip()

        with transaction.atomic():
            version_obj, version_created = RubricVersion.objects.get_or_create(
                version=rubric_version,
                defaults={
                    "released_at": released_at or timezone.now(),
                    "criteria_count": len(criteria_payload),
                    "categories": categories_payload,
                    "criteria_definitions_path": str(fixture_path),
                    "changelog": changelog,
                    "is_active": False,
                },
            )

            # `rubric_version` rows are immutable by trigger (CS-030 /
            # reject_catalog_mutation): only `is_active` may flip. We therefore
            # never UPDATE metadata here. If the existing row's
            # criteria_count / categories drift from the fixture, surface a
            # loud warning so a follow-up ticket can clean it up out-of-band.
            drift_warnings: list[str] = []
            if not version_created:
                if version_obj.criteria_count != len(criteria_payload):
                    drift_warnings.append(
                        f"rubric_version.criteria_count={version_obj.criteria_count} "
                        f"but fixture has {len(criteria_payload)} entries"
                    )
                if version_obj.categories != categories_payload:
                    drift_warnings.append(
                        "rubric_version.categories drifted from fixture (immutable; "
                        "requires manual reconciliation)"
                    )

            created_count = 0
            updated_count = 0
            for idx, raw in enumerate(criteria_payload, start=1):
                missing = REQUIRED_CRITERION_KEYS - set(raw)
                if missing:
                    raise CommandError(
                        f"{fixture_path}:criteria[{idx}] missing required fields: "
                        f"{sorted(missing)}"
                    )

                defaults = _criterion_defaults(raw, fixture_path, idx)

                _, created = Criterion.objects.update_or_create(
                    code=raw["code"],
                    rubric_version=version_obj,
                    defaults=defaults,
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            if activate:
                RubricVersion.objects.exclude(version=rubric_version).filter(
                    is_active=True
                ).update(is_active=False)
                if not version_obj.is_active:
                    version_obj.is_active = True
                    version_obj.save(update_fields=["is_active", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {len(criteria_payload)} criteria into rubric_version "
                f"{rubric_version} (created={created_count}, updated={updated_count})"
            )
        )
        if version_created:
            self.stdout.write(self.style.SUCCESS(f"  RubricVersion {rubric_version}: created"))
        else:
            self.stdout.write(f"  RubricVersion {rubric_version}: existed (metadata is immutable)")
        for warning in drift_warnings:
            self.stdout.write(self.style.WARNING(f"  drift: {warning}"))
        if activate:
            self.stdout.write(self.style.SUCCESS(f"  RubricVersion {rubric_version}: activated"))

    # --------------------------------------------------------------- helpers

    def _resolve_fixture_path(self, fixture_arg: str | None) -> Path:
        if fixture_arg:
            return Path(fixture_arg).expanduser().resolve()
        # Default lives in backend/fixtures/ (BASE_DIR == backend/).
        return (Path(settings.BASE_DIR) / DEFAULT_FIXTURE).resolve()

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise CommandError(f"Invalid YAML at {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise CommandError(f"{path}: expected a top-level mapping, got {type(data).__name__}")
        return data

    def _validate_payload(self, data: dict[str, Any], path: Path, expected_version: str) -> None:
        missing_top = {"rubric_version", "categories", "criteria"} - set(data)
        if missing_top:
            raise CommandError(
                f"{path}: missing required top-level keys: {sorted(missing_top)}"
            )
        if data["rubric_version"] != expected_version:
            raise CommandError(
                f"{path}: rubric_version in fixture is '{data['rubric_version']}' "
                f"but --rubric-version is '{expected_version}'. Pass --rubric-version "
                "to match the fixture or load the correct YAML file."
            )
        if not isinstance(data["criteria"], list) or not data["criteria"]:
            raise CommandError(f"{path}: 'criteria' must be a non-empty list")
        if not isinstance(data["categories"], dict) or not data["categories"]:
            raise CommandError(f"{path}: 'categories' must be a non-empty mapping")

        valid_categories = {c.value for c in Category}
        fixture_categories = set(data["categories"].keys())
        unknown = fixture_categories - valid_categories
        if unknown:
            raise CommandError(
                f"{path}: unknown categories in fixture: {sorted(unknown)}; "
                f"expected subset of {sorted(valid_categories)}"
            )


# ----------------------------------------------------------------- coercion


def _criterion_defaults(raw: dict[str, Any], path: Path, idx: int) -> dict[str, Any]:
    """Coerce one YAML criterion entry into model field values."""

    category = raw["category"]
    if category not in {c.value for c in Category}:
        raise CommandError(
            f"{path}:criteria[{idx}] (code={raw['code']!r}) has invalid category {category!r}"
        )

    weight = Decimal(str(raw["weight_in_category"]))
    if not (Decimal("0") < weight <= Decimal("100")):
        raise CommandError(
            f"{path}:criteria[{idx}] (code={raw['code']!r}) weight_in_category "
            f"{weight} outside (0, 100]"
        )

    applicable_types = _ensure_string_list(
        raw["applicable_types"],
        path,
        idx,
        field="applicable_types",
        max_len=APPLICABLE_TYPE_MAX,
    )
    legal_anchor = _ensure_string_list(
        raw.get("legal_anchor") or [],
        path,
        idx,
        field="legal_anchor",
        max_len=LEGAL_ANCHOR_MAX,
        allow_empty=True,
    )

    scoring_scale = raw["scoring_scale"]
    if not isinstance(scoring_scale, dict) or not scoring_scale:
        raise CommandError(
            f"{path}:criteria[{idx}] (code={raw['code']!r}) scoring_scale "
            "must be a non-empty mapping of score -> description"
        )

    defaults: dict[str, Any] = {
        "category": category,
        "title": str(raw["title"]).strip(),
        "description": str(raw["description"]).strip(),
        "weight_in_category": weight,
        "applicable_types": applicable_types,
        "legal_anchor": legal_anchor,
        "override_code": raw.get("override_code") or None,
        "evaluation_prompt": str(raw["evaluation_prompt"]).strip(),
        "scoring_scale": scoring_scale,
    }

    if "worst_case_when_unverifiable" in raw and raw["worst_case_when_unverifiable"] is not None:
        defaults["worst_case_when_unverifiable"] = Decimal(
            str(raw["worst_case_when_unverifiable"])
        )

    return defaults


def _ensure_string_list(
    value: Any,
    path: Path,
    idx: int,
    *,
    field: str,
    max_len: int,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        raise CommandError(
            f"{path}:criteria[{idx}] field {field!r} must be a list, got {type(value).__name__}"
        )
    if not value and not allow_empty:
        raise CommandError(
            f"{path}:criteria[{idx}] field {field!r} must contain at least one entry"
        )
    out: list[str] = []
    for item in value:
        s = str(item).strip()
        if not s:
            raise CommandError(
                f"{path}:criteria[{idx}] field {field!r} contains an empty string"
            )
        if len(s) > max_len:
            raise CommandError(
                f"{path}:criteria[{idx}] field {field!r} entry {s!r} exceeds "
                f"max length {max_len}"
            )
        out.append(s)
    return out


def _parse_released_at(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value, timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise CommandError(f"Invalid released_at value {value!r}: {exc}") from exc
    return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed, timezone.utc)
