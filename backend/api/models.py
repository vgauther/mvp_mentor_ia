from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


class Profile(models.Model):
    """Projection locale minimale d'un utilisateur Keycloak."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur"
        LEARNER = "learner", "Apprenant"

    keycloak_id = models.CharField(
        max_length=255,
        unique=True,
        editable=False,
    )
    username = models.CharField(max_length=150)
    email = models.EmailField(
        null=True,
        blank=True,
        db_index=True,
    )
    display_name = models.CharField(
        max_length=150,
        blank=True,
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.LEARNER,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name or self.username


class Training(models.Model):
    """Formation en cours de préparation par un administrateur."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        STRUCTURING = "structuring", "En structuration"
        READY = "ready", "Prête"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    created_by = models.ForeignKey(
        Profile,
        on_delete=models.PROTECT,
        related_name="created_trainings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-id")

    def __str__(self) -> str:
        return self.title


class TrainingAssignment(models.Model):
    """Affectation d'une formation à un utilisateur."""

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="training_assignments",
    )
    training = models.ForeignKey(
        Training,
        on_delete=models.CASCADE,
        related_name="user_assignments",
    )
    assigned_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_training_assignments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("profile", "training"),
                name="unique_profile_training_assignment",
            )
        ]

    def __str__(self) -> str:
        return f"{self.profile} · {self.training}"


class LearningObjective(models.Model):
    """Compétence ou capacité que la formation doit faire acquérir."""

    training = models.ForeignKey(
        Training,
        on_delete=models.CASCADE,
        related_name="objectives",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "id")

    def __str__(self) -> str:
        return self.title


class CourseUnit(models.Model):
    """Élément de structure : module, chapitre ou section."""

    class Kind(models.TextChoices):
        MODULE = "module", "Module"
        CHAPTER = "chapter", "Chapitre"
        SECTION = "section", "Section"

    training = models.ForeignKey(
        Training,
        on_delete=models.CASCADE,
        related_name="units",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    working_title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    objectives = models.ManyToManyField(
        LearningObjective,
        blank=True,
        related_name="course_units",
    )
    raw_materials = models.ManyToManyField(
        "RawMaterial",
        blank=True,
        related_name="course_units",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "id")

    def clean(self):
        super().clean()

        if self.kind == self.Kind.MODULE and self.parent_id:
            raise ValidationError({"parent": "Un module ne peut pas avoir de parent."})

        if self.kind == self.Kind.CHAPTER:
            if not self.parent_id or self.parent.kind != self.Kind.MODULE:
                raise ValidationError(
                    {"parent": "Un chapitre doit appartenir à un module."}
                )

        if self.kind == self.Kind.SECTION:
            if not self.parent_id or self.parent.kind != self.Kind.CHAPTER:
                raise ValidationError(
                    {"parent": "Une section doit appartenir à un chapitre."}
                )

        if self.parent_id and self.parent.training_id != self.training_id:
            raise ValidationError(
                {"parent": "Le parent doit appartenir à la même formation."}
            )

    def __str__(self) -> str:
        return self.working_title


def raw_material_upload_to(instance, filename: str) -> str:
    suffix = Path(filename).suffix.lower()[:12]
    return f"raw-data/training-{instance.training_id}/{uuid4().hex}{suffix}"


class RawMaterial(models.Model):
    """Donnée source non transformée qui alimentera la génération future."""

    class Kind(models.TextChoices):
        VIDEO = "video", "Vidéo"
        PDF = "pdf", "PDF"
        TEXT = "text", "Texte"
        QUIZ = "quiz", "Quiz"

    training = models.ForeignKey(
        Training,
        on_delete=models.CASCADE,
        related_name="raw_materials",
    )
    kind = models.CharField(max_length=10, choices=Kind.choices, db_index=True)
    file = models.FileField(upload_to=raw_material_upload_to, blank=True)
    content = models.TextField(blank=True)
    quiz_data = models.JSONField(default=dict, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=150, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    created_by = models.ForeignKey(
        Profile,
        on_delete=models.PROTECT,
        related_name="uploaded_raw_materials",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    @property
    def display_name(self) -> str:
        if self.kind == self.Kind.QUIZ:
            title = str(self.quiz_data.get("title", "")).strip()
            if title:
                return title[:80]
            question_count = len(self.quiz_data.get("questions", []))
            suffix = "question" if question_count == 1 else "questions"
            return f"Quiz · {question_count} {suffix}"
        if self.original_filename:
            return self.original_filename
        if self.content:
            first_line = self.content.strip().splitlines()[0]
            return first_line[:80]
        return self.get_kind_display()

    def __str__(self) -> str:
        return self.display_name


class RawMaterialEnrichment(models.Model):
    """Contenu dérivé par IA sans altérer la donnée source associée."""

    class Status(models.TextChoices):
        PENDING = "pending", "À enrichir"
        QUEUED = "queued", "En attente"
        PROCESSING = "processing", "En cours"
        READY = "ready", "Prête"
        ERROR = "error", "Erreur"

    material = models.OneToOneField(
        RawMaterial,
        on_delete=models.CASCADE,
        related_name="enrichment",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    progress_message = models.CharField(max_length=255, blank=True)
    transcript = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)
    media_purpose = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    language = models.CharField(max_length=20, blank=True)
    key_concepts = models.JSONField(default=list, blank=True)
    glossary = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    ai_model = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.material.display_name} · {self.get_status_display()}"


class CourseStructureGeneration(models.Model):
    """Brouillon de structure produit par IA et conservé avant validation."""

    class Status(models.TextChoices):
        PENDING = "pending", "À générer"
        QUEUED = "queued", "En attente"
        PROCESSING = "processing", "En cours"
        READY = "ready", "Proposition prête"
        ERROR = "error", "Erreur"

    training = models.OneToOneField(
        Training,
        on_delete=models.CASCADE,
        related_name="structure_generation",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    progress_message = models.CharField(max_length=255, blank=True)
    structure = models.JSONField(default=dict, blank=True)
    ai_model = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_course_structures",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.training.title} · {self.get_status_display()}"


@receiver(post_delete, sender=RawMaterial)
def delete_raw_material_file(sender, instance, **kwargs):
    """Supprime également le fichier lorsqu'une source est supprimée."""

    if instance.file:
        instance.file.delete(save=False)
