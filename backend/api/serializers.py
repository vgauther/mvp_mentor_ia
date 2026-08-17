import json
from pathlib import Path

from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from .models import (
    CourseStructureGeneration,
    CourseUnit,
    LearningObjective,
    Profile,
    RawMaterial,
    RawMaterialEnrichment,
    Training,
)


class ProfileSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )
    assigned_trainings = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            "id",
            "username",
            "email",
            "display_name",
            "role",
            "role_label",
            "assigned_trainings",
            "created_at",
            "updated_at",
        )

    def get_assigned_trainings(self, obj):
        assignments = obj.training_assignments.all()
        return [
            {
                "id": assignment.training_id,
                "title": assignment.training.title,
                "status": assignment.training.status,
                "status_label": assignment.training.get_status_display(),
            }
            for assignment in assignments
        ]


class ProfileRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Profile.Role.choices)


class ProfileTrainingAssignmentSerializer(serializers.Serializer):
    training_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )

    def validate_training_ids(self, training_ids):
        if len(training_ids) != len(set(training_ids)):
            raise serializers.ValidationError(
                "Une formation ne peut être attribuée qu'une seule fois."
            )

        trainings_by_id = {
            training.id: training
            for training in Training.objects.filter(pk__in=training_ids)
        }
        if len(trainings_by_id) != len(training_ids):
            raise serializers.ValidationError(
                "Une ou plusieurs formations sont introuvables."
            )
        return [trainings_by_id[training_id] for training_id in training_ids]


class LearnerTrainingSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Training
        fields = ("id", "title", "description", "status", "status_label", "updated_at")


class LearningObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObjective
        fields = (
            "id",
            "title",
            "description",
            "position",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "position", "created_at", "updated_at")


class CourseUnitSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    objective_ids = serializers.PrimaryKeyRelatedField(
        source="objectives",
        many=True,
        queryset=LearningObjective.objects.all(),
        required=False,
    )
    resource_ids = serializers.PrimaryKeyRelatedField(
        source="raw_materials",
        many=True,
        queryset=RawMaterial.objects.all(),
        required=False,
    )

    class Meta:
        model = CourseUnit
        fields = (
            "id",
            "parent",
            "kind",
            "kind_label",
            "working_title",
            "notes",
            "position",
            "objective_ids",
            "resource_ids",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "kind_label",
            "position",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        training = self.context["training"]
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        objectives = attrs.get("objectives", [])
        raw_materials = attrs.get("raw_materials", [])

        if parent and parent.training_id != training.id:
            raise serializers.ValidationError(
                {"parent": "Le parent doit appartenir à cette formation."}
            )

        invalid_objectives = [
            objective.id
            for objective in objectives
            if objective.training_id != training.id
        ]
        if invalid_objectives:
            raise serializers.ValidationError(
                {
                    "objective_ids": (
                        "Tous les objectifs doivent appartenir à cette formation."
                    )
                }
            )

        invalid_resources = [
            material.id
            for material in raw_materials
            if material.training_id != training.id
        ]
        if invalid_resources:
            raise serializers.ValidationError(
                {
                    "resource_ids": (
                        "Toutes les ressources doivent appartenir à cette formation."
                    )
                }
            )

        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        if kind == CourseUnit.Kind.MODULE and parent:
            raise serializers.ValidationError(
                {"parent": "Un module ne peut pas avoir de parent."}
            )
        if kind == CourseUnit.Kind.CHAPTER and (
            not parent or parent.kind != CourseUnit.Kind.MODULE
        ):
            raise serializers.ValidationError(
                {"parent": "Un chapitre doit appartenir à un module."}
            )
        if kind == CourseUnit.Kind.SECTION and (
            not parent or parent.kind != CourseUnit.Kind.CHAPTER
        ):
            raise serializers.ValidationError(
                {"parent": "Une section doit appartenir à un chapitre."}
            )

        return attrs


class RawMaterialEnrichmentSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = RawMaterialEnrichment
        fields = (
            "status",
            "status_label",
            "progress_message",
            "transcript",
            "extracted_text",
            "media_purpose",
            "summary",
            "language",
            "key_concepts",
            "glossary",
            "keywords",
            "ai_model",
            "error_message",
            "started_at",
            "generated_at",
            "updated_at",
        )


class CourseStructureGenerationSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    published_by_name = serializers.CharField(
        source="published_by.display_name",
        read_only=True,
        default="",
    )

    class Meta:
        model = CourseStructureGeneration
        fields = (
            "status",
            "status_label",
            "progress_message",
            "structure",
            "ai_model",
            "error_message",
            "started_at",
            "generated_at",
            "published_at",
            "published_by_name",
            "updated_at",
        )


class RawMaterialSerializer(serializers.ModelSerializer):
    QUIZ_QUESTION_TYPES = {"single_choice", "multiple_choice", "short_text"}

    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    display_name = serializers.CharField(read_only=True)
    file = serializers.FileField(write_only=True, required=False)
    has_file = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    enrichment = RawMaterialEnrichmentSerializer(read_only=True, default=None)

    class Meta:
        model = RawMaterial
        fields = (
            "id",
            "kind",
            "kind_label",
            "display_name",
            "file",
            "content",
            "quiz_data",
            "has_file",
            "download_url",
            "original_filename",
            "mime_type",
            "size",
            "created_at",
            "enrichment",
        )
        read_only_fields = (
            "id",
            "kind_label",
            "display_name",
            "has_file",
            "download_url",
            "original_filename",
            "mime_type",
            "size",
            "created_at",
            "enrichment",
        )
        extra_kwargs = {
            "content": {"required": False, "allow_blank": True},
            "quiz_data": {"required": False},
        }

    def get_has_file(self, obj):
        return bool(obj.file)

    def get_download_url(self, obj):
        if not obj.file:
            return None
        return (
            f"/api/admin/trainings/{obj.training_id}/"
            f"raw-materials/{obj.id}/download/"
        )

    def validate_quiz_data(self, quiz_data):
        if not isinstance(quiz_data, dict):
            raise serializers.ValidationError("Le quiz doit être un objet structuré.")

        title = str(quiz_data.get("title", "")).strip()
        questions = quiz_data.get("questions")
        if not isinstance(questions, list) or not questions:
            raise serializers.ValidationError("Ajoutez au moins une question au quiz.")

        cleaned_questions = []
        for question_index, question in enumerate(questions, start=1):
            if not isinstance(question, dict):
                raise serializers.ValidationError(
                    f"La question {question_index} doit être un objet structuré."
                )

            question_type = question.get("type")
            if question_type not in self.QUIZ_QUESTION_TYPES:
                raise serializers.ValidationError(
                    f"Le type de la question {question_index} est invalide."
                )

            prompt = str(question.get("prompt", "")).strip()
            if not prompt:
                raise serializers.ValidationError(
                    f"Le texte de la question {question_index} est requis."
                )

            cleaned_question = {"type": question_type, "prompt": prompt}
            if question_type == "short_text":
                answers = question.get("accepted_answers")
                if not isinstance(answers, list):
                    answers = []
                cleaned_answers = [str(answer).strip() for answer in answers]
                cleaned_answers = [answer for answer in cleaned_answers if answer]
                if not cleaned_answers:
                    raise serializers.ValidationError(
                        f"Ajoutez une réponse acceptée à la question {question_index}."
                    )
                cleaned_question["accepted_answers"] = cleaned_answers
            else:
                options = question.get("options")
                if not isinstance(options, list) or len(options) < 2:
                    raise serializers.ValidationError(
                        f"Ajoutez au moins deux choix à la question {question_index}."
                    )

                cleaned_options = []
                for option_index, option in enumerate(options, start=1):
                    if not isinstance(option, dict):
                        raise serializers.ValidationError(
                            f"Le choix {option_index} de la question {question_index} est invalide."
                        )
                    text = str(option.get("text", "")).strip()
                    if not text:
                        raise serializers.ValidationError(
                            f"Le choix {option_index} de la question {question_index} est vide."
                        )
                    cleaned_options.append(
                        {"text": text, "is_correct": bool(option.get("is_correct"))}
                    )

                correct_count = sum(
                    option["is_correct"] for option in cleaned_options
                )
                if question_type == "single_choice" and correct_count != 1:
                    raise serializers.ValidationError(
                        f"Sélectionnez une seule bonne réponse à la question {question_index}."
                    )
                if question_type == "multiple_choice" and correct_count < 1:
                    raise serializers.ValidationError(
                        f"Sélectionnez au moins une bonne réponse à la question {question_index}."
                    )
                cleaned_question["options"] = cleaned_options

            cleaned_questions.append(cleaned_question)

        return {"title": title, "questions": cleaned_questions}

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        uploaded_file = attrs.get("file")
        content = attrs.get(
            "content", getattr(self.instance, "content", "")
        ).strip()

        if kind in (RawMaterial.Kind.VIDEO, RawMaterial.Kind.PDF):
            if not uploaded_file and not getattr(self.instance, "file", None):
                raise serializers.ValidationError(
                    {"file": "Un fichier est requis pour ce type de donnée."}
                )
            if uploaded_file.size > settings.RAW_UPLOAD_MAX_SIZE:
                raise serializers.ValidationError(
                    {"file": "Le fichier dépasse la taille maximale de 500 Mo."}
                )

            suffix = Path(uploaded_file.name).suffix.lower()
            mime_type = getattr(uploaded_file, "content_type", "") or ""
            if kind == RawMaterial.Kind.PDF and (
                suffix != ".pdf" or mime_type not in ("application/pdf", "")
            ):
                raise serializers.ValidationError(
                    {"file": "Le fichier sélectionné doit être un PDF."}
                )
            if kind == RawMaterial.Kind.VIDEO and mime_type and not mime_type.startswith(
                "video/"
            ):
                raise serializers.ValidationError(
                    {"file": "Le fichier sélectionné doit être une vidéo."}
                )

        if kind == RawMaterial.Kind.TEXT and not content:
            raise serializers.ValidationError(
                {"content": "Le contenu brut ne peut pas être vide."}
            )

        if kind == RawMaterial.Kind.QUIZ:
            quiz_data = attrs.get(
                "quiz_data", getattr(self.instance, "quiz_data", None)
            )
            attrs["quiz_data"] = self.validate_quiz_data(quiz_data)
            attrs["content"] = ""
        else:
            attrs["quiz_data"] = {}
            attrs["content"] = content

        return attrs

    @staticmethod
    def structured_quiz_size(quiz_data):
        return len(
            json.dumps(quiz_data, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )

    def create(self, validated_data):
        uploaded_file = validated_data.get("file")
        if uploaded_file:
            validated_data["original_filename"] = Path(uploaded_file.name).name[:255]
            validated_data["mime_type"] = (
                getattr(uploaded_file, "content_type", "") or ""
            )[:150]
            validated_data["size"] = uploaded_file.size
        elif validated_data.get("kind") == RawMaterial.Kind.QUIZ:
            validated_data["size"] = self.structured_quiz_size(
                validated_data["quiz_data"]
            )
        else:
            validated_data["size"] = len(
                validated_data.get("content", "").encode("utf-8")
            )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.kind == RawMaterial.Kind.QUIZ and "quiz_data" in validated_data:
            validated_data["size"] = self.structured_quiz_size(
                validated_data["quiz_data"]
            )
        instance = super().update(instance, validated_data)
        RawMaterialEnrichment.objects.filter(material=instance).update(
            status=RawMaterialEnrichment.Status.PENDING,
            progress_message="La source a changé, un nouvel enrichissement est nécessaire.",
            media_purpose="",
            summary="",
            language="",
            key_concepts=[],
            glossary=[],
            keywords=[],
            ai_model="",
            error_message="",
            started_at=None,
            generated_at=None,
        )
        return instance


class TrainingListSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.display_name",
        read_only=True,
    )
    objective_count = serializers.IntegerField(read_only=True)
    unit_count = serializers.IntegerField(read_only=True)
    raw_material_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Training
        fields = (
            "id",
            "title",
            "description",
            "status",
            "status_label",
            "created_by_name",
            "objective_count",
            "unit_count",
            "raw_material_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status_label",
            "created_by_name",
            "objective_count",
            "unit_count",
            "raw_material_count",
            "created_at",
            "updated_at",
        )


class TrainingDetailSerializer(TrainingListSerializer):
    enrichment_ai_configured = serializers.SerializerMethodField()
    objectives = LearningObjectiveSerializer(many=True, read_only=True)
    units = CourseUnitSerializer(many=True, read_only=True)
    raw_materials = RawMaterialSerializer(many=True, read_only=True)
    structure_generation = CourseStructureGenerationSerializer(
        read_only=True,
        default=None,
    )

    class Meta(TrainingListSerializer.Meta):
        fields = TrainingListSerializer.Meta.fields + (
            "objectives",
            "units",
            "raw_materials",
            "enrichment_ai_configured",
            "structure_generation",
        )

    def get_enrichment_ai_configured(self, obj):
        return bool(settings.OPENAI_API_KEY)


class PublicLearningObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObjective
        fields = ("id", "title", "description", "position")


class PublicRawMaterialSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="display_name", read_only=True)
    has_file = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = RawMaterial
        fields = (
            "id",
            "kind",
            "name",
            "content",
            "quiz_data",
            "has_file",
            "file_url",
            "original_filename",
            "mime_type",
            "size",
        )

    def get_has_file(self, obj):
        return bool(obj.file)

    def get_file_url(self, obj):
        if not obj.file:
            return None

        path = reverse(
            "public-raw-material-file",
            kwargs={
                "training_id": obj.training_id,
                "material_id": obj.id,
            },
        )
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


class PublicTrainingListSerializer(serializers.ModelSerializer):
    published_at = serializers.DateTimeField(
        source="structure_generation.published_at",
        read_only=True,
    )

    class Meta:
        model = Training
        fields = (
            "id",
            "title",
            "description",
            "published_at",
            "updated_at",
        )


class PublicTrainingDetailSerializer(PublicTrainingListSerializer):
    objectives = PublicLearningObjectiveSerializer(many=True, read_only=True)
    structure = serializers.SerializerMethodField()
    raw_materials = PublicRawMaterialSerializer(many=True, read_only=True)

    class Meta(PublicTrainingListSerializer.Meta):
        fields = PublicTrainingListSerializer.Meta.fields + (
            "objectives",
            "structure",
            "raw_materials",
        )

    def get_structure(self, obj):
        units = list(obj.units.all())
        children_by_parent = {}
        for unit in units:
            children_by_parent.setdefault(unit.parent_id, []).append(unit)

        def serialize_unit(unit):
            return {
                "id": unit.id,
                "kind": unit.kind,
                "title": unit.working_title,
                "notes": unit.notes,
                "position": unit.position,
                "objective_ids": [
                    objective.id for objective in unit.objectives.all()
                ],
                "raw_material_ids": [
                    material.id for material in unit.raw_materials.all()
                ],
                "children": [
                    serialize_unit(child)
                    for child in children_by_parent.get(unit.id, [])
                ],
            }

        return [serialize_unit(unit) for unit in children_by_parent.get(None, [])]
