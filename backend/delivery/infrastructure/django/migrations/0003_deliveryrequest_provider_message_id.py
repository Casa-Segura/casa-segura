"""Store Zavu (or other provider) message id for webhook correlation — CS-357."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0002_sms_channel"),
    ]

    operations = [
        migrations.AddField(
            model_name="deliveryrequest",
            name="provider_message_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=128,
                help_text="Outbound provider message id (e.g. Zavu) for delivery webhook correlation",
            ),
        ),
    ]
