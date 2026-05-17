from django.apps import AppConfig


class FeedbackConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "feedback.infrastructure.django"
    label = "feedback"
    verbose_name = "Casa Segura — User Feedback / Error Reports"
