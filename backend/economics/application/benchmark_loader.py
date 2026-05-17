"""CS-130: economic_benchmarks.yaml loader, validator, and DB upsert.

Reads a versioned YAML catalog matching PRD_F5_ANALISIS_ECONOMICO §6.4 and
upserts a `BenchmarkVersion` row plus its `EconomicBenchmark` rows. Mirrors
the structure of `rubric.../load_rubric_catalog.py`:

* validation happens in one pass with actionable `CommandError`-friendly
  exceptions (`BenchmarkLoaderError`);
* upsert runs in a single transaction so partial loads never leak;
* the `BenchmarkVersion` row is immutable by trigger (CS-030) once published,
  so this loader only updates `is_active` on the existing row.

The loader is intentionally pure-Python (no Django code path) until
`upsert_benchmarks` is called, so it can be unit-tested without DB access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from django.db import transaction
from django.utils import timezone

from economics.domain.enums import BenchmarkUnit
from economics.infrastructure.django.models import BenchmarkVersion, EconomicBenchmark

# DOMAIN_MODEL §3.8 caps applicable_contract_types entries at 16 chars (matches
# the ArrayField CharField in the model). Keep the constant local rather than
# importing from models — the loader must work without touching ORM internals.
APPLICABLE_TYPE_MAX = 16
BENCHMARK_KEY_MAX = 64

REQUIRED_TOP_LEVEL = {"version", "released_at", "next_review_due", "benchmarks"}
REQUIRED_BENCHMARK_KEYS = {
    "unit",
    "applicable_contract_types",
    "source",
    "last_updated",
    "next_review_due",
}

VALID_UNITS = {u.value for u in BenchmarkUnit}


class BenchmarkLoaderError(ValueError):
    """Raised when a benchmark YAML file violates the schema contract.

    Carries a path + actionable message so the management command can surface
    it as a `CommandError` without losing context.
    """


@dataclass(frozen=True)
class BenchmarkEntry:
    """One validated benchmark row, ready to upsert."""

    benchmark_key: str
    value_min: Decimal | None
    value_max: Decimal | None
    value_default: Decimal | None
    unit: str
    applicable_contract_types: tuple[str, ...]
    source: str
    source_url: str
    last_updated: date
    next_review_due: date
    notes: str


@dataclass(frozen=True)
class BenchmarkPayload:
    """A parsed and validated benchmarks fixture."""

    version: str
    released_at: datetime
    next_review_due: date
    changelog: str
    entries: tuple[BenchmarkEntry, ...]


# ─── Public API ──────────────────────────────────────────────────────────────


def load_yaml(path: Path | str) -> BenchmarkPayload:
    """Parse and validate a benchmarks YAML file. Raises `BenchmarkLoaderError`."""

    p = Path(path).expanduser()
    if not p.exists():
        raise BenchmarkLoaderError(f"Benchmarks fixture not found: {p}")

    try:
        with p.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise BenchmarkLoaderError(f"Invalid YAML at {p}: {exc}") from exc

    if not isinstance(data, dict):
        raise BenchmarkLoaderError(f"{p}: expected a top-level mapping, got {type(data).__name__}")

    missing = REQUIRED_TOP_LEVEL - set(data)
    if missing:
        raise BenchmarkLoaderError(f"{p}: missing required top-level keys: {sorted(missing)}")

    version = str(data["version"]).strip()
    if not version:
        raise BenchmarkLoaderError(f"{p}: 'version' must be a non-empty string")

    released_at = _parse_datetime(data["released_at"], field="released_at", path=p)
    next_review_due = _parse_date(data["next_review_due"], field="next_review_due", path=p)
    if next_review_due < released_at.date():
        raise BenchmarkLoaderError(
            f"{p}: top-level next_review_due ({next_review_due}) is before released_at ({released_at.date()})"
        )

    changelog = str(data.get("changelog") or "").strip()

    raw_benchmarks = data["benchmarks"]
    if not isinstance(raw_benchmarks, dict) or not raw_benchmarks:
        raise BenchmarkLoaderError(f"{p}: 'benchmarks' must be a non-empty mapping")

    entries: list[BenchmarkEntry] = []
    for key, raw in raw_benchmarks.items():
        entries.append(_validate_entry(key, raw, path=p))

    # Detect duplicate keys (YAML allows them; safe_load keeps the last).
    keys = [e.benchmark_key for e in entries]
    if len(keys) != len(set(keys)):
        seen: set[str] = set()
        dups: list[str] = []
        for k in keys:
            if k in seen:
                dups.append(k)
            seen.add(k)
        raise BenchmarkLoaderError(f"{p}: duplicate benchmark keys: {sorted(set(dups))}")

    return BenchmarkPayload(
        version=version,
        released_at=released_at,
        next_review_due=next_review_due,
        changelog=changelog,
        entries=tuple(entries),
    )


@transaction.atomic
def upsert_benchmarks(
    payload: BenchmarkPayload,
    *,
    activate: bool = False,
) -> tuple[BenchmarkVersion, int, int]:
    """Persist `payload` to the DB. Returns `(version_row, created_count, updated_count)`.

    Idempotent: the `BenchmarkVersion` row is found-or-created (metadata is
    immutable by trigger). Per-row benchmarks are `update_or_create` keyed on
    `(benchmark_key, benchmark_version)`.
    """

    version_obj, _ = BenchmarkVersion.objects.get_or_create(
        version=payload.version,
        defaults={
            "released_at": payload.released_at,
            "changelog": payload.changelog,
            "is_active": False,
        },
    )

    created_count = 0
    updated_count = 0
    for entry in payload.entries:
        _, created = EconomicBenchmark.objects.update_or_create(
            benchmark_key=entry.benchmark_key,
            benchmark_version=version_obj,
            defaults={
                "value_min": entry.value_min,
                "value_max": entry.value_max,
                "value_default": entry.value_default,
                "unit": entry.unit,
                "applicable_contract_types": list(entry.applicable_contract_types),
                "source": entry.source,
                "source_url": entry.source_url,
                "last_updated": entry.last_updated,
                "next_review_due": entry.next_review_due,
            },
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    if activate:
        BenchmarkVersion.objects.exclude(version=payload.version).filter(is_active=True).update(is_active=False)
        if not version_obj.is_active:
            version_obj.is_active = True
            version_obj.save(update_fields=["is_active"])

    return version_obj, created_count, updated_count


# ─── Internals ───────────────────────────────────────────────────────────────


def _validate_entry(key: Any, raw: Any, *, path: Path) -> BenchmarkEntry:  # noqa: PLR0912
    if not isinstance(key, str) or not key.strip():
        raise BenchmarkLoaderError(f"{path}: benchmark key {key!r} must be a non-empty string")
    benchmark_key = key.strip()
    if len(benchmark_key) > BENCHMARK_KEY_MAX:
        raise BenchmarkLoaderError(f"{path}: benchmark_key {benchmark_key!r} exceeds {BENCHMARK_KEY_MAX} chars")

    if not isinstance(raw, dict):
        raise BenchmarkLoaderError(f"{path}: entry {benchmark_key!r} must be a mapping, got {type(raw).__name__}")

    missing = REQUIRED_BENCHMARK_KEYS - set(raw)
    if missing:
        raise BenchmarkLoaderError(f"{path}: entry {benchmark_key!r} missing required fields: {sorted(missing)}")

    # At least one of value_default / value_min / value_max must be set.
    value_default = _opt_decimal(raw.get("value_default"), field="value_default", key=benchmark_key, path=path)
    value_min = _opt_decimal(raw.get("value_min"), field="value_min", key=benchmark_key, path=path)
    value_max = _opt_decimal(raw.get("value_max"), field="value_max", key=benchmark_key, path=path)
    if value_default is None and value_min is None and value_max is None:
        raise BenchmarkLoaderError(
            f"{path}: entry {benchmark_key!r} must define at least one of value_default / value_min / value_max"
        )
    for label, val in (("value_default", value_default), ("value_min", value_min), ("value_max", value_max)):
        if val is not None and val < Decimal("0"):
            raise BenchmarkLoaderError(f"{path}: entry {benchmark_key!r} {label} must be >= 0, got {val}")
    if value_min is not None and value_max is not None and value_min > value_max:
        raise BenchmarkLoaderError(
            f"{path}: entry {benchmark_key!r} value_min ({value_min}) > value_max ({value_max})"
        )

    unit = str(raw["unit"]).strip()
    if unit not in VALID_UNITS:
        raise BenchmarkLoaderError(f"{path}: entry {benchmark_key!r} unit {unit!r} not in {sorted(VALID_UNITS)}")

    types_raw = raw["applicable_contract_types"]
    if not isinstance(types_raw, list) or not types_raw:
        raise BenchmarkLoaderError(
            f"{path}: entry {benchmark_key!r} applicable_contract_types must be a non-empty list"
        )
    applicable_types: list[str] = []
    for item in types_raw:
        s = str(item).strip()
        if not s:
            raise BenchmarkLoaderError(
                f"{path}: entry {benchmark_key!r} applicable_contract_types contains an empty entry"
            )
        if len(s) > APPLICABLE_TYPE_MAX:
            raise BenchmarkLoaderError(
                f"{path}: entry {benchmark_key!r} applicable_contract_types entry {s!r} "
                f"exceeds {APPLICABLE_TYPE_MAX} chars"
            )
        applicable_types.append(s)

    source = str(raw["source"]).strip()
    if not source:
        raise BenchmarkLoaderError(f"{path}: entry {benchmark_key!r} source must be non-empty")
    source_url = str(raw.get("source_url") or "").strip()
    notes = str(raw.get("notes") or "").strip()

    last_updated = _parse_date(raw["last_updated"], field=f"{benchmark_key}.last_updated", path=path)
    next_review_due = _parse_date(raw["next_review_due"], field=f"{benchmark_key}.next_review_due", path=path)
    if next_review_due < last_updated:
        raise BenchmarkLoaderError(
            f"{path}: entry {benchmark_key!r} next_review_due ({next_review_due}) "
            f"is before last_updated ({last_updated})"
        )

    return BenchmarkEntry(
        benchmark_key=benchmark_key,
        value_min=value_min,
        value_max=value_max,
        value_default=value_default,
        unit=unit,
        applicable_contract_types=tuple(applicable_types),
        source=source,
        source_url=source_url,
        last_updated=last_updated,
        next_review_due=next_review_due,
        notes=notes,
    )


def _opt_decimal(value: Any, *, field: str, key: str, path: Path) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise BenchmarkLoaderError(f"{path}: entry {key!r} {field}={value!r} is not a valid decimal: {exc}") from exc


def _parse_date(value: Any, *, field: str, path: Path) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return date.fromisoformat(text.split("T", 1)[0])
    except ValueError as exc:
        raise BenchmarkLoaderError(f"{path}: field {field!r} value {value!r} is not an ISO date: {exc}") from exc


def _parse_datetime(value: Any, *, field: str, path: Path) -> datetime:
    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value, UTC)
    if isinstance(value, date):
        return timezone.make_aware(datetime(value.year, value.month, value.day), UTC)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise BenchmarkLoaderError(f"{path}: field {field!r} value {value!r} is not an ISO datetime: {exc}") from exc
    return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed, UTC)
