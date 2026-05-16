"""Ingestion-local enums (ContractSubmission, OcrJob)."""

from __future__ import annotations

from django.db import models


class FileFormat(models.TextChoices):
    """Accepted upload formats per DOMAIN_MODEL §4.1."""

    PDF = "pdf", "PDF"
    JPG = "jpg", "JPG"
    JPEG = "jpeg", "JPEG"
    PNG = "png", "PNG"
    HEIC = "heic", "HEIC"
    WEBP = "webp", "WebP"


class ProcessingStatus(models.TextChoices):
    """ContractSubmission lifecycle. See DOMAIN_MODEL §4.1."""

    RECEIVED = "received", "Recibido"
    EXTRACTING = "extracting", "Extrayendo texto"
    EXTRACTED = "extracted", "Texto extraído"
    CLASSIFYING = "classifying", "Clasificando"
    ANALYZING = "analyzing", "Analizando"
    COMPLETED = "completed", "Completado"
    FAILED_EXTRACTION = "failed_extraction", "Falló extracción"
    FAILED_CLASSIFICATION = "failed_classification", "Falló clasificación"
    FAILED_ANALYSIS = "failed_analysis", "Falló análisis"
    REJECTED_LANGUAGE = "rejected_language", "Rechazado por idioma"
    REJECTED_TYPE = "rejected_type", "Rechazado por tipo de contrato"
    REJECTED_SIZE = "rejected_size", "Rechazado por tamaño"
    EXPIRED = "expired", "Expirado"


class ExtractionStrategy(models.TextChoices):
    """OCR extraction strategies. See DOMAIN_MODEL §6.5 (stored lowercase per CS-025)."""

    PYPDF = "pypdf", "pypdf (PDF con texto extraíble)"
    VISION_LLM = "vision_llm", "Vision LLM (OpenRouter)"
    TESSERACT = "tesseract", "Tesseract local (fallback)"


class OcrJobStatus(models.TextChoices):
    """OcrJob lifecycle. PRD DDL set is canonical (per CS-025 notes):
    DOMAIN_MODEL lists `running|success|failed|timeout`, PRD/F1 add `cancelled` and drop `running`.

    We adopt the PRD set (success|failed|timeout|cancelled) plus a `running` marker for
    in-flight jobs needed by the orchestrator. Document at API boundary."""

    RUNNING = "running", "En ejecución"
    SUCCESS = "success", "Éxito"
    FAILED = "failed", "Fallido"
    TIMEOUT = "timeout", "Timeout"
    CANCELLED = "cancelled", "Cancelado"


class SubmissionSource(models.TextChoices):
    """Where the submission came in from."""

    WEB = "web", "Web"


class DisclaimerAcceptanceMethod(models.TextChoices):
    """How the user acknowledged the disclaimer before submission."""

    CHECKBOX = "checkbox", "Checkbox en UI"
