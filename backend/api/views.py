from pathlib import Path

from django.core import signing
from django.db import models, transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    CourseStructureGeneration,
    CourseUnit,
    LearningObjective,
    Profile,
    RawMaterial,
    RawMaterialEnrichment,
    Training,
    TrainingAssignment,
)
from .permissions import IsProfileAdmin
from .serializers import (
    CourseUnitSerializer,
    LearningObjectiveSerializer,
    LearnerTrainingSerializer,
    ProfileRoleUpdateSerializer,
    ProfileSerializer,
    ProfileTrainingAssignmentSerializer,
    RawMaterialSerializer,
    TrainingDetailSerializer,
    TrainingListSerializer,
)
from .services.enrichment import ai_is_configured, enqueue_training_enrichment
from .services.publication import publish_training_structure
from .services.structure_generation import enqueue_structure_generation


def training_queryset():
    return (
        Training.objects.select_related("created_by", "structure_generation")
        .prefetch_related(
            "objectives",
            "units__objectives",
            "units__raw_materials",
            "raw_materials__enrichment",
        )
        .annotate(
            objective_count=models.Count("objectives", distinct=True),
            unit_count=models.Count("units", distinct=True),
            raw_material_count=models.Count("raw_materials", distinct=True),
        )
    )


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"project": "Mentor IA", "status": "ok"})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        return Response(
            {
                "id": profile.id,
                "keycloak_id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "display_name": profile.display_name,
                "role": profile.role,
                "role_label": profile.get_role_display(),
                "roles": [profile.role],
            }
        )


class AdminView(APIView):
    permission_classes = [IsProfileAdmin]

    def get(self, request):
        return Response(
            {
                "message": "Accès administrateur Mentor IA validé.",
                "username": request.user.username,
            }
        )


class UserListView(APIView):
    permission_classes = [IsProfileAdmin]

    def get(self, request):
        profiles = Profile.objects.prefetch_related(
            "training_assignments__training"
        ).order_by("id")
        return Response(ProfileSerializer(profiles, many=True).data)


class UserRoleView(APIView):
    permission_classes = [IsProfileAdmin]

    @transaction.atomic
    def patch(self, request, profile_id):
        profile = get_object_or_404(
            Profile.objects.select_for_update(),
            pk=profile_id,
        )
        serializer = ProfileRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data["role"]

        if (
            profile.role == Profile.Role.ADMIN
            and new_role != Profile.Role.ADMIN
            and not Profile.objects.exclude(pk=profile.pk).filter(
                role=Profile.Role.ADMIN
            ).exists()
        ):
            raise ValidationError(
                {
                    "role": (
                        "Le dernier administrateur ne peut pas devenir "
                        "apprenant."
                    )
                }
            )

        if profile.role != new_role:
            profile.role = new_role
            profile.save(update_fields=["role", "updated_at"])

        return Response(
            ProfileSerializer(profile).data,
            status=status.HTTP_200_OK,
        )


class UserTrainingAssignmentView(APIView):
    permission_classes = [IsProfileAdmin]

    @transaction.atomic
    def put(self, request, profile_id):
        profile = get_object_or_404(
            Profile.objects.select_for_update(),
            pk=profile_id,
        )
        serializer = ProfileTrainingAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trainings = serializer.validated_data["training_ids"]
        training_ids = {training.id for training in trainings}

        profile.training_assignments.exclude(training_id__in=training_ids).delete()
        existing_ids = set(
            profile.training_assignments.filter(training_id__in=training_ids)
            .values_list("training_id", flat=True)
        )
        TrainingAssignment.objects.bulk_create(
            [
                TrainingAssignment(
                    profile=profile,
                    training=training,
                    assigned_by=request.user.profile,
                )
                for training in trainings
                if training.id not in existing_ids
            ]
        )

        profile = Profile.objects.prefetch_related(
            "training_assignments__training"
        ).get(pk=profile.pk)
        return Response(ProfileSerializer(profile).data)


class LearnerTrainingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        trainings = Training.objects.filter(
            user_assignments__profile=request.user.profile
        ).order_by("-updated_at", "-id")
        return Response(LearnerTrainingSerializer(trainings, many=True).data)


class TrainingListCreateView(APIView):
    permission_classes = [IsProfileAdmin]

    def get(self, request):
        trainings = training_queryset()
        return Response(TrainingListSerializer(trainings, many=True).data)

    def post(self, request):
        serializer = TrainingListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        training = serializer.save(created_by=request.user.profile)
        training = training_queryset().get(pk=training.pk)
        return Response(
            TrainingDetailSerializer(training).data,
            status=status.HTTP_201_CREATED,
        )


