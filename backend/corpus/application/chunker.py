"""Markdown chunker (CS-081).

Splits a `ParsedLaw.body` into article-sized chunks suitable for
embedding. The corpus is authored as Markdown with `### Art. N — title`
headers, so the chunker:

  1. Walks the body line-by-line and starts a new chunk whenever it hits
     a `### Art. N` heading (case- and accent-insensitive).
  2. Captures heading content up to but not including the next `###`.
  3. If a single article exceeds `CHUNK_CHAR_BOUNDARY` chars, splits on
     paragraph boundaries (`\n\n`) into sub-chunks tagged with a numeric
     suffix on the anchor.
  4. Skips stub laws (`is_stub == True`) — we want to record the
     `LegalDocument` row but not pollute embeddings.

Each chunk gets a slugified anchor (`art-4`, `art-12-b`) so frontend deep
links remain stable across re-ingestions of the same corpus version.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from corpus.application.loader import ParsedLaw
from corpus.application.tags import normalize_tag

CHUNK_CHAR_BOUNDARY = 1500

_ARTICLE_HEADING_RE = re.compile(
    r"^###\s*Art\.?\s*(?P<num>[\d]+[a-zA-Z\-]*)\s*(?:[—-]\s*(?P<title>.+))?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LegalChunkDraft:
    """In-memory representation of a chunk before it hits Django ORM."""

    law_id: str
    article_number: str
    anchor: str
    text_paraphrased: str
    text_verbatim: str
    tags: list[str]
    relevance_for_findings: list[str]


def chunk_law(law: ParsedLaw) -> list[LegalChunkDraft]:
    """Return chunks for a single law. Empty list for stub laws."""

    if law.is_stub or not law.body:
        return []

    articles = list(_iter_articles(law.body))
    drafts: list[LegalChunkDraft] = []
    base_tags = _law_level_tags(law)

    for article in articles:
        sub_chunks = _split_long_article(article.body, CHUNK_CHAR_BOUNDARY)
        for idx, segment in enumerate(sub_chunks):
            anchor_suffix = "" if len(sub_chunks) == 1 else f"-p{idx + 1}"
            anchor = f"art-{normalize_tag(article.number)}{anchor_suffix}"
            drafts.append(
                LegalChunkDraft(
                    law_id=law.law_id,
                    article_number=f"Art. {article.number}",
                    anchor=anchor,
                    text_paraphrased=segment.strip(),
                    text_verbatim=segment.strip(),
                    tags=base_tags,
                    relevance_for_findings=[],
                )
            )
    return drafts


# ─── internals ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Article:
    number: str
    title: str
    body: str


def _iter_articles(body: str):
    current_num: str | None = None
    current_title: str = ""
    buffer: list[str] = []

    for line in body.splitlines():
        match = _ARTICLE_HEADING_RE.match(line.strip())
        if match:
            if current_num is not None:
                yield _Article(
                    number=current_num,
                    title=current_title,
                    body="\n".join(buffer).strip(),
                )
            current_num = match.group("num").strip()
            current_title = (match.group("title") or "").strip()
            buffer = [line]
            continue
        if current_num is not None:
            buffer.append(line)

    if current_num is not None:
        yield _Article(
            number=current_num,
            title=current_title,
            body="\n".join(buffer).strip(),
        )


def _split_long_article(text: str, boundary: int) -> list[str]:
    if len(text) <= boundary:
        return [text]

    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) > boundary and current:
            chunks.append(current)
            current = para
        else:
            current = candidate
    if current:
        chunks.append(current)

    # If even paragraph-splitting kept a chunk over `boundary` (very long
    # single paragraph), fall back to hard slicing.
    fixed: list[str] = []
    for chunk in chunks:
        if len(chunk) <= boundary:
            fixed.append(chunk)
            continue
        for start in range(0, len(chunk), boundary):
            fixed.append(chunk[start : start + boundary])
    return fixed


def _law_level_tags(law: ParsedLaw) -> list[str]:
    """Compute base tags from the law's frontmatter `covers` list + subject."""

    raw = list(law.raw_frontmatter.get("covers") or [])
    if law.subject:
        raw.append(law.subject)
    return [normalize_tag(item) for item in raw if normalize_tag(item)]
