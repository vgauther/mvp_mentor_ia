from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0005_rawmaterialenrichment"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseStructureGeneration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "À générer"), ("queued", "En attente"), ("processing", "En cours"), ("ready", "Proposition prête"), ("error", "Erreur")], db_index=True, default="pending", max_length=20)),
                ("progress_message", models.CharField(blank=True, max_length=255)),
                ("structure", models.JSONField(blank=True, default=dict)),
                ("ai_model", models.CharField(blank=True, max_length=100)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("generated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("training", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="structure_generation", to="api.training")),
            ],
        ),
    ]
