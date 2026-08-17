import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .authentication import KeycloakUser, get_or_sync_profile
from .models import (
    CourseStructureGeneration,
    CourseUnit,
    Profile,
    RawMaterial,
    RawMaterialEnrichment,
    Training,
    TrainingAssignment,
)


class GetOrSyncProfileTests(TestCase):
    def test_creates_profile(self):
        profile = get_or_sync_profile(
            keycloak_id="keycloak-user-1",
            username="test-user",
            email="test-user@example.test",
        )

        self.assertEqual(Profile.objects.count(), 1)
        self.assertEqual(profile.keycloak_id, "keycloak-user-1")
        self.assertEqual(profile.username, "test-user")
        self.assertEqual(profile.email, "test-user@example.test")
        self.assertEqual(profile.display_name, "")
        self.assertEqual(profile.role, Profile.Role.ADMIN)

    def test_assigns_learner_role_after_first_profile(self):
        get_or_sync_profile(
            keycloak_id="keycloak-admin",
            username="admin-user",
            email="admin@example.test",
        )

        learner = get_or_sync_profile(
            keycloak_id="keycloak-learner",
            username="learner-user",
            email="learner@example.test",
        )

        self.assertEqual(learner.role, Profile.Role.LEARNER)

    def test_does_not_create_duplicate(self):
        first_profile = get_or_sync_profile(
            keycloak_id="keycloak-user-1",
            username="test-user",
            email="test-user@example.test",
        )

        second_profile = get_or_sync_profile(
            keycloak_id="keycloak-user-1",
            username="test-user",
            email="test-user@example.test",
        )

        self.assertEqual(Profile.objects.count(), 1)
        self.assertEqual(first_profile.pk, second_profile.pk)

    def test_updates_username_and_email(self):
        profile = get_or_sync_profile(
            keycloak_id="keycloak-user-1",
            username="old-username",
            email="old-email@example.test",
        )

        get_or_sync_profile(
            keycloak_id="keycloak-user-1",
            username="new-username",
            email="new-email@example.test",
        )

        profile.refresh_from_db()

        self.assertEqual(profile.username, "new-username")
        self.assertEqual(profile.email, "new-email@example.test")

    def test_preserves_display_name(self):
        profile = get_or_sync_profile(
            keycloak_id="keycloak-user-1",
            username="test-user",
            email="test-user@example.test",
        )

        profile.display_name = "Mon nom affiché"
        profile.save(update_fields=["display_name", "updated_at"])

        get_or_sync_profile(
            keycloak_id="keycloak-user-1",
            username="updated-user",
            email="updated-user@example.test",
        )

        profile.refresh_from_db()

        self.assertEqual(profile.display_name, "Mon nom affiché")


class ApiFoundationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.profile = Profile.objects.create(
            keycloak_id="keycloak-user-1",
            username="mentor-user",
            email="mentor-user@example.test",
            display_name="Mentor User",
            role=Profile.Role.LEARNER,
        )

    def authenticate_with_role(self, role):
        self.profile.role = role
        self.profile.save(update_fields=["role", "updated_at"])
        user = KeycloakUser(
            id=self.profile.keycloak_id,
            username=self.profile.username,
            email=self.profile.email,
            roles=frozenset({role}),
            claims={},
            profile=self.profile,
        )
        self.client.force_authenticate(user=user)

    def test_health_route_is_public(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"project": "Mentor IA", "status": "ok"},
        )

    def test_me_route_returns_authenticated_profile(self):
        self.authenticate_with_role(Profile.Role.LEARNER)

        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["display_name"], "Mentor User")
        self.assertEqual(response.json()["role"], "learner")
        self.assertEqual(response.json()["roles"], ["learner"])

    def test_admin_route_requires_admin_role(self):
        self.authenticate_with_role(Profile.Role.LEARNER)
        self.assertEqual(self.client.get("/api/admin/").status_code, 403)

        self.authenticate_with_role(Profile.Role.ADMIN)
        response = self.client.get("/api/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "mentor-user")

    def test_admin_can_list_users_and_change_a_role(self):
        self.authenticate_with_role(Profile.Role.ADMIN)
        learner = Profile.objects.create(
            keycloak_id="keycloak-learner",
            username="learner-user",
            email="learner@example.test",
            role=Profile.Role.LEARNER,
        )

        list_response = self.client.get("/api/admin/users/")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 2)
        self.assertEqual(list_response.json()[1]["role"], "learner")

        role_response = self.client.patch(
            f"/api/admin/users/{learner.pk}/role/",
            {"role": "admin"},
            format="json",
        )

        self.assertEqual(role_response.status_code, 200)
        learner.refresh_from_db()
        self.assertEqual(learner.role, Profile.Role.ADMIN)

    def test_admin_can_assign_replace_and_remove_user_trainings(self):
        self.authenticate_with_role(Profile.Role.ADMIN)
        learner = Profile.objects.create(
            keycloak_id="keycloak-assigned-learner",
            username="assigned-learner",
            role=Profile.Role.LEARNER,
        )
        first_training = Training.objects.create(
            title="Première formation",
            created_by=self.profile,
        )
        second_training = Training.objects.create(
            title="Deuxième formation",
            created_by=self.profile,
        )

        response = self.client.put(
            f"/api/admin/users/{learner.pk}/trainings/",
            {"training_ids": [first_training.pk, second_training.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [training["id"] for training in response.json()["assigned_trainings"]],
            [first_training.pk, second_training.pk],
        )
        self.assertEqual(TrainingAssignment.objects.filter(profile=learner).count(), 2)
        self.assertTrue(
            TrainingAssignment.objects.filter(
                profile=learner,
                assigned_by=self.profile,
            ).exists()
        )

        replace_response = self.client.put(
            f"/api/admin/users/{learner.pk}/trainings/",
            {"training_ids": [second_training.pk]},
            format="json",
        )
        self.assertEqual(replace_response.status_code, 200)
        self.assertEqual(
            [training["id"] for training in replace_response.json()["assigned_trainings"]],
            [second_training.pk],
        )

        remove_response = self.client.put(
            f"/api/admin/users/{learner.pk}/trainings/",
            {"training_ids": []},
            format="json",
        )
        self.assertEqual(remove_response.status_code, 200)
        self.assertEqual(remove_response.json()["assigned_trainings"], [])
        self.assertFalse(TrainingAssignment.objects.filter(profile=learner).exists())

    def test_user_only_sees_their_assigned_trainings(self):
        admin = Profile.objects.create(
            keycloak_id="keycloak-training-admin",
            username="training-admin",
            role=Profile.Role.ADMIN,
        )
        assigned_training = Training.objects.create(
            title="Formation attribuée",
            created_by=admin,
        )
        Training.objects.create(
            title="Formation non attribuée",
            created_by=admin,
        )
        TrainingAssignment.objects.create(
            profile=self.profile,
            training=assigned_training,
            assigned_by=admin,
        )
        self.authenticate_with_role(Profile.Role.LEARNER)

        response = self.client.get("/api/learner/trainings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["id"], assigned_training.pk)

    def test_learner_cannot_manage_users(self):
        self.authenticate_with_role(Profile.Role.LEARNER)

        self.assertEqual(
            self.client.get("/api/admin/users/").status_code,
            403,
        )
        self.assertEqual(
            self.client.put(
                f"/api/admin/users/{self.profile.pk}/trainings/",
                {"training_ids": []},
                format="json",
            ).status_code,
            403,
        )

    def test_last_admin_cannot_be_demoted(self):
        self.authenticate_with_role(Profile.Role.ADMIN)

        response = self.client.patch(
            f"/api/admin/users/{self.profile.pk}/role/",
            {"role": "learner"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.role, Profile.Role.ADMIN)


class AdminTrainingApiTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.client = APIClient()
        self.profile = Profile.objects.create(
            keycloak_id="keycloak-admin",
            username="admin-user",
            email="admin@example.test",
            role=Profile.Role.ADMIN,
        )
        self.user = KeycloakUser(
            id=self.profile.keycloak_id,
            username=self.profile.username,
            email=self.profile.email,
            roles=frozenset({Profile.Role.ADMIN}),
            claims={},
            profile=self.profile,
        )
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self.media_override.disable()
        self.media_directory.cleanup()

    def create_training(self):
        response = self.client.post(
            "/api/admin/trainings/",
            {
                "title": "Prendre la parole avec confiance",
                "description": "Sources et objectifs du parcours.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_admin_can_create_and_list_a_training(self):
        created = self.create_training()

        self.assertEqual(created["status"], "draft")
        self.assertEqual(created["objective_count"], 0)
        self.assertEqual(Training.objects.get().created_by, self.profile)

        response = self.client.get("/api/admin/trainings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["title"], created["title"])

    def test_admin_can_update_a_training_title(self):
        created = self.create_training()

        response = self.client.patch(
            f"/api/admin/trainings/{created['id']}/",
            {"title": "Nouveau titre de formation"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Nouveau titre de formation")
        self.assertEqual(
            Training.objects.get(pk=created["id"]).title,
            "Nouveau titre de formation",
        )

    def test_objectives_and_course_hierarchy_can_be_created(self):
        training = self.create_training()
        training_id = training["id"]
        objective_response = self.client.post(
            f"/api/admin/trainings/{training_id}/objectives/",
            {"title": "Structurer une intervention claire"},
            format="json",
        )
        self.assertEqual(objective_response.status_code, 201)
        objective_id = objective_response.json()["id"]

        module_response = self.client.post(
            f"/api/admin/trainings/{training_id}/units/",
            {
                "kind": "module",
                "working_title": "Fondamentaux",
                "objective_ids": [objective_id],
            },
            format="json",
        )
        self.assertEqual(module_response.status_code, 201)

        chapter_response = self.client.post(
            f"/api/admin/trainings/{training_id}/units/",
            {
                "kind": "chapter",
                "working_title": "Construire son message",
                "parent": module_response.json()["id"],
                "objective_ids": [objective_id],
            },
            format="json",
        )

        self.assertEqual(chapter_response.status_code, 201)
        self.assertEqual(CourseUnit.objects.count(), 2)
        self.assertEqual(chapter_response.json()["kind_label"], "Chapitre")

    def test_invalid_course_hierarchy_is_rejected(self):
        training_id = self.create_training()["id"]

        response = self.client.post(
            f"/api/admin/trainings/{training_id}/units/",
            {"kind": "section", "working_title": "Section isolée"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CourseUnit.objects.count(), 0)

    def test_text_structured_quiz_pdf_and_protected_download_are_supported(self):
        training_id = self.create_training()["id"]
        text_response = self.client.post(
            f"/api/admin/trainings/{training_id}/raw-materials/",
            {"kind": "text", "content": "Notes brutes de la formation"},
            format="json",
        )
        self.assertEqual(text_response.status_code, 201)

        quiz_response = self.client.post(
            f"/api/admin/trainings/{training_id}/raw-materials/",
            {
                "kind": "quiz",
                "quiz_data": {
                    "title": "",
                    "questions": [
                        {
                            "type": "single_choice",
                            "prompt": "Quel est votre objectif ?",
                            "options": [
                                {"text": "Comprendre", "is_correct": True},
                                {"text": "Ignorer", "is_correct": False},
                            ],
                        },
                        {
                            "type": "short_text",
                            "prompt": "Quel taux obtenez-vous ?",
                            "accepted_answers": ["1,1715"],
                        },
                    ],
                },
            },
            format="json",
        )
        self.assertEqual(quiz_response.status_code, 201)
        self.assertEqual(quiz_response.json()["content"], "")
        self.assertEqual(len(quiz_response.json()["quiz_data"]["questions"]), 2)
        self.assertEqual(quiz_response.json()["display_name"], "Quiz · 2 questions")

        pdf = SimpleUploadedFile(
            "support.pdf",
            b"%PDF-1.4 test",
            content_type="application/pdf",
        )
        pdf_response = self.client.post(
            f"/api/admin/trainings/{training_id}/raw-materials/",
            {"kind": "pdf", "file": pdf},
            format="multipart",
        )
        self.assertEqual(pdf_response.status_code, 201)
        self.assertTrue(pdf_response.json()["has_file"])

        download_response = self.client.get(pdf_response.json()["download_url"])
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response["Content-Type"], "application/pdf")

        preview_token_response = self.client.get(
            f"/api/admin/trainings/{training_id}/raw-materials/"
            f"{pdf_response.json()['id']}/preview-token/"
        )
        self.assertEqual(preview_token_response.status_code, 200)
        preview_response = APIClient().get(preview_token_response.json()["url"])
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response["Content-Type"], "application/pdf")
        self.assertTrue(preview_response["Content-Disposition"].startswith("inline;"))
        self.assertEqual(b"".join(preview_response.streaming_content), b"%PDF-1.4 test")
        self.assertEqual(RawMaterial.objects.count(), 3)

    def test_enrichment_requires_an_ai_configuration(self):
        training_id = self.create_training()["id"]
        self.client.post(
            f"/api/admin/trainings/{training_id}/raw-materials/",
            {"kind": "text", "content": "Contenu à analyser"},
            format="json",
        )

        with override_settings(OPENAI_API_KEY=""):
            response = self.client.post(
                f"/api/admin/trainings/{training_id}/enrichments/generate/",
                {},
                format="json",
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(RawMaterialEnrichment.objects.count(), 0)

    @override_settings(OPENAI_API_KEY="test-key")
    def test_enrichment_can_be_queued_and_is_exposed_in_training_detail(self):
        training_id = self.create_training()["id"]
        material_response = self.client.post(
            f"/api/admin/trainings/{training_id}/raw-materials/",
            {"kind": "text", "content": "Contenu à analyser"},
            format="json",
        )
        material_id = material_response.json()["id"]

        with patch("api.views.enqueue_training_enrichment") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    f"/api/admin/trainings/{training_id}/enrichments/generate/",
                    {},
                    format="json",
                )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"queued": 1, "total": 1})
        enqueue.assert_called_once_with(training_id)
        enrichment = RawMaterialEnrichment.objects.get(material_id=material_id)
        self.assertEqual(enrichment.status, RawMaterialEnrichment.Status.QUEUED)

        enrichment.status = RawMaterialEnrichment.Status.READY
        enrichment.media_purpose = "Présenter un concept"
        enrichment.key_concepts = [
            {"name": "Concept", "explanation": "Définition fondée sur la source"}
        ]
        enrichment.save()

        detail = self.client.get(f"/api/admin/trainings/{training_id}/").json()
        self.assertTrue(detail["enrichment_ai_configured"])
        self.assertEqual(
            detail["raw_materials"][0]["enrichment"]["status"],
            "ready",
        )
        self.assertEqual(
            detail["raw_materials"][0]["enrichment"]["media_purpose"],
            "Présenter un concept",
        )

    @override_settings(OPENAI_API_KEY="test-key")
    def test_enriched_materials_can_be_queued_for_structure_generation(self):
        training_id = self.create_training()["id"]
        self.client.post(
            f"/api/admin/trainings/{training_id}/objectives/",
            {"title": "Comprendre le marché des changes"},
            format="json",
        )
        material_response = self.client.post(
            f"/api/admin/trainings/{training_id}/raw-materials/",
            {"kind": "text", "content": "Contenu enrichi"},
            format="json",
        )
        RawMaterialEnrichment.objects.create(
            material_id=material_response.json()["id"],
            status=RawMaterialEnrichment.Status.READY,
            media_purpose="Présenter les bases",
            summary="Résumé fidèle",
            key_concepts=[{"name": "Change", "explanation": "Échange de devises"}],
        )

        with patch("api.views.enqueue_structure_generation") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    f"/api/admin/trainings/{training_id}/structure/generate/",
                    {},
                    format="json",
                )

        self.assertEqual(response.status_code, 202)
        generation = CourseStructureGeneration.objects.get(training_id=training_id)
        self.assertEqual(generation.status, CourseStructureGeneration.Status.QUEUED)
        enqueue.assert_called_once_with(generation.id)
        self.assertEqual(
            Training.objects.get(pk=training_id).status,
            Training.Status.STRUCTURING,
        )

        detail = self.client.get(f"/api/admin/trainings/{training_id}/").json()
        self.assertEqual(detail["structure_generation"]["status"], "queued")

    def test_ready_structure_can_be_validated_and_published(self):
        training_id = self.create_training()["id"]
        objective_response = self.client.post(
            f"/api/admin/trainings/{training_id}/objectives/",
            {"title": "Comprendre le marché des changes"},
            format="json",
        )
        material_response = self.client.post(
            f"/api/admin/trainings/{training_id}/raw-materials/",
            {"kind": "text", "content": "Contenu de référence"},
            format="json",
        )
        objective_id = objective_response.json()["id"]
        material_id = material_response.json()["id"]
        generation = CourseStructureGeneration.objects.create(
            training_id=training_id,
            status=CourseStructureGeneration.Status.READY,
            structure={
                "title": "Parcours sur les marchés des changes",
                "introduction": "Une progression fondée uniquement sur les sources disponibles.",
                "unsupported_objective_ids": [],
                "modules": [
                    {
                        "title": "Fondamentaux",
                        "rationale": "Installer les connaissances indispensables.",
                        "chapters": [
                            {
                                "title": "Comprendre le marché",
                                "rationale": "Présenter les notions avant leur application.",
                                "sections": [
                                    {
                                        "title": "Mécanismes essentiels",
                                        "rationale": "La source soutient directement cet objectif.",
                                        "objective_ids": [objective_id],
                                        "resource_ids": [material_id],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        )

        response = self.client.post(
            f"/api/admin/trainings/{training_id}/structure/publish/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], Training.Status.READY)
        self.assertEqual(response.json()["unit_count"], 3)
        self.assertIsNotNone(response.json()["structure_generation"]["published_at"])
        self.assertEqual(CourseUnit.objects.filter(training_id=training_id).count(), 3)
        section = CourseUnit.objects.get(
            training_id=training_id,
            kind=CourseUnit.Kind.SECTION,
        )
        self.assertEqual(section.parent.kind, CourseUnit.Kind.CHAPTER)
        self.assertEqual(list(section.objectives.values_list("id", flat=True)), [objective_id])
        self.assertEqual(list(section.raw_materials.values_list("id", flat=True)), [material_id])
        generation.refresh_from_db()
        self.assertEqual(generation.published_by, self.profile)
        self.assertIsNotNone(generation.published_at)

    def test_invalid_structure_cannot_be_published(self):
        training_id = self.create_training()["id"]
        self.client.post(
            f"/api/admin/trainings/{training_id}/objectives/",
            {"title": "Comprendre le marché des changes"},
            format="json",
        )
        self.client.post(
            f"/api/admin/trainings/{training_id}/raw-materials/",
            {"kind": "text", "content": "Contenu de référence"},
            format="json",
        )
        CourseStructureGeneration.objects.create(
            training_id=training_id,
            status=CourseStructureGeneration.Status.READY,
            structure={
                "title": "Structure invalide",
                "introduction": "Cette proposition omet volontairement les ressources disponibles.",
                "unsupported_objective_ids": [],
                "modules": [],
            },
        )

        response = self.client.post(
            f"/api/admin/trainings/{training_id}/structure/publish/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CourseUnit.objects.filter(training_id=training_id).count(), 0)
        self.assertEqual(
            Training.objects.get(pk=training_id).status,
            Training.Status.DRAFT,
        )

    def test_raw_quiz_content_is_rejected(self):
        training_id = self.create_training()["id"]

        response = self.client.post(
            f"/api/admin/trainings/{training_id}/raw-materials/",
            {"kind": "quiz", "content": "Q1. Question brute"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(RawMaterial.objects.count(), 0)

    def test_structured_quiz_can_be_updated(self):
        training_id = self.create_training()["id"]
        create_response = self.client.post(
            f"/api/admin/trainings/{training_id}/raw-materials/",
            {
                "kind": "quiz",
                "quiz_data": {
                    "title": "",
                    "questions": [
                        {
                            "type": "short_text",
                            "prompt": "Taux spot ?",
                            "accepted_answers": ["1,10"],
                        }
                    ],
                },
            },
            format="json",
        )

        material_id = create_response.json()["id"]
        response = self.client.patch(
            f"/api/admin/trainings/{training_id}/raw-materials/{material_id}/",
            {
                "quiz_data": {
                    "title": "Contrôle",
                    "questions": [
                        {
                            "type": "short_text",
                            "prompt": "Taux forward ?",
                            "accepted_answers": ["1,12"],
                        }
                    ],
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["display_name"], "Contrôle")
        self.assertEqual(response.json()["quiz_data"]["questions"][0]["prompt"], "Taux forward ?")

    def test_learner_cannot_access_training_administration(self):
        self.profile.role = Profile.Role.LEARNER
        self.profile.save(update_fields=["role", "updated_at"])

        response = self.client.get("/api/admin/trainings/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/admin/trainings/1/structure/publish/",
                {},
                format="json",
            ).status_code,
            403,
        )
