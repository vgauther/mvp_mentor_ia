from __future__ import annotations

import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz
import imageio_ffmpeg
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone
from openai import OpenAI
from pydantic import BaseModel, Field

from api.models import RawMaterial, RawMaterialEnrichment


class KeyConcept(BaseModel):
    name: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class GlossaryEntry(BaseModel):
    term: str = Field(min_length=1)
    definition: str = Field(min_length=1)


class ResourceMetadata(BaseModel):
    media_purpose: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    language: str = Field(min_length=2)
    key_concepts: list[KeyConcept]
    glossary: list[GlossaryEntry]
    keywords: list[str]


class MissingAIConfiguration(RuntimeError):
    pass


def ai_is_configured() -> bool:
    return bool(settings.OPENAI_API_KEY)


def _quiz_as_text(material: RawMaterial) -> str:
    lines: list[str] = []
    title = str(material.quiz_data.get("title", "")).strip()
    if title:
        lines.append(title)
    for index, question in enumerate(material.quiz_data.get("questions", []), start=1):
        lines.append(f"Question {index}: {question.get('prompt', '')}")
        for option in question.get("options", []):
            correctness = "réponse correcte" if option.get("is_correct") else "option"
            lines.append(f"- {option.get('text', '')} ({correctness})")
        answers = question.get("accepted_answers", [])
        if answers:
            lines.append("Réponses acceptées: " + ", ".join(map(str, answers)))
    return "\n".join(lines)


def _extract_pdf(material: RawMaterial) -> str:
    pages: list[str] = []
    with fitz.open(material.file.path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append(f"[Page {page_number}]\n{text}")
    if not pages:
        raise RuntimeError(
            "Aucun texte n’a été détecté dans ce PDF. Un traitement OCR sera nécessaire."
        )
    return "\n\n".join(pages)


def _transcribe_video(material: RawMaterial, client: OpenAI) -> str:
    with tempfile.TemporaryDirectory(prefix="mentor-enrichment-") as directory:
        segment_pattern = str(Path(directory) / "segment-%04d.mp3")
        command = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            material.file.path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "48k",
            "-f",
            "segment",
            "-segment_time",
            "300",
            "-reset_timestamps",
            "1",
            segment_pattern,
        ]
        subprocess.run(command, check=True, capture_output=True, timeout=3600)
        segments = sorted(Path(directory).glob("segment-*.mp3"))
        if not segments:
            raise RuntimeError("La piste audio de la vidéo n’a pas pu être extraite.")

        transcripts: list[str] = []
        for segment in segments:
            with segment.open("rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model=settings.OPENAI_TRANSCRIPTION_MODEL,
                    file=audio_file,
                    response_format="text",
                    prompt=(
                        "Transcris fidèlement ce contenu de formation dans sa langue "
                        "d’origine. Préserve les termes techniques, nombres et noms propres."
                    ),
                )
            transcripts.append(
                response if isinstance(response, str) else response.text
            )
        return "\n\n".join(transcripts).strip()


def _source_text(material: RawMaterial, client: OpenAI) -> tuple[str, str]:
    if material.kind == RawMaterial.Kind.VIDEO:
        return _transcribe_video(material, client), ""
    if material.kind == RawMaterial.Kind.PDF:
        return "", _extract_pdf(material)
    if material.kind == RawMaterial.Kind.QUIZ:
        return "", _quiz_as_text(material)
    return "", material.content.strip()


def _generate_metadata(
    material: RawMaterial,
    source_text: str,
    client: OpenAI,
) -> ResourceMetadata:
    payload = {
        "resource_id": material.id,
        "resource_type": material.kind,
        "source_content": source_text[:120000],
    }
    response = client.responses.parse(
        model=settings.OPENAI_TEXT_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "Analyse une ressource brute de formation et produis uniquement des "
                    "métadonnées descriptives fondées sur son contenu. Explique à quoi le média "
                    "peut servir, résume-le, identifie ses concepts clés et définis les termes "
                    "spécialisés. Ne crée aucun objectif pédagogique, aucun plan de cours, aucun "
                    "ordre et aucune information absente de la source. Reste dans la langue de "
                    "la ressource."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False),
            },
        ],
        text_format=ResourceMetadata,
    )
    parsed = getattr(response, "output_parsed", None)
    if isinstance(parsed, ResourceMetadata):
        return parsed
    raise RuntimeError("La réponse IA ne contient pas les métadonnées attendues.")


def _process_enrichment(enrichment_id: int) -> None:
    enrichment = RawMaterialEnrichment.objects.select_related("material").get(
        pk=enrichment_id
    )
    enrichment.status = RawMaterialEnrichment.Status.PROCESSING
    enrichment.progress_message = "Extraction du contenu source"
    enrichment.started_at = timezone.now()
    enrichment.error_message = ""
    enrichment.save(
        update_fields=[
            "status",
            "progress_message",
            "started_at",
            "error_message",
            "updated_at",
        ]
    )

    try:
        if not ai_is_configured():
            raise MissingAIConfiguration("La clé OpenAI n’est pas configurée.")

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        transcript, extracted_text = _source_text(enrichment.material, client)
        source_text = transcript or extracted_text
        if not source_text.strip():
            raise RuntimeError("Aucun contenu exploitable n’a été extrait de cette ressource.")

        enrichment.transcript = transcript
        enrichment.extracted_text = extracted_text
        enrichment.progress_message = "Génération des métadonnées"
        enrichment.save(
            update_fields=[
                "transcript",
                "extracted_text",
                "progress_message",
                "updated_at",
            ]
        )

        metadata = _generate_metadata(enrichment.material, source_text, client)
        enrichment.media_purpose = metadata.media_purpose
        enrichment.summary = metadata.summary
        enrichment.language = metadata.language[:20]
        enrichment.key_concepts = [item.model_dump() for item in metadata.key_concepts]
        enrichment.glossary = [item.model_dump() for item in metadata.glossary]
        enrichment.keywords = list(dict.fromkeys(metadata.keywords))
        enrichment.ai_model = settings.OPENAI_TEXT_MODEL
        enrichment.status = RawMaterialEnrichment.Status.READY
        enrichment.progress_message = "Enrichissement terminé"
        enrichment.generated_at = timezone.now()
        enrichment.save()
    except Exception as exc:  # l’erreur doit rester consultable ressource par ressource
        enrichment.status = RawMaterialEnrichment.Status.ERROR
        enrichment.progress_message = "Enrichissement interrompu"
        enrichment.error_message = str(exc)[:4000]
        enrichment.save(
            update_fields=[
                "status",
                "progress_message",
                "error_message",
                "updated_at",
            ]
        )


def process_training_enrichments(training_id: int) -> None:
    close_old_connections()
    try:
        enrichment_ids = list(
            RawMaterialEnrichment.objects.filter(
                material__training_id=training_id,
                status=RawMaterialEnrichment.Status.QUEUED,
            ).values_list("id", flat=True)
        )
        for enrichment_id in enrichment_ids:
            _process_enrichment(enrichment_id)
    finally:
        close_old_connections()


_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mentor-enrichment")


def enqueue_training_enrichment(training_id: int) -> None:
    _executor.submit(process_training_enrichments, training_id)
