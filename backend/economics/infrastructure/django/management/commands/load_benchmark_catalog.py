"""CS-130: idempotent loader for the economic benchmarks catalog.

Reads `backend/fixtures/economic_benchmarks_<version>.yaml` and upserts a
`BenchmarkVersion` row plus its `EconomicBenchmark` rows. Companion to
`seed_benchmark_version` (which only inserts the version row).

Usage:
    python manage.py load_benchmark_catalog
    python manage.py load_benchmark_catalog \\
        --fixture backend/fixtures/economic_benchmarks_2026q2.yaml \\
        --benchmark-version 2026-Q2 --activate

Validation happens in `economics.application.benchmark_loader.load_yaml`; this
command only translates `BenchmarkLoaderError` into `CommandError` and drives
the DB upsert inside a single `transaction.atomic`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from economics.application.benchmark_loader import (
    BenchmarkLoaderError,
    load_yaml,
    upsert_benchmarks,
)

DEFAULT_FIXTURE = "fixtures/economic_benchmarks_2026q2.yaml"


class Command(BaseCommand):
    help = (
        "Idempotently load the BenchmarkVersion + EconomicBenchmark catalog from a YAML "
        "fixture. Default fixture: backend/fixtures/economic_benchmarks_2026q2.yaml."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--fixture",
            default=None,
            dest="fixture",
            help="Path to the YAML fixture. Defaults to <BASE_DIR>/fixtures/economic_benchmarks_2026q2.yaml.",
        )
        parser.add_argument(
            "--benchmark-version",
            default=None,
            dest="benchmark_version",
            help=(
                "Expected version string. Optional — when omitted the loader trusts the "
                "fixture's top-level `version`. When provided, must match the fixture."
            ),
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            help="After loading, mark this version is_active=True (deactivates any other).",
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        fixture_arg: str | None = opts["fixture"]
        expected_version: str | None = opts["benchmark_version"]
        activate: bool = opts["activate"]

        fixture_path = self._resolve_fixture_path(fixture_arg)

        try:
            payload = load_yaml(fixture_path)
        except BenchmarkLoaderError as exc:
            raise CommandError(str(exc)) from exc

        if expected_version is not None and payload.version != expected_version:
            raise CommandError(
                f"{fixture_path}: fixture version is '{payload.version}' but --benchmark-version "
                f"is '{expected_version}'. Pass the matching --benchmark-version or load the "
                "correct YAML file."
            )

        version_obj, created_count, updated_count = upsert_benchmarks(
            payload, activate=activate
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {len(payload.entries)} benchmarks into BenchmarkVersion "
                f"{payload.version} (created={created_count}, updated={updated_count})"
            )
        )
        if activate:
            self.stdout.write(
                self.style.SUCCESS(f"activated: BenchmarkVersion {version_obj.version}")
            )

    def _resolve_fixture_path(self, fixture_arg: str | None) -> Path:
        if fixture_arg:
            return Path(fixture_arg).expanduser().resolve()
        return (Path(settings.BASE_DIR) / DEFAULT_FIXTURE).resolve()