class TrainingDetailView(APIView):
    permission_classes = [IsProfileAdmin]

    def get_object(self, training_id):
        return get_object_or_404(training_queryset(), pk=training_id)

    def get(self, request, training_id):
        return Response(TrainingDetailSerializer(self.get_object(training_id)).data)

    def patch(self, request, training_id):
        training = self.get_object(training_id)
        serializer = TrainingListSerializer(
            training,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        training = training_queryset().get(pk=training.pk)
        return Response(TrainingDetailSerializer(training).data)

    def delete(self, request, training_id):
        self.get_object(training_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LearningObjectiveListCreateView(APIView):
    permission_classes = [IsProfileAdmin]

    def get_training(self, training_id):
        return get_object_or_404(Training, pk=training_id)

    def get(self, request, training_id):
        training = self.get_training(training_id)
        return Response(
            LearningObjectiveSerializer(training.objectives.all(), many=True).data
        )

    def post(self, request, training_id):
        training = self.get_training(training_id)
        serializer = LearningObjectiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        next_position = (
            training.objectives.aggregate(max_position=models.Max("position"))[
                "max_position"
            ]
            or 0
        ) + 1
        serializer.save(training=training, position=next_position)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LearningObjectiveDetailView(APIView):
    permission_classes = [IsProfileAdmin]

    def get_object(self, training_id, objective_id):
        return get_object_or_404(
            LearningObjective,
            pk=objective_id,
            training_id=training_id,
        )

    def patch(self, request, training_id, objective_id):
        objective = self.get_object(training_id, objective_id)
        serializer = LearningObjectiveSerializer(
            objective,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, training_id, objective_id):
        self.get_object(training_id, objective_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseUnitListCreateView(APIView):
    permission_classes = [IsProfileAdmin]

    def get_training(self, training_id):
        return get_object_or_404(Training, pk=training_id)

    def get(self, request, training_id):
        training = self.get_training(training_id)
        units = training.units.prefetch_related("objectives")
        return Response(CourseUnitSerializer(units, many=True).data)

    def post(self, request, training_id):
        training = self.get_training(training_id)
        serializer = CourseUnitSerializer(
            data=request.data,
            context={"training": training},
        )
        serializer.is_valid(raise_exception=True)
        next_position = (
            training.units.aggregate(max_position=models.Max("position"))[
                "max_position"
            ]
            or 0
        ) + 1
        serializer.save(training=training, position=next_position)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CourseUnitDetailView(APIView):
    permission_classes = [IsProfileAdmin]

    def get_object(self, training_id, unit_id):
        return get_object_or_404(
            CourseUnit.objects.prefetch_related("objectives"),
            pk=unit_id,
            training_id=training_id,
        )

    def patch(self, request, training_id, unit_id):
        unit = self.get_object(training_id, unit_id)
        serializer = CourseUnitSerializer(
            unit,
            data=request.data,
            partial=True,
            context={"training": unit.training},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, training_id, unit_id):
        self.get_object(training_id, unit_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RawMaterialListCreateView(APIView):
    permission_classes = [IsProfileAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_training(self, training_id):
        return get_object_or_404(Training, pk=training_id)

    def get(self, request, training_id):
        training = self.get_training(training_id)
        return Response(
            RawMaterialSerializer(training.raw_materials.all(), many=True).data
        )

    def post(self, request, training_id):
        training = self.get_training(training_id)
        serializer = RawMaterialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(training=training, created_by=request.user.profile)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RawMaterialDetailView(APIView):
    permission_classes = [IsProfileAdmin]

    def get_object(self, training_id, material_id):
        return get_object_or_404(
            RawMaterial,
            pk=material_id,
            training_id=training_id,
        )

    def delete(self, request, training_id, material_id):
        self.get_object(training_id, material_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, training_id, material_id):
        material = self.get_object(training_id, material_id)
        serializer = RawMaterialSerializer(
            material,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TrainingEnrichmentGenerateView(APIView):
    permission_classes = [IsProfileAdmin]

    @transaction.atomic
    def post(self, request, training_id):
        training = get_object_or_404(Training, pk=training_id)
        materials = list(training.raw_materials.all())
        if not materials:
            return Response(
                {"detail": "Ajoutez au moins une ressource avant l’enrichissement."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not ai_is_configured():
            return Response(
                {
                    "detail": (
                        "Le moteur IA n’est pas configuré. Ajoutez OPENAI_API_KEY "
                        "au service backend avant de lancer l’enrichissement."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        force = bool(request.data.get("force", False))
        queued_count = 0
        for material in materials:
            enrichment, created = RawMaterialEnrichment.objects.get_or_create(
                material=material
            )
            if enrichment.status == RawMaterialEnrichment.Status.PROCESSING:
                continue
            if (
                enrichment.status == RawMaterialEnrichment.Status.READY
                and not force
            ):
                continue

            enrichment.status = RawMaterialEnrichment.Status.QUEUED
            enrichment.progress_message = "En attente de traitement"
            enrichment.error_message = ""
            if force or created:
                enrichment.generated_at = None
            enrichment.save(
                update_fields=[
                    "status",
                    "progress_message",
                    "error_message",
                    "generated_at",
                    "updated_at",
                ]
            )
            queued_count += 1

        transaction.on_commit(lambda: enqueue_training_enrichment(training.id))
        return Response(
            {"queued": queued_count, "total": len(materials)},
            status=status.HTTP_202_ACCEPTED,
        )


class TrainingStructureGenerateView(APIView):
    permission_classes = [IsProfileAdmin]

    @transaction.atomic
    def post(self, request, training_id):
        training = get_object_or_404(Training, pk=training_id)
        objective_count = training.objectives.count()
        materials = training.raw_materials.all()
        material_count = materials.count()

        if not ai_is_configured():
            return Response(
                {"detail": "Le moteur IA n’est pas configuré."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if objective_count == 0:
            return Response(
                {"detail": "Renseignez au moins un objectif pédagogique."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if material_count == 0:
            return Response(
                {"detail": "Ajoutez au moins une ressource."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ready_count = materials.filter(
            enrichment__status=RawMaterialEnrichment.Status.READY
        ).count()
        if ready_count != material_count:
            return Response(
                {
                    "detail": (
                        "Toutes les ressources doivent être enrichies avant la "
                        f"génération ({ready_count}/{material_count} prêtes)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        generation, _ = CourseStructureGeneration.objects.get_or_create(
            training=training
        )
        if generation.status in {
            CourseStructureGeneration.Status.QUEUED,
            CourseStructureGeneration.Status.PROCESSING,
        }:
            return Response(
                {"detail": "Une génération est déjà en cours."},
                status=status.HTTP_409_CONFLICT,
            )
        if (
            generation.status == CourseStructureGeneration.Status.READY
            and not bool(request.data.get("force", False))
        ):
            return Response(
                {"detail": "Une proposition existe déjà. Confirmez sa régénération."},
                status=status.HTTP_409_CONFLICT,
            )

        generation.status = CourseStructureGeneration.Status.QUEUED
        generation.progress_message = "En attente de génération"
        generation.error_message = ""
        generation.published_at = None
        generation.published_by = None
        generation.save(
            update_fields=[
                "status",
                "progress_message",
                "error_message",
                "published_at",
                "published_by",
                "updated_at",
            ]
        )
        training.status = Training.Status.STRUCTURING
        training.save(update_fields=["status", "updated_at"])
        transaction.on_commit(lambda: enqueue_structure_generation(generation.id))
        return Response(
            {"status": generation.status},
            status=status.HTTP_202_ACCEPTED,
        )


class TrainingStructurePublishView(APIView):
    permission_classes = [IsProfileAdmin]

    def post(self, request, training_id):
        get_object_or_404(Training, pk=training_id)
        try:
            publish_training_structure(training_id, request.user.profile)
        except CourseStructureGeneration.DoesNotExist:
            raise ValidationError(
                {"detail": "Générez une proposition avant de la publier."}
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})

        training = training_queryset().get(pk=training_id)
        return Response(TrainingDetailSerializer(training).data)


class RawMaterialDownloadView(RawMaterialDetailView):
    def get(self, request, training_id, material_id):
        material = self.get_object(training_id, material_id)
        if not material.file:
            return Response(
                {"detail": "Cette donnée brute ne contient pas de fichier."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(
            material.file.open("rb"),
            as_attachment=True,
            filename=material.original_filename or Path(material.file.name).name,
            content_type=material.mime_type or "application/octet-stream",
        )


class RawMaterialPreviewTokenView(RawMaterialDetailView):
    def get(self, request, training_id, material_id):
        material = self.get_object(training_id, material_id)
        if not material.file:
            return Response(
                {"detail": "Cette ressource ne contient pas de fichier."},
                status=status.HTTP_404_NOT_FOUND,
            )

        token = signing.dumps(
            {
                "training_id": material.training_id,
                "material_id": material.id,
            },
            salt="raw-material-preview",
            compress=True,
        )
        return Response({"url": f"/api/raw-material-previews/{token}/"})


class RawMaterialPreviewView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            payload = signing.loads(
                token,
                salt="raw-material-preview",
                max_age=300,
            )
        except signing.BadSignature:
            return Response(
                {"detail": "Ce lien de prévisualisation est invalide ou expiré."},
                status=status.HTTP_403_FORBIDDEN,
            )

        material = get_object_or_404(
            RawMaterial,
            pk=payload.get("material_id"),
            training_id=payload.get("training_id"),
        )
        if not material.file:
            return Response(
                {"detail": "Cette ressource ne contient pas de fichier."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = FileResponse(
            material.file.open("rb"),
            as_attachment=False,
            filename=material.original_filename or Path(material.file.name).name,
            content_type=material.mime_type or "application/octet-stream",
        )
        response["Cache-Control"] = "private, max-age=300"
        return response
