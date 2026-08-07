from django.db import migrations, models


def remove_skipped_decisions(apps, schema_editor):
    name_decision = apps.get_model("api", "NameDecision")
    name_decision.objects.filter(choice="skipped").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0009_namesearch_filters"),
    ]

    operations = [
        migrations.RunPython(
            remove_skipped_decisions,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="namedecision",
            name="choice",
            field=models.CharField(
                choices=[
                    ("liked", "Aimé"),
                    ("rejected", "Refusé"),
                ],
                db_index=True,
                max_length=8,
            ),
        ),
    ]
