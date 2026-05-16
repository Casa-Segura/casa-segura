from django.db import migrations, models
from django.db.models import Q


def forwards(apps, schema_editor):
    DeliveryRequest = apps.get_model("delivery", "DeliveryRequest")
    DeliveryRequest.objects.filter(channel="whatsapp_summary").update(
        channel="sms_summary",
    )


def backwards(apps, schema_editor):
    DeliveryRequest = apps.get_model("delivery", "DeliveryRequest")
    DeliveryRequest.objects.filter(channel="sms_summary").update(
        channel="whatsapp_summary",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("delivery", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="deliveryrequest",
            name="ck_delivery_channel_enum",
        ),
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="deliveryrequest",
            name="channel",
            field=models.CharField(
                choices=[
                    ("sms_summary", "Resumen por SMS"),
                    ("email_pdf", "PDF por email"),
                    ("web_link", "Enlace web"),
                ],
                help_text="Channel chosen by the user",
                max_length=24,
            ),
        ),
        migrations.AddConstraint(
            model_name="deliveryrequest",
            constraint=models.CheckConstraint(
                condition=Q(channel__in=["sms_summary", "email_pdf", "web_link"]),
                name="ck_delivery_channel_enum",
            ),
        ),
    ]
