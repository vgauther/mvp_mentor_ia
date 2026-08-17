import json
import xml.etree.ElementTree as ET

from django.db import migrations, models


def element_text(element):
    return " ".join(" ".join(element.itertext()).split())


def convert_quiz_xml(apps, schema_editor):
    RawMaterial = apps.get_model("api", "RawMaterial")

    for material in RawMaterial.objects.filter(kind="quiz").iterator():
        raw_content = material.content.strip()
        if not raw_content:
            continue

        try:
            root = ET.fromstring(raw_content)
        except ET.ParseError as error:
            raise RuntimeError(
                f"Impossible de convertir le quiz brut {material.pk}."
            ) from error

        questions = []
        for response in root:
            if response.tag == "stringresponse":
                prompt_element = response.find("div")
                prompt = element_text(prompt_element) if prompt_element is not None else ""
                answer = response.attrib.get("answer", "").strip()
                questions.append(
                    {
                        "type": "short_text",
                        "prompt": prompt,
                        "accepted_answers": [answer],
                    }
                )
                continue

            if response.tag == "multiplechoiceresponse":
                prompt_element = response.find("div")
                prompt = element_text(prompt_element) if prompt_element is not None else ""
                options = []
                for choice in response.findall("./choicegroup/choice"):
                    options.append(
                        {
                            "text": element_text(choice),
                            "is_correct": choice.attrib.get("correct") == "true",
                        }
                    )
                questions.append(
                    {
                        "type": "single_choice",
                        "prompt": prompt,
                        "options": options,
                    }
                )

        if not questions:
            raise RuntimeError(f"Le quiz brut {material.pk} ne contient aucune question.")

        quiz_data = {"title": "", "questions": questions}
        material.quiz_data = quiz_data
        material.content = ""
        material.size = len(
            json.dumps(
                quiz_data,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        material.save(update_fields=("quiz_data", "content", "size"))


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0003_training_learningobjective_courseunit_rawmaterial"),
    ]

    operations = [
        migrations.AddField(
            model_name="rawmaterial",
            name="quiz_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(convert_quiz_xml, migrations.RunPython.noop),
    ]
