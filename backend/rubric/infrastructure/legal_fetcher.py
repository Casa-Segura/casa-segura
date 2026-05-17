"""Adapter that wires ``corpus.LegalCitationService`` into the rubric.

``rubric.application.services.finding_factory.LegalCitationFetcher`` is
a narrow protocol on purpose — tests inject a stub. The production
adapter here converts the corpus ``LegalCitation`` dataclasses into
``LegalReference`` Pydantic models the rubric persists inside each
``Finding``.

Lookup order:
1. If ``prefer_anchors`` is non-empty, query F3 with
   ``finding_pattern=<first-anchor>`` so CS-086's pattern table can
   short-circuit the embedding call.
2. Otherwise fall back to the semantic search by ``finding_text``.
"""

from __future__ import annotations

from corpus.application.retrieval import LegalCitationService
from rubric.domain.entities import LegalReference


class CorpusLegalFetcher:
    """Production fetcher backed by ``LegalCitationService`` (CS-085/CS-086)."""

    def __init__(self, service: LegalCitationService | None = None) -> None:
        self._service = service or LegalCitationService()

    def retrieve(
        self,
        *,
        finding_text: str,
        prefer_anchors: tuple[str, ...] = (),
        top_k: int = 3,
    ) -> list[LegalReference]:
        pattern = prefer_anchors[0] if prefer_anchors else None
        citations = self._service.retrieve_legal_basis(
            finding=finding_text,
            finding_pattern=pattern,
            top_k=top_k,
        )
        if not citations and prefer_anchors:
            # If the pattern hit failed, retry without it so the semantic
            # search still has a chance to surface something for the
            # report (PRD_F3 US-03 fallback path).
            citations = self._service.retrieve_legal_basis(
                finding=finding_text,
                finding_pattern=None,
                top_k=top_k,
            )

        return [self._to_reference(c) for c in citations[:top_k]]

    def _to_reference(self, citation) -> LegalReference:
        return LegalReference(
            law_id=citation.law_id,
            law_title=citation.law_id.replace("-", " ").title(),
            article=citation.article_number,
            anchor=citation.anchor,
            paraphrased_quote=citation.text_paraphrased,
            corpus_version=(
                self._service.corpus_version.version if self._service.corpus_version is not None else None
            ),
        )


__all__ = ["CorpusLegalFetcher"]
