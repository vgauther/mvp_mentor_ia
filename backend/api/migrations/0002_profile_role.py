from django.db import migrations, models


def promote_first_profile(apps, schema_editor):
    profile_model = apps.get_model("api", "Profile")
    first_profile = profile_model.objects.order_by("id").first()

    if first_profile:
        first_profile.role = "admin"
        first_profile.save(update_fields=["role"])


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Administrateur"),
                    ("learner", "Apprenant"),
                ],
                db_index=True,
                default="learner",
                max_length=10,
            ),
        ),
        migrations.RunPython(
            promote_first_profile,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
