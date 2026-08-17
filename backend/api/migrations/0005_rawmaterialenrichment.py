from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0004_rawmaterial_quiz_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="RawMaterialEnrichment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "À enrichir"), ("queued", "En attente"), ("processing", "En cours"), ("ready", "Prête"), ("error", "Erreur")], db_index=True, default="pending", max_length=20)),
                ("progress_message", models.CharField(blank=True, max_length=255)),
                ("transcript", models.TextField(blank=True)),
                ("extracted_text", models.TextField(blank=True)),
                ("media_purpose", models.TextField(blank=True)),
                ("summary", models.TextField(blank=True)),
                ("language", models.CharField(blank=True, max_length=20)),
                ("key_concepts", models.JSONField(blank=True, default=list)),
                ("glossary", models.JSONField(blank=True, default=list)),
                ("keywords", models.JSONField(blank=True, default=list)),
                ("ai_model", models.CharField(blank=True, max_length=100)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("generated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("material", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="enrichment", to="api.rawmaterial")),
            ],
        ),
    ]
