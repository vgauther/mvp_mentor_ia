from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0007_trainingassignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="courseunit",
            name="raw_materials",
            field=models.ManyToManyField(blank=True, related_name="course_units", to="api.rawmaterial"),
        ),
        migrations.AddField(
            model_name="coursestructuregeneration",
            name="published_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="coursestructuregeneration",
            name="published_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="published_course_structures", to="api.profile"),
        ),
    ]
