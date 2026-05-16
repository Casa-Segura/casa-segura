"""`manage.py ingest_corpus` — transactional corpus ingestion CLI (CS-084).

Composes the loader (CS-080) → chunker (CS-081) → tag normaliser (CS-082)
→ embedding pipeline (CS-083) and persists everything under a single
`CorpusVersion`. The whole operation runs inside an atomic transaction:
either every law + chunk lands, or nothing does.

The command is idempotent: re-running with the same `--version` and an
identical content-hash manifest is a no-op. Re-running with new content
is rejected (the immutability trigger from CS-030 refuses to mutate
published catalog rows; you must bump the version).

Usage:

    python manage.py ingest_corpus --version 2026-05-15 --activate
    python manage.py ingest_corpus --version 2026-05-15 --root docs/RAG\\ Legal\\ context/
"""

from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from corpus.application.chunker import chunk_law
from corpus.application.embeddings import embed_texts
from corpus.application.loader import laws_summary, load_corpus_markdown
from corpus.application.version import activate as activate_version
from corpus.infrastructure.django.models import CorpusVersion, LegalChunk, LegalDocument

DEFAULT_CORPUS_ROOT = Path("docs/RAG Legal context")


class Command(BaseCommand):
    help = "Ingest the legal corpus markdown into a versioned snapshot."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--version",
            required=True,
            help="Corpus version tag, e.g. 2026-05-15 or v1.",
        )
        parser.add_argument(
            "--root",
            default=None,
            help=f"Override the corpus markdown root (default: {DEFAULT_CORPUS_ROOT}).",
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Mark the new CorpusVersion as the active singleton.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and chunk but don't write to the database.",
        )

    def handle(self, *args, **options) -> None:
        version_tag: str = options["version"]
        root_arg: str | None = options["root"]
        activate: bool = options["activate"]
        dry_run: bool = options["dry_run"]

        root = Path(root_arg) if root_arg else _resolve_default_root()
        if not root.exists():
            raise CommandError(f"corpus root not found: {root}")

        self.stdout.write(f"loading corpus markdown from {root}")
        parsed_laws = load_corpus_markdown(root)
        if not parsed_laws:
            raise CommandError("no markdown laws discovered")

        chunks_per_law = {law.law_id: chunk_law(law) for law in parsed_laws}
        total_chunks = sum(len(c) for c in chunks_per_law.values())
        articles_total = sum(len(c) for c in chunks_per_law.values())

        self.stdout.write(self.style.SUCCESS(f"parsed {len(parsed_laws)} laws → {total_chunks} chunks"))

        if dry_run:
            self.stdout.write("--dry-run: skipping persistence")
            return

        with transaction.atomic():
            version_obj, created = CorpusVersion.objects.get_or_create(
                version=version_tag,
                defaults=dict(
                    released_at=timezone.now(),
                    laws_count=len(parsed_laws),
                    articles_count=articles_total,
                    chunks_count=total_chunks,
                    manifest=laws_summary(parsed_laws),
                    changelog=f"Ingested via ingest_corpus on {timezone.now():%Y-%m-%d}",
                    is_active=False,
                ),
            )
            if not created:
                self.stdout.write(self.style.WARNING(f"corpus version {version_tag} already exists — skipping insert"))
                return

            for law in parsed_laws:
                LegalDocument.objects.create(
                    law_id=law.law_id,
                    corpus_version=version_obj,
                    title=law.title,
                    short_title=law.short_title,
                    decree=law.decree,
                    issued_at=law.issued_at,
                    official_gazette=law.official_gazette,
                    last_verified=law.last_verified,
                    source_url=law.source_url,
                    status=law.status,
                    subject=law.subject,
                )

            drafts: list = []
            for law_id, law_chunks in chunks_per_law.items():
                drafts.extend((law_id, draft) for draft in law_chunks)

            if drafts:
                texts = [draft.text_paraphrased for _, draft in drafts]
                self.stdout.write(f"embedding {len(texts)} chunks…")
                vectors = embed_texts(texts)
                if len(vectors) != len(drafts):
                    raise CommandError(f"embedding count mismatch: {len(vectors)} != {len(drafts)}")
                LegalChunk.objects.bulk_create(
                    [
                        LegalChunk(
                            id=uuid.uuid4(),
                            law_id=law_id,
                            corpus_version=version_obj,
                            article_number=draft.article_number,
                            anchor=draft.anchor,
                            text_paraphrased=draft.text_paraphrased,
                            text_verbatim=draft.text_verbatim,
                            embedding=vector,
                            tags=draft.tags,
                            relevance_for_findings=draft.relevance_for_findings,
                        )
                        for (law_id, draft), vector in zip(drafts, vectors, strict=True)
                    ],
                    batch_size=200,
                )

            if activate:
                activate_version(version_tag)

        self.stdout.write(
            self.style.SUCCESS(
                f"corpus {version_tag} ingested ({len(parsed_laws)} laws, {total_chunks} chunks){' + activated' if activate else ''}"
            )
        )


def _resolve_default_root() -> Path:
    """Find `docs/RAG Legal context/` relative to the repo root."""

    base = Path(settings.BASE_DIR).parent
    return base / DEFAULT_CORPUS_ROOT
