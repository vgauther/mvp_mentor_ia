from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone
from openai import OpenAI
from pydantic import BaseModel, Field

from api.models import CourseStructureGeneration, RawMaterialEnrichment, Training


class GeneratedSection(BaseModel):
    title: str = Field(min_length=3)
    rationale: str = Field(min_length=10)
    objective_ids: list[int] = Field(default_factory=list)
    resource_ids: list[int] = Field(min_length=1)


class GeneratedChapter(BaseModel):
    title: str = Field(min_length=3)
    rationale: str = Field(min_length=10)
    sections: list[GeneratedSection] = Field(min_length=1)


class GeneratedModule(BaseModel):
    title: str = Field(min_length=3)
    rationale: str = Field(min_length=10)
    chapters: list[GeneratedChapter] = Field(min_length=1)


class GeneratedCourseStructure(BaseModel):
    title: str = Field(min_length=3)
    introduction: str = Field(min_length=20)
    modules: list[GeneratedModule] = Field(min_length=1)
    unsupported_objective_ids: list[int] = Field(default_factory=list)


def _resource_payload(training: Training) -> list[dict[str, object]]:
    resources: list[dict[str, object]] = []
    materials = training.raw_materials.select_related("enrichment").all()
    for material in materials:
        enrichment = material.enrichment
        resources.append(
            {
                "resource_id": material.id,
                "kind": material.kind,
                "original_name": material.display_name,
                "metadata": {
                    "media_purpose": enrichment.media_purpose,
                    "summary": enrichment.summary,
                    "language": enrichment.language,
                    "key_concepts": enrichment.key_concepts,
                    "glossary": enrichment.glossary,
                    "keywords": enrichment.keywords,
                },
                "quiz": material.quiz_data if material.kind == "quiz" else None,
            }
        )
    return resources


def _validate_structure(
    structure: GeneratedCourseStructure,
    objective_ids: set[int],
    resource_ids: set[int],
) -> None:
    used_resources: list[int] = []
    mapped_objectives: set[int] = set()
    for module in structure.modules:
        for chapter in module.chapters:
            for section in chapter.sections:
                used_resources.extend(section.resource_ids)
                mapped_objectives.update(section.objective_ids)

    duplicate_resources = sorted(
        resource_id
        for resource_id in set(used_resources)
        if used_resources.count(resource_id) > 1
    )
    if duplicate_resources:
        raise ValueError(
            f"Ressources utilisées plusieurs fois : {duplicate_resources}"
        )
    used_resource_ids = set(used_resources)
    missing_resources = sorted(resource_ids - used_resource_ids)
    unknown_resources = sorted(used_resource_ids - resource_ids)
    if missing_resources or unknown_resources:
        raise ValueError(
            "La couverture des ressources est invalide : "
            f"manquantes={missing_resources}, inconnues={unknown_resources}."
        )

    unsupported = set(structure.unsupported_objective_ids)
    unknown_objectives = sorted((mapped_objectives | unsupported) - objective_ids)
    overlap = sorted(mapped_objectives & unsupported)
    missing_objectives = sorted(objective_ids - mapped_objectives - unsupported)
    if unknown_objectives or overlap or missing_objectives:
        raise ValueError(
            "La couverture des objectifs est invalide : "
            f"inconnus={unknown_objectives}, doublons={overlap}, "
            f"non classés={missing_objectives}."
        )


def validate_structure_payload(
    training: Training,
    payload: dict[str, object],
) -> GeneratedCourseStructure:
    structure = GeneratedCourseStructure.model_validate(payload)
    _validate_structure(
        structure,
        set(training.objectives.values_list("id", flat=True)),
        set(training.raw_materials.values_list("id", flat=True)),
    )
    return structure


def _generate_structure(training: Training) -> GeneratedCourseStructure:
    objectives = list(training.objectives.all())
    resources = _resource_payload(training)
    objective_ids = {objective.id for objective in objectives}
    resource_ids = {int(resource["resource_id"]) for resource in resources}
    payload = {
        "course": {
            "title": training.title,
            "description": training.description,
            "objectives": [
                {
                    "objective_id": objective.id,
                    "title": objective.title,
                    "description": objective.description,
                }
                for objective in objectives
            ],
        },
        "unordered_resources": resources,
    }

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.responses.parse(
        model=settings.OPENAI_TEXT_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "Tu es ingénieur pédagogique. Organise les ressources enrichies et non "
                    "ordonnées en une structure modules, chapitres et sections. Utilise chaque "
                    "resource_id exactement une fois et uniquement les identifiants fournis. "
                    "N’invente jamais de ressource, de fait ou d’objectif pédagogique. Les "
                    "objectifs sont autoritatifs et saisis manuellement : associe un objective_id "
                    "à une section seulement lorsque ses ressources le soutiennent réellement. "
                    "Place les objectifs non soutenus dans unsupported_objective_ids. Chaque "
                    "objectif doit être soit associé à au moins une section, soit déclaré non "
                    "soutenu, jamais les deux. Regroupe d’abord par concepts, puis ordonne des "
                    "fondations vers l’application. Place un quiz juste après les contenus qu’il "
                    "évalue lorsque le lien est clair ; garde les évaluations cumulatives à la "
                    "fin. N’utilise ni les identifiants ni les noms de fichiers pour déduire "
                    "l’ordre. Donne un titre et une justification concise à chaque niveau. "
                    "Rédige dans la langue des objectifs."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False),
            },
        ],
        text_format=GeneratedCourseStructure,
        max_output_tokens=20000,
    )
    parsed = getattr(response, "output_parsed", None)
    if not isinstance(parsed, GeneratedCourseStructure):
        raise RuntimeError("La réponse IA ne contient pas une structure exploitable.")
    _validate_structure(parsed, objective_ids, resource_ids)
    return parsed


def process_structure_generation(generation_id: int) -> None:
    close_old_connections()
    try:
        generation = CourseStructureGeneration.objects.select_related(
            "training"
        ).get(pk=generation_id)
        generation.status = CourseStructureGeneration.Status.PROCESSING
        generation.progress_message = "Organisation des ressources enrichies"
        generation.started_at = timezone.now()
        generation.error_message = ""
        generation.save(
            update_fields=[
                "status",
                "progress_message",
                "started_at",
                "error_message",
                "updated_at",
            ]
        )

        try:
            structure = _generate_structure(generation.training)
            generation.structure = structure.model_dump(mode="json")
            generation.status = CourseStructureGeneration.Status.READY
            generation.progress_message = "Proposition prête à être examinée"
            generation.ai_model = settings.OPENAI_TEXT_MODEL
            generation.generated_at = timezone.now()
            generation.save()
        except Exception as exc:
            generation.status = CourseStructureGeneration.Status.ERROR
            generation.progress_message = "Génération interrompue"
            generation.error_message = str(exc)[:4000]
            generation.save(
                update_fields=[
                    "status",
                    "progress_message",
                    "error_message",
                    "updated_at",
                ]
            )
    finally:
        close_old_connections()


_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mentor-structure")


def enqueue_structure_generation(generation_id: int) -> None:
    _executor.submit(process_structure_generation, generation_id)
