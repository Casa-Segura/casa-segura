"""Markdown corpus loader (CS-080).

Walks `docs/RAG Legal context/` looking for `NN-<slug>.md` files. Each file
must carry YAML frontmatter naming the law and its metadata; the body is
kept verbatim for downstream chunking (CS-081).

Stub files (frontmatter `estado: pendiente_de_descarga`) are loaded as
empty `LegalDocument` rows with `status=IN_FORCE` so downstream code
doesn't blow up, and they're flagged so the chunker can skip them.

Public entry: `load_corpus_markdown(root: Path) -> list[ParsedLaw]`.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
_FILENAME_RE = re.compile(r"^(\d{2})-(.+)\.md$")


@dataclass(frozen=True)
class ParsedLaw:
    """Result of parsing one markdown corpus file."""

    law_id: str
    title: str
    short_title: str
    decree: str
    issued_at: date | None
    official_gazette: str
    last_verified: date | None
    source_url: str
    subject: str
    status: str
    body: str
    content_hash: str
    is_stub: bool
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)


def load_corpus_markdown(root: Path) -> list[ParsedLaw]:
    """Discover + parse all `NN-*.md` files under `root`. Ignores READMEs."""

    results: list[ParsedLaw] = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or not path.suffix == ".md":
            continue
        if not _FILENAME_RE.match(path.name):
            # README, ARCHITECTURE-* etc. are excluded by convention.
            continue
        results.append(_parse_file(path))
    return results


def _parse_file(path: Path) -> ParsedLaw:
    raw = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        raise ValueError(f"missing YAML frontmatter in {path.name}")

    frontmatter = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()
    if not isinstance(frontmatter, dict):
        raise ValueError(f"frontmatter in {path.name} is not a mapping")

    law_id = str(frontmatter.get("law_id") or "").strip()
    if not law_id:
        raise ValueError(f"frontmatter in {path.name} missing law_id")

    estado = str(frontmatter.get("estado") or "vigente").strip().lower()
    is_stub = estado == "pendiente_de_descarga"

    content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    return ParsedLaw(
        law_id=law_id,
        title=str(frontmatter.get("title") or law_id),
        short_title=str(frontmatter.get("short_title") or ""),
        decree=str(frontmatter.get("decreto") or ""),
        issued_at=_coerce_date(frontmatter.get("fecha_emision")),
        official_gazette=str(frontmatter.get("diario_oficial") or ""),
        last_verified=_coerce_date(frontmatter.get("last_verified")),
        source_url=str(frontmatter.get("source_url") or ""),
        subject=str(frontmatter.get("materia") or ""),
        status=_map_status(estado),
        body=body,
        content_hash=content_hash,
        is_stub=is_stub,
        raw_frontmatter=frontmatter,
    )


def _coerce_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        logger.info("corpus.loader.unparseable_date", value=value)
        return None


def _map_status(estado: str) -> str:
    """Map the Spanish corpus `estado` field to the LegalDocumentStatus enum."""

    estado = estado.strip().lower()
    if "derogad" in estado:
        return "repealed"
    if "reforma" in estado:
        return "in_force_with_amendments"
    return "in_force"


def laws_summary(parsed: Iterable[ParsedLaw]) -> dict[str, Any]:
    """Build a JSON-serialisable summary suitable for `CorpusVersion.manifest`."""

    payload = []
    for law in parsed:
        payload.append(
            {
                "law_id": law.law_id,
                "title": law.title,
                "is_stub": law.is_stub,
                "content_hash": law.content_hash,
                "source_url": law.source_url,
            }
        )
    return {"laws": payload}
