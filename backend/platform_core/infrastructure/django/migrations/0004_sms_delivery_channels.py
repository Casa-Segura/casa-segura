from django.db import migrations, models
from django.db.models import Q


def forwards(apps, schema_editor):
    ContractAnalysis = apps.get_model("platform_core", "ContractAnalysis")
    ContractAnalysis.objects.filter(delivery_status="sent_whatsapp").update(
        delivery_status="sent_sms",
    )
    ContractAnalysis.objects.filter(delivery_channel="whatsapp_summary").update(
        delivery_channel="sms_summary",
    )


def backwards(apps, schema_editor):
    ContractAnalysis = apps.get_model("platform_core", "ContractAnalysis")
    ContractAnalysis.objects.filter(delivery_status="sent_sms").update(
        delivery_status="sent_whatsapp",
    )
    ContractAnalysis.objects.filter(delivery_channel="sms_summary").update(
        delivery_channel="whatsapp_summary",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("platform_core", "0003_fix_immutability_function"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="contractanalysis",
            name="ck_contract_analysis_delivery_status_enum",
        ),
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="contractanalysis",
            name="delivery_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pendiente"),
                    ("queued", "Encolada"),
                    ("sent_sms", "Enviado por SMS"),
                    ("sent_email", "Enviado por email"),
                    ("available_link", "Disponible vía enlace"),
                    ("expired", "Expirada"),
                    ("failed", "Fallida"),
                ],
                default="pending",
                help_text="Report delivery state (canonical per PRD_F8 §5.1)",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="contractanalysis",
            name="delivery_channel",
            field=models.CharField(
                blank=True,
                choices=[
                    ("sms_summary", "Resumen por SMS"),
                    ("email_pdf", "PDF por email"),
                    ("web_link", "Enlace web"),
                ],
                help_text="Channel chosen by the user",
                max_length=24,
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="contractanalysis",
            constraint=models.CheckConstraint(
                condition=Q(
                    delivery_status__in=[
                        "pending",
                        "queued",
                        "sent_sms",
                        "sent_email",
                        "available_link",
                        "expired",
                        "failed",
                    ],
                ),
                name="ck_contract_analysis_delivery_status_enum",
            ),
        ),
    ]
