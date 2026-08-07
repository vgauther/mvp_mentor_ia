from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0007_add_skipped_decision_choice"),
    ]

    operations = [
        migrations.AlterField(
            model_name="firstname",
            name="origin",
            field=models.CharField(
                blank=True,
                choices=[
                    ("indeterminee", "Indéterminée"),
                    ("internationale", "Internationale"),
                    ("arabe", "Arabe"),
                    ("hebraique", "Hébraïque"),
                    ("semitique_autre", "Sémitique autre"),
                    ("latine", "Latine"),
                    ("grecque", "Grecque"),
                    ("germanique", "Germanique"),
                    ("anglo_saxonne", "Anglo-saxonne"),
                    ("francaise", "Française"),
                    ("hispanique", "Hispanique"),
                    ("italienne", "Italienne"),
                    ("lusophone", "Lusophone"),
                    ("celtique", "Celtique"),
                    ("nordique_balte", "Nordique ou balte"),
                    ("slave", "Slave"),
                    ("basque", "Basque"),
                    ("balkanique", "Balkanique"),
                    ("turcique", "Turcique"),
                    ("persane_iranienne", "Persane ou iranienne"),
                    ("caucasienne", "Caucasienne"),
                    ("indienne_sanskrite", "Indienne ou sanskrite"),
                    ("sud_asiatique_autre", "Sud-asiatique autre"),
                    ("chinoise", "Chinoise"),
                    ("japonaise", "Japonaise"),
                    ("coreenne", "Coréenne"),
                    ("asiatique_sud_est", "Asiatique du Sud-Est"),
                    ("africaine", "Africaine"),
                    (
                        "austronesienne_oceanienne",
                        "Austronésienne ou océanienne",
                    ),
                    (
                        "autochtone_ameriques",
                        "Autochtone des Amériques",
                    ),
                ],
                db_index=True,
                max_length=150,
            ),
        ),
    ]