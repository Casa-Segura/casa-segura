"""Submissions API (CS-050 + CS-051 + CS-059)."""

from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ingestion.application.ocr.errors import NotAnalyzableError
from ingestion.application.upload_service import UploadRequest, ingest_upload
from ingestion.domain.enums import DisclaimerAcceptanceMethod, SubmissionSource
from ingestion.infrastructure.django.models import ContractSubmission
from ingestion.interfaces.api.disclaimer_gate import (
    merge_submission_upload_aliases,
    require_disclaimer_accepted_or_raise,
)
from ingestion.interfaces.api.serializers import (
    SubmissionResponseSerializer,
    SubmissionUploadSerializer,
)


class SubmissionUploadView(APIView):
    """`POST /api/v1/submissions/` — accept a contract file and run OCR.

    The endpoint is idempotent: re-uploading the exact same bytes returns
    the original submission. The extracted text itself is never returned
    or persisted — only metadata (token count, language, status).
    """

    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (AllowAny,)

    def post(self, request) -> Response:
        merged = merge_submission_upload_aliases(request.data)
        require_disclaimer_accepted_or_raise(merged)

        serializer = SubmissionUploadSerializer(data=merged)
        serializer.is_valid(raise_exception=True)

        upload = serializer.validated_data["file"]
        file_bytes = upload.read()
        content_type = (upload.content_type or "").lower()
        filename = upload.name or ""

        disclaimer_at = timezone.now()
        disclaimer_method = DisclaimerAcceptanceMethod(
            serializer.validated_data["disclaimer_method"]
        )
        source = SubmissionSource(serializer.validated_data["source"])

        req = UploadRequest(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            disclaimer_accepted_at=disclaimer_at,
            disclaimer_method=disclaimer_method,
            source=source,
        )

        try:
            outcome = ingest_upload(req)
        except NotAnalyzableError as exc:
            return Response(
                {
                    "error": "not_analyzable",
                    "error_code": exc.reason.value,
                    "detail": exc.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        body = SubmissionResponseSerializer(outcome.submission).data
        http_status = status.HTTP_201_CREATED if outcome.created else status.HTTP_200_OK
        return Response(body, status=http_status)


class SubmissionDetailView(APIView):
    """`GET /api/v1/submissions/<id>/` — read submission status."""

    permission_classes = (AllowAny,)

    def get(self, request, submission_id):
        try:
            submission = ContractSubmission.objects.get(pk=submission_id)
        except ContractSubmission.DoesNotExist:
            return Response(
                {"error": "not_found", "detail": "submission_id unknown"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(SubmissionResponseSerializer(submission).data)
