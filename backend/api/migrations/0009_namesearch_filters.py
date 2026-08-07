from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0008_firstname_origin_nomenclature"),
    ]

    operations = [
        migrations.AddField(
            model_name="namesearch",
            name="first_letters",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="namesearch",
            name="max_length",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="namesearch",
            name="min_length",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="namesearch",
            name="origins",
            field=models.JSONField(default=list),
        ),
    ]
