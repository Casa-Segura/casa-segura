from django.db import migrations, models


def forwards(apps, schema_editor):
    ContractSubmission = apps.get_model("ingestion", "ContractSubmission")
    ContractSubmission.objects.filter(source="whatsapp").update(source="web")
    ContractSubmission.objects.filter(disclaimer_method="whatsapp_reply").update(
        disclaimer_method="checkbox",
    )


def backwards(apps, schema_editor):
    # Data cannot reliably distinguish migrated web rows from original web rows.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("ingestion", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="contractsubmission",
            name="source",
            field=models.CharField(
                choices=[("web", "Web")],
                default="web",
                help_text="Channel the submission arrived on",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="contractsubmission",
            name="disclaimer_method",
            field=models.CharField(
                choices=[("checkbox", "Checkbox en UI")],
                default="checkbox",
                help_text="How the disclaimer was accepted",
                max_length=24,
            ),
        ),
    ]
