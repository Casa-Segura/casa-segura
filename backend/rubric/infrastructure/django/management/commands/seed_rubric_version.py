"""CS-033: idempotent seed for the bootstrap RubricVersion (1.0.0).

Inserts version `1.0.0` if missing and (optionally) marks it active.
Re-runs are safe: existing rows are left alone (the catalog is immutable
by trigger; this command never UPDATEs published rows beyond `is_active`).

Usage:
    python manage.py seed_rubric_version
    python manage.py seed_rubric_version --activate
    python manage.py seed_rubric_version --catalog-version 1.0.0 --activate

The criterion catalog itself (38 rows) is left to a follow-up command
that loads from the canonical YAML in docs/Casa Segura Formal PRDs/
RUBRICA_CONTRATO.md once the YAML extraction is in place; today this
command guarantees the *version row* exists so ContractAnalysis FK
inserts don't fail.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from rubric.infrastructure.django.models import RubricVersion

DEFAULT_VERSION = "1.0.0"
DEFAULT_CATEGORIES = {
    "A": {"name": "Legalidad básica", "weight": 0.15},
    "B": {"name": "Salud económica", "weight": 0.20},
    "C": {"name": "Estructura del contrato", "weight": 0.15},
    "D": {"name": "Garantías y saneamiento", "weight": 0.15},
    "E": {"name": "Cláusulas abusivas y derechos", "weight": 0.20},
    "F": {"name": "Cumplimiento específico por tipo", "weight": 0.15},
}
DEFAULT_PATH = "rubric/data/rubric_1_0_0.yaml"


class Command(BaseCommand):
    help = "Idempotently seed the bootstrap RubricVersion row."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--catalog-version", default=DEFAULT_VERSION, dest="catalog_version")
        parser.add_argument("--criteria-count", type=int, default=38, dest="criteria_count")
        parser.add_argument(
            "--activate",
            action="store_true",
            help="After ensuring the row exists, set is_active=true (deactivates any other).",
        )

    def handle(self, *args, **opts) -> None:
        version: str = opts["catalog_version"]
        criteria_count: int = opts["criteria_count"]
        activate: bool = opts["activate"]

        with transaction.atomic():
            obj, created = RubricVersion.objects.get_or_create(
                version=version,
                defaults={
                    "released_at": timezone.now(),
                    "criteria_count": criteria_count,
                    "categories": DEFAULT_CATEGORIES,
                    "criteria_definitions_path": DEFAULT_PATH,
                    "changelog": "Bootstrap rubric version (placeholder until YAML loader lands).",
                    "is_active": False,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"{'created' if created else 'exists'}: RubricVersion {obj.version}"))

            if activate:
                # is_active is the only field allowed to flip post-publish.
                # Deactivate all others first to honor the singleton constraint.
                RubricVersion.objects.exclude(version=version).filter(is_active=True).update(is_active=False)
                if not obj.is_active:
                    obj.is_active = True
                    obj.save(update_fields=["is_active", "updated_at"])
                self.stdout.write(self.style.SUCCESS(f"activated: RubricVersion {obj.version}"))
