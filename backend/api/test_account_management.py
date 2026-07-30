from types import SimpleNamespace

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Profile
from .serializers import CurrentProfileSerializer


class CurrentProfileSerializerTests(TestCase):
    def setUp(self):
        self.profile = Profile.objects.create(
            keycloak_id="keycloak-user-1",
            username="test-user",
            email="test-user@example.test",
        )

    def test_only_display_name_is_writable(self):
        serializer = CurrentProfileSerializer()

        self.assertFalse(
            serializer.fields["display_name"].read_only
        )
        self.assertTrue(serializer.fields["id"].read_only)
        self.assertTrue(serializer.fields["username"].read_only)
        self.assertTrue(serializer.fields["email"].read_only)
        self.assertTrue(serializer.fields["roles"].read_only)
        self.assertTrue(serializer.fields["created_at"].read_only)
        self.assertTrue(serializer.fields["updated_at"].read_only)
        self.assertNotIn("keycloak_id", serializer.fields)

    def test_rejects_fields_managed_by_keycloak(self):
        serializer = CurrentProfileSerializer(
            self.profile,
            data={
                "display_name": "Nouveau nom",
                "username": "modified-user",
                "email": "modified@example.test",
                "keycloak_id": "modified-keycloak-id",
            },
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)
        self.assertIn("email", serializer.errors)
        self.assertIn("keycloak_id", serializer.errors)

        self.profile.refresh_from_db()

        self.assertEqual(self.profile.display_name, "")
        self.assertEqual(self.profile.username, "test-user")
        self.assertEqual(
            self.profile.email,
            "test-user@example.test",
        )
        self.assertEqual(
            self.profile.keycloak_id,
            "keycloak-user-1",
        )


class AccountManagementViewTests(APITestCase):
    def setUp(self):
        self.profile = Profile.objects.create(
            keycloak_id="keycloak-current-user",
            username="current-user",
            email="current@example.com",
        )
        self.other_profile = Profile.objects.create(
            keycloak_id="keycloak-other-user",
            username="other-user",
            email="other@example.com",
            display_name="Autre utilisateur",
        )

        self.user = SimpleNamespace(
            id=self.profile.keycloak_id,
            username=self.profile.username,
            email=self.profile.email,
            roles=frozenset(
                {
                    "default-roles",
                    "parent",
                }
            ),
            is_authenticated=True,
            profile=self.profile,
        )

        self.client.force_authenticate(user=self.user)

    def test_me_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("me"))

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_me_returns_current_profile(self):
        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data),
            {
                "id",
                "username",
                "email",
                "display_name",
                "roles",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(response.data["id"], self.profile.id)
        self.assertEqual(
            response.data["username"],
            "current-user",
        )
        self.assertEqual(
            response.data["email"],
            "current@example.com",
        )
        self.assertEqual(
            response.data["roles"],
            [
                "default-roles",
                "parent",
            ],
        )
        self.assertNotIn("keycloak_id", response.data)

    def test_me_updates_display_name(self):
        response = self.client.patch(
            reverse("me"),
            {
                "display_name": "Victor",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()

        self.assertEqual(self.profile.display_name, "Victor")
        self.assertEqual(response.data["display_name"], "Victor")

    def test_me_rejects_managed_fields(self):
        response = self.client.patch(
            reverse("me"),
            {
                "display_name": "Nom refusé",
                "username": "modified-user",
                "email": "modified@example.com",
                "keycloak_id": "modified-keycloak-id",
                "roles": ["admin"],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("username", response.data)
        self.assertIn("email", response.data)
        self.assertIn("keycloak_id", response.data)
        self.assertIn("roles", response.data)

        self.profile.refresh_from_db()

        self.assertEqual(self.profile.display_name, "")
        self.assertEqual(self.profile.username, "current-user")
        self.assertEqual(
            self.profile.email,
            "current@example.com",
        )
        self.assertEqual(
            self.profile.keycloak_id,
            "keycloak-current-user",
        )

    def test_me_does_not_allow_complete_replacement(self):
        response = self.client.put(
            reverse("me"),
            {
                "display_name": "Victor",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_profile_lookup_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("profile-lookup"),
            {
                "email": "other@example.com",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_profile_lookup_is_exact_and_case_insensitive(self):
        response = self.client.get(
            reverse("profile-lookup"),
            {
                "email": "OTHER@EXAMPLE.COM",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.other_profile.id)
        self.assertEqual(
            response.data["username"],
            "other-user",
        )
        self.assertEqual(
            response.data["email"],
            "other@example.com",
        )
        self.assertEqual(
            response.data["display_name"],
            "Autre utilisateur",
        )
        self.assertNotIn("keycloak_id", response.data)

    def test_profile_lookup_requires_email(self):
        response = self.client.get(reverse("profile-lookup"))

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("email", response.data)

    def test_profile_lookup_rejects_partial_email(self):
        response = self.client.get(
            reverse("profile-lookup"),
            {
                "email": "other@example.fr",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )