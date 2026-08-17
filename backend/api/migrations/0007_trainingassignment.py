from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0006_coursestructuregeneration"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrainingAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("assigned_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_training_assignments", to="api.profile")),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="training_assignments", to="api.profile")),
                ("training", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_assignments", to="api.training")),
            ],
            options={"ordering": ("created_at", "id")},
        ),
        migrations.AddConstraint(
            model_name="trainingassignment",
            constraint=models.UniqueConstraint(fields=("profile", "training"), name="unique_profile_training_assignment"),
        ),
    ]
