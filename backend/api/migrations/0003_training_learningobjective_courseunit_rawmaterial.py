import api.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0002_profile_role"),
    ]

    operations = [
        migrations.CreateModel(
            name="Training",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("draft", "Brouillon"), ("structuring", "En structuration"), ("ready", "Prête")], db_index=True, default="draft", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_trainings", to="api.profile")),
            ],
            options={"ordering": ("-updated_at", "-id")},
        ),
        migrations.CreateModel(
            name="LearningObjective",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("position", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("training", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="objectives", to="api.training")),
            ],
            options={"ordering": ("position", "id")},
        ),
        migrations.CreateModel(
            name="CourseUnit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("module", "Module"), ("chapter", "Chapitre"), ("section", "Section")], max_length=10)),
                ("working_title", models.CharField(max_length=255)),
                ("notes", models.TextField(blank=True)),
                ("position", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("objectives", models.ManyToManyField(blank=True, related_name="course_units", to="api.learningobjective")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="api.courseunit")),
                ("training", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="units", to="api.training")),
            ],
            options={"ordering": ("position", "id")},
        ),
        migrations.CreateModel(
            name="RawMaterial",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("video", "Vidéo"), ("pdf", "PDF"), ("text", "Texte"), ("quiz", "Quiz")], db_index=True, max_length=10)),
                ("file", models.FileField(blank=True, upload_to=api.models.raw_material_upload_to)),
                ("content", models.TextField(blank=True)),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("mime_type", models.CharField(blank=True, max_length=150)),
                ("size", models.PositiveBigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="uploaded_raw_materials", to="api.profile")),
                ("training", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="raw_materials", to="api.training")),
            ],
            options={"ordering": ("-created_at", "-id")},
        ),
    ]
