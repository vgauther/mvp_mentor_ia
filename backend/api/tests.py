from django.test import TestCase

from .authentication import get_or_sync_profile
from .models import Profile


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