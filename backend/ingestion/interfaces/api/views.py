"""Submissions API (CS-050 + CS-051 + CS-059)."""

from __future__ import annotations

import sys

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.utils import timezone


def _web_banner(message: str, **fields) -> None:
    extras = "  ".join(f"{k}={v}" for k, v in fields.items() if v is not None)
    line = f"  [WEB]    {message:<32}  {extras}".rstrip()
    print(line, file=sys.stdout, flush=True)

from ingestion.application.ocr.errors import NotAnalyzableError, NotAnalyzableReason
from ingestion.application.post_ocr_pipeline import schedule_post_ocr_pipeline
from ingestion.application.upload_service import (
    FileUpload,
    UploadRequest,
    ingest_upload,
)
from ingestion.domain.enums import (
    DisclaimerAcceptanceMethod,
    ExtractionStrategy,
    ProcessingStatus,
    SubmissionSource,
)
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
        _web_banner(
            "POST /api/v1/submissions/",
            content_type=request.content_type,
            field_keys=list(request.data.keys()),
            file_keys=list(request.FILES.keys()),
        )
        merged = merge_submission_upload_aliases(request.data)
        require_disclaimer_accepted_or_raise(merged)

        # Multi-file shape: prefer `files[]` over the legacy single `file`
        # field. Both are validated through the same SubmissionUploadSerializer.
        files_list = request.FILES.getlist("files") or ([request.FILES["file"]] if "file" in request.FILES else [])

        serializer = SubmissionUploadSerializer(data=merged, context={"file_count": len(files_list)})
        serializer.is_valid(raise_exception=True)

        if not files_list:
            return Response(
                {
                    "error": "validation_error",
                    "error_code": "FILE_REQUIRED",
                    "detail": "at least one file must be supplied (file= or files=)",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploads: list[FileUpload] = []
        for upload in files_list:
            uploads.append(
                FileUpload(
                    file_bytes=upload.read(),
                    filename=upload.name or "",
                    content_type=(upload.content_type or "").lower(),
                )
            )

        disclaimer_at = timezone.now()
        disclaimer_method = DisclaimerAcceptanceMethod(serializer.validated_data["disclaimer_method"])
        source = SubmissionSource(serializer.validated_data["source"])

        forced = request.headers.get("X-Force-Strategy")
        force_strategy: ExtractionStrategy | None = None
        if forced:
            try:
                force_strategy = ExtractionStrategy(forced.strip().lower())
            except ValueError:
                allowed = sorted(s.value for s in ExtractionStrategy)
                return Response(
                    {
                        "error": "validation_error",
                        "error_code": "INVALID_FORCE_STRATEGY",
                        "detail": (
                            f"X-Force-Strategy={forced!r} is not a valid extraction strategy. Allowed: {allowed}."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        req = UploadRequest(
            files=tuple(uploads),
            disclaimer_accepted_at=disclaimer_at,
            disclaimer_method=disclaimer_method,
            source=source,
            force_strategy=force_strategy,
        )

        try:
            outcome = ingest_upload(req)
        except NotAnalyzableError as exc:
            _web_banner("400 NotAnalyzable", code=exc.reason.value, msg=exc.message[:160])
            return Response(
                {
                    "error": "not_analyzable",
                    "error_code": exc.reason.value,
                    "detail": exc.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        sub = outcome.submission
        _web_banner(
            "ingest outcome",
            submission_id=str(sub.id)[:8],
            created=outcome.created,
            status=sub.processing_status,
            error_code=sub.error_code,
        )

        # PRD §7.4 — Spanish-only policy returns HTTP 422 LANGUAGE_NOT_SUPPORTED
        # when the language gate rejects the submission, even though the OCR
        # path completed end-to-end. TEXT_TOO_SHORT (CS-053) lands here too.
        if sub.processing_status == ProcessingStatus.REJECTED_LANGUAGE.value:
            return Response(
                {
                    "error": "not_analyzable",
                    "error_code": "LANGUAGE_NOT_SUPPORTED",
                    "detail": sub.error_reason or "non-spanish content detected",
                    "submission_id": str(sub.id),
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if sub.error_code == NotAnalyzableReason.TEXT_TOO_SHORT.value:
            return Response(
                {
                    "error": "not_analyzable",
                    "error_code": "TEXT_TOO_SHORT",
                    "detail": sub.error_reason or "extracted text below minimum threshold",
                    "submission_id": str(sub.id),
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        handoff = outcome.extracted_text_handoff
        if (
            handoff
            and sub.processing_status == ProcessingStatus.EXTRACTED.value
            and sub.analysis_id is None
        ):
            schedule_post_ocr_pipeline(
                submission_id=str(sub.id),
                extracted_text=handoff,
                delivery_channel=serializer.validated_data["delivery_channel"],
                delivery_target=serializer.validated_data.get("delivery_target"),
            )
            sub.refresh_from_db(fields=["processing_status", "analysis_id"])

        body = SubmissionResponseSerializer(sub).data
        http_status = status.HTTP_201_CREATED if outcome.created else status.HTTP_200_OK
        return Response(body, status=http_status)


class SubmissionDetailView(APIView):
    """`GET /api/v1/submissions/<id>/` — read submission status."""

    permission_classes = (AllowAny,)

    def get(self, request, submission_id):
        try:
            submission = ContractSubmission.objects.select_related("analysis").get(pk=submission_id)
        except ContractSubmission.DoesNotExist:
            return Response(
                {"error": "not_found", "detail": "submission_id unknown"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(SubmissionResponseSerializer(submission).data)
