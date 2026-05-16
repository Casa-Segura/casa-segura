"""Corpus retrieval API (CS-085 + CS-086)."""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from corpus.application.retrieval import LegalCitationService


class RetrieveRequestSerializer(serializers.Serializer):
    finding = serializers.CharField(allow_blank=False, max_length=2000)
    finding_pattern = serializers.CharField(required=False, allow_blank=True, max_length=128)
    threshold = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=50)


class RetrieveLegalBasisView(APIView):
    """`POST /api/v1/corpus/retrieve/` — return citations for a finding."""

    permission_classes = (AllowAny,)

    def post(self, request) -> Response:
        serializer = RetrieveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = LegalCitationService()
        citations = service.retrieve_legal_basis(
            finding=serializer.validated_data["finding"],
            finding_pattern=serializer.validated_data.get("finding_pattern") or None,
            threshold=serializer.validated_data.get("threshold"),
            top_k=serializer.validated_data.get("top_k"),
        )

        return Response(
            {
                "corpus_version": (service.corpus_version.version if service.corpus_version else None),
                "citations": [
                    {
                        "chunk_id": c.chunk_id,
                        "law_id": c.law_id,
                        "article_number": c.article_number,
                        "anchor": c.anchor,
                        "text_paraphrased": c.text_paraphrased,
                        "similarity": round(c.similarity, 4),
                        "source": c.source,
                    }
                    for c in citations
                ],
            },
            status=status.HTTP_200_OK,
        )
