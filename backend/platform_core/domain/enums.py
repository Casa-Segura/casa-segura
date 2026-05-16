"""Cross-feature domain enums. Centralized in platform_core because ContractAnalysis
(owned by platform_core) is the central entity that references all of them.

Modules that own narrower enums keep them locally (e.g. ingestion.ProcessingStatus)."""

from __future__ import annotations

from django.db import models


class ContractType(models.TextChoices):
    """Contract types covered by Casa Segura. See DOMAIN_MODEL §6.1."""

    CVC = "CVC", "Compraventa al contado"
    CVP = "CVP", "Compraventa a plazos"
    ARV = "ARV", "Arrendamiento de vivienda"
    ARC = "ARC", "Arrendamiento de local comercial"
    APV = "APV", "Arrendamiento con promesa de venta"
    LEA = "LEA", "Arrendamiento financiero / leasing"
    IVU = "IVU", "Contrato institucional IVU"
    FSV = "FSV", "Compra o préstamo financiado por FSV"
    NOT_CLASSIFIABLE = "NOT_CLASSIFIABLE", "No clasificable"


class Band(models.TextChoices):
    """Overall score band. See DOMAIN_MODEL §6.2."""

    GREEN = "green", "Verde (8.0 - 10.0)"
    YELLOW = "yellow", "Amarillo (5.0 - 7.9)"
    RED = "red", "Rojo (0 - 4.9)"
    NOT_ANALYZABLE = "not_analyzable", "No analizable"


class Severity(models.TextChoices):
    """Finding severity. See DOMAIN_MODEL §6.3."""

    CRITICAL = "critical", "Crítica"
    RED = "red", "Roja"
    YELLOW = "yellow", "Amarilla"
    GREEN = "green", "Verde"
    UNVERIFIABLE = "unverifiable", "No verificable"


class DeliveryChannel(models.TextChoices):
    """Channels through which the report is delivered to the user.

    See DOMAIN_MODEL §6.4. Stored lowercase per F8/CS-029 (lowercase at DB,
    uppercase mapping done at API boundary if needed)."""

    EMAIL_PDF = "email_pdf", "PDF por email"
    WHATSAPP_SUMMARY = "whatsapp_summary", "Resumen por WhatsApp"
    WEB_LINK = "web_link", "Enlace web"


class DeliveryStatus(models.TextChoices):
    """Delivery state on ContractAnalysis (different from DeliveryRequest.status).

    Canonical set per PRD_F8 §5.1 (supersedes RUBRICA_CONTRATO.md §12.2)."""

    PENDING = "pending", "Pendiente"
    QUEUED = "queued", "Encolada"
    SENT_EMAIL = "sent_email", "Enviado por email"
    SENT_WHATSAPP = "sent_whatsapp", "Enviado por WhatsApp"
    AVAILABLE_LINK = "available_link", "Disponible vía enlace"
    EXPIRED = "expired", "Expirada"
    FAILED = "failed", "Fallida"


class OverrideCode(models.TextChoices):
    """The 11 critical overrides defined by RUBRICA_CONTRATO §11. See DOMAIN_MODEL §6.6."""

    ART_1605_CC = "art_1605_cc", "Venta de inmueble sin escritura pública (Art. 1605 CC)"
    ART_1613_CC = "art_1613_cc", "Precio al arbitrio de una parte (Art. 1613 CC)"
    ART_1644_CC = "art_1644_cc", "Renuncia de mala fe a saneamiento (Art. 1644 CC)"
    ART_1425_CC = "art_1425_cc", "Promesa sin plazo definido (Art. 1425 CC)"
    ART_3_IVU_FAMILY_HOMESTEAD = "art_3_ivu_family_homestead", "Intento de transferir bajo Bien de Familia"
    ART_5_LPC_NON_WAIVABLE = "art_5_lpc_non_waivable", "Renuncia a derechos irrenunciables (Art. 5 LPC)"
    ART_12_LPC = "art_12_lpc", "Interés moratorio sobre saldo total (Art. 12 LPC)"
    ART_13_LPC = "art_13_lpc", "Modificación unilateral (Art. 13 LPC)"
    ART_18_LPC_BLANK_SIGNATURE = "art_18_lpc_blank_signature", "Firma en blanco (Art. 18 LPC)"
    ART_17H_LPC_ARBITRATION = "art_17h_lpc_arbitration", "Arbitraje impuesto en adhesión (Art. 17H LPC)"
    ART_58_FSV = "art_58_fsv", "Anotación FSV no divulgada (Art. 58 FSV)"


class PrivacyAuditEvent(models.TextChoices):
    """Event types recorded in the PrivacyAuditLog (F8 operational table)."""

    ANALYSIS_ANONYMIZED = "analysis_anonymized", "Análisis anonimizado"
    DELIVERY_TARGET_PURGED = "delivery_target_purged", "Destino de entrega purgado"
    SUBMISSION_PURGED = "submission_purged", "Submission transitoria purgada"
    OCR_JOB_PURGED = "ocr_job_purged", "OCR job purgado"
    DELIVERY_REQUEST_PURGED = "delivery_request_purged", "DeliveryRequest purgado"
    LINK_EXPIRED = "link_expired", "Enlace público expirado"
    RESEND_REQUESTED = "resend_requested", "Reenvío solicitado por usuario"


class JobExecutionStatus(models.TextChoices):
    """Status for the JobExecutionLog (Celery beat / retention jobs)."""

    STARTED = "started", "Iniciado"
    SUCCESS = "success", "Éxito"
    PARTIAL = "partial", "Parcial"
    FAILED = "failed", "Fallido"
