from django.db import transaction
from django.utils import timezone

from api.models import CourseStructureGeneration, CourseUnit, Profile, Training
from api.services.structure_generation import validate_structure_payload


@transaction.atomic
def publish_training_structure(training_id: int, published_by: Profile) -> Training:
    training = Training.objects.select_for_update().get(pk=training_id)
    generation = CourseStructureGeneration.objects.select_for_update().get(
        training=training
    )

    if generation.status != CourseStructureGeneration.Status.READY:
        raise ValueError("La proposition IA n'est pas prête à être publiée.")

    structure = validate_structure_payload(training, generation.structure)
    objectives = {
        objective.id: objective for objective in training.objectives.all()
    }
    materials = {
        material.id: material for material in training.raw_materials.all()
    }

    training.units.all().delete()
    position = 0

    for module_data in structure.modules:
        position += 1
        module = CourseUnit.objects.create(
            training=training,
            kind=CourseUnit.Kind.MODULE,
            working_title=module_data.title,
            notes=module_data.rationale,
            position=position,
        )

        for chapter_data in module_data.chapters:
            position += 1
            chapter = CourseUnit.objects.create(
                training=training,
                parent=module,
                kind=CourseUnit.Kind.CHAPTER,
                working_title=chapter_data.title,
                notes=chapter_data.rationale,
                position=position,
            )

            for section_data in chapter_data.sections:
                position += 1
                section = CourseUnit.objects.create(
                    training=training,
                    parent=chapter,
                    kind=CourseUnit.Kind.SECTION,
                    working_title=section_data.title,
                    notes=section_data.rationale,
                    position=position,
                )
                section.objectives.set(
                    objectives[objective_id]
                    for objective_id in section_data.objective_ids
                )
                section.raw_materials.set(
                    materials[resource_id]
                    for resource_id in section_data.resource_ids
                )

    published_at = timezone.now()
    generation.published_at = published_at
    generation.published_by = published_by
    generation.progress_message = "Structure validée et publiée"
    generation.save(
        update_fields=[
            "published_at",
            "published_by",
            "progress_message",
            "updated_at",
        ]
    )
    training.status = Training.Status.READY
    training.save(update_fields=["status", "updated_at"])
    return training
