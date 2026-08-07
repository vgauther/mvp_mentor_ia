from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class FirstNameOriginListViewTests(TestCase):
    def test_authenticated_user_can_list_first_name_origins(self):
        user = get_user_model().objects.create_user(
            username="origin-test-user",
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/first-name-origins/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 30)

        origins_by_id = {
            origin["id"]: origin
            for origin in response.data
        }

        self.assertIn("arabe", origins_by_id)
        self.assertEqual(
            origins_by_id["arabe"]["label"],
            "Arabe",
        )
        self.assertNotEqual(
            origins_by_id["arabe"]["description"],
            "",
        )
        self.assertEqual(
            set(origins_by_id["arabe"]),
            {
                "id",
                "label",
                "description",
            },
        )