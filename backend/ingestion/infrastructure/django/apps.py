from django.apps import AppConfig


class IngestionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ingestion.infrastructure.django"
    label = "ingestion"
    verbose_name = "Casa Segura — Ingestion & OCR"
