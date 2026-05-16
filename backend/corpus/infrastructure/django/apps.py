from django.apps import AppConfig


class CorpusConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "corpus.infrastructure.django"
    label = "corpus"
    verbose_name = "Casa Segura — Legal Corpus & RAG"
