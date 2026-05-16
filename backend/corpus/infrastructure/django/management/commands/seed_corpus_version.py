"""CS-034: idempotent seed for a placeholder CorpusVersion.

Inserts a placeholder corpus row (date-stamped or user-provided version
string) so ContractAnalysis FK inserts don't fail before the legal corpus
is actually ingested. Once the F3 ingestion pipeline lands, the real
corpus_version replaces this one (new INSERT, never UPDATE — catalog
trigger forbids drift).

Usage:
    python manage.py seed_corpus_version
    python manage.py seed_corpus_version --catalog-version 2026-05-15
    python manage.py seed_corpus_version --activate
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from corpus.infrastructure.django.models import CorpusVersion


class Command(BaseCommand):
    help = "Idempotently seed a placeholder CorpusVersion row."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--catalog-version",
            default=None,
            dest="catalog_version",
            help="Version string (default: today's UTC date in YYYY-MM-DD).",
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            help="After ensuring the row exists, set is_active=true (deactivates any other).",
        )

    def handle(self, *args, **opts) -> None:
        version: str = opts["catalog_version"] or timezone.now().date().isoformat()
        activate: bool = opts["activate"]

        with transaction.atomic():
            obj, created = CorpusVersion.objects.get_or_create(
                version=version,
                defaults={
                    "released_at": timezone.now(),
                    "laws_count": 0,
                    "articles_count": 0,
                    "chunks_count": 0,
                    "manifest": {"laws": [], "placeholder": True},
                    "changelog": "Placeholder corpus version (no laws ingested yet).",
                    "is_active": False,
                },
            )
            self.stdout.write(
                self.style.SUCCESS(f"{'created' if created else 'exists'}: CorpusVersion {obj.version}")
            )

            if activate:
                CorpusVersion.objects.exclude(version=version).filter(is_active=True).update(is_active=False)
                if not obj.is_active:
                    obj.is_active = True
                    obj.save(update_fields=["is_active", "updated_at"])
                self.stdout.write(self.style.SUCCESS(f"activated: CorpusVersion {obj.version}"))
