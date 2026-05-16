from django.apps import AppConfig


class PlatformCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "platform_core.infrastructure.django"
    label = "platform_core"
    verbose_name = "Casa Segura — Platform (shared schema)"
