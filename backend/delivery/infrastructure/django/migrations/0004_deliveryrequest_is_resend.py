"""Add is_resend flag — CS-248."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("delivery", "0003_deliveryrequest_provider_message_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="deliveryrequest",
            name="is_resend",
            field=models.BooleanField(
                default=False,
                help_text="True when enqueued via guarded resend endpoint",
            ),
        ),
    ]
