"""CS-130: idempotent seed for a bootstrap BenchmarkVersion row.

Mirrors `rubric.../seed_rubric_version`: ensures a `BenchmarkVersion` row
exists so subsequent `ContractAnalysis.benchmark_version` FK inserts (and the
catalog loader) don't fail. The per-row benchmark catalog itself is loaded by
the companion `load_benchmark_catalog` command from
`backend/fixtures/economic_benchmarks_*.yaml`.

Usage:
    python manage.py seed_benchmark_version
    python manage.py seed_benchmark_version --benchmark-version 2026-Q2 --activate
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from economics.infrastructure.django.models import BenchmarkVersion

DEFAULT_VERSION = "2026-Q2"


class Command(BaseCommand):
    help = "Idempotently seed the bootstrap BenchmarkVersion row."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--benchmark-version",
            default=DEFAULT_VERSION,
            dest="benchmark_version",
            help="Version string to seed (default 2026-Q2).",
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            help="After ensuring the row exists, set is_active=True (deactivates any other).",
        )

    def handle(self, *args, **opts) -> None:
        version: str = opts["benchmark_version"]
        activate: bool = opts["activate"]

        with transaction.atomic():
            obj, created = BenchmarkVersion.objects.get_or_create(
                version=version,
                defaults={
                    "released_at": timezone.now(),
                    "changelog": "Bootstrap benchmark version (placeholder until YAML loader runs).",
                    "is_active": False,
                },
            )
            self.stdout.write(
                self.style.SUCCESS(f"{'created' if created else 'exists'}: BenchmarkVersion {obj.version}")
            )

            if activate:
                BenchmarkVersion.objects.exclude(version=version).filter(is_active=True).update(is_active=False)
                if not obj.is_active:
                    obj.is_active = True
                    obj.save(update_fields=["is_active"])
                self.stdout.write(self.style.SUCCESS(f"activated: BenchmarkVersion {obj.version}"))
