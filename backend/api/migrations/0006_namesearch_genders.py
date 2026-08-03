import api.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0005_namedecision"),
    ]

    operations = [
        migrations.AddField(
            model_name="namesearch",
            name="genders",
            field=models.JSONField(
                default=api.models.default_search_genders,
            ),
        ),
    ]