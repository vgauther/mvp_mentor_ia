from types import SimpleNamespace

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    FirstName,
    NameSearch,
    NameSearchParticipant,
    Profile,
)


class NameSearchUpdateTests(APITestCase):
    def setUp(self):
        self.owner_profile = Profile.objects.create(
            keycloak_id="update-owner",
            username="update-owner",
            email="update-owner@example.com",
        )
        self.member_profile = Profile.objects.create(
            keycloak_id="update-member",
            username="update-member",
            email="update-member@example.com",
        )
        self.outsider_profile = Profile.objects.create(
            keycloak_id="update-outsider",
            username="update-outsider",
            email="update-outsider@example.com",
        )

        self.search = NameSearch.objects.create(
            creator=self.owner_profile,
            title="Notre recherche",
            genders=[FirstName.Gender.FEMALE],
        )
        NameSearchParticipant.objects.create(
            search=self.search,
            profile=self.owner_profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        NameSearchParticipant.objects.create(
            search=self.search,
            profile=self.member_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        self.authenticate(self.owner_profile)

    def authenticate(self, profile):
        user = SimpleNamespace(
            is_authenticated=True,
            profile=profile,
        )
        self.client.force_authenticate(user=user)

    def update_url(self):
        return reverse(
            "name-search-update",
            kwargs={"search_id": self.search.id},
        )

    def test_owner_can_update_title_and_genders(self):
        response = self.client.patch(
            self.update_url(),
            {
                "title": "Notre nouveau titre",
                "genders": [
                    FirstName.Gender.MALE,
                    FirstName.Gender.FEMALE,
                    FirstName.Gender.MALE,
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.search.refresh_from_db()
        self.assertEqual(self.search.title, "Notre nouveau titre")
        self.assertEqual(
            self.search.genders,
            [FirstName.Gender.MALE, FirstName.Gender.FEMALE],
        )
        self.assertEqual(response.data["title"], "Notre nouveau titre")
        self.assertEqual(
            response.data["genders"],
            [FirstName.Gender.MALE, FirstName.Gender.FEMALE],
        )

    def test_partial_update_can_change_only_title(self):
        response = self.client.patch(
            self.update_url(),
            {"title": "Titre uniquement"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.search.refresh_from_db()
        self.assertEqual(self.search.title, "Titre uniquement")
        self.assertEqual(
            self.search.genders,
            [FirstName.Gender.FEMALE],
        )

    def test_member_cannot_update_search(self):
        self.authenticate(self.member_profile)

        response = self.client.patch(
            self.update_url(),
            {"title": "Modification interdite"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.search.refresh_from_db()
        self.assertEqual(self.search.title, "Notre recherche")

    def test_outsider_cannot_update_search(self):
        self.authenticate(self.outsider_profile)

        response = self.client.patch(
            self.update_url(),
            {"title": "Modification interdite"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.patch(
            self.update_url(),
            {"title": "Modification interdite"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_blank_title_and_empty_genders_are_rejected(self):
        invalid_payloads = (
            {"title": ""},
            {"genders": []},
            {"genders": ["invalid"]},
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.patch(
                    self.update_url(),
                    payload,
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

        self.search.refresh_from_db()
        self.assertEqual(self.search.title, "Notre recherche")
        self.assertEqual(
            self.search.genders,
            [FirstName.Gender.FEMALE],
        )

    def test_read_only_fields_cannot_be_changed(self):
        response = self.client.patch(
            self.update_url(),
            {
                "status": NameSearch.Status.ARCHIVED,
                "creator": self.outsider_profile.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.search.refresh_from_db()
        self.assertEqual(self.search.status, NameSearch.Status.ACTIVE)
        self.assertEqual(self.search.creator, self.owner_profile)

    def test_route_only_accepts_patch(self):
        methods = (
            self.client.get,
            self.client.put,
            self.client.delete,
        )

        for method in methods:
            with self.subTest(method=method.__name__):
                response = method(
                    self.update_url(),
                    {},
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )