from types import SimpleNamespace

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    FirstName,
    NameDecision,
    NameSearch,
    NameSearchParticipant,
    Profile,
)


class NextFirstNameViewTests(APITestCase):
    def setUp(self):
        self.profile = Profile.objects.create(
            keycloak_id="keycloak-current-user-next-name",
            username="current-user-next-name",
            email="current-next-name@example.com",
        )
        self.other_profile = Profile.objects.create(
            keycloak_id="keycloak-other-user-next-name",
            username="other-user-next-name",
            email="other-next-name@example.com",
        )
        self.user = SimpleNamespace(
            is_authenticated=True,
            profile=self.profile,
        )
        self.client.force_authenticate(user=self.user)

        self.female_first_name = FirstName.objects.create(
            name="Emma",
            gender=FirstName.Gender.FEMALE,
            is_active=True,
        )
        self.male_first_name = FirstName.objects.create(
            name="Léo",
            gender=FirstName.Gender.MALE,
            is_active=True,
        )
        self.mixed_first_name = FirstName.objects.create(
            name="Camille",
            gender=FirstName.Gender.MIXED,
            is_active=True,
        )
        self.inactive_first_name = FirstName.objects.create(
            name="Alba",
            gender=FirstName.Gender.FEMALE,
            is_active=False,
        )

    def create_search(
        self,
        *,
        title="Recherche",
        creator=None,
        profile=None,
        role=NameSearchParticipant.Role.OWNER,
        invitation_status=(
            NameSearchParticipant.InvitationStatus.ACCEPTED
        ),
        genders=None,
    ):
        search_data = {
            "creator": creator or self.profile,
            "title": title,
        }
        if genders is not None:
            search_data["genders"] = genders

        search = NameSearch.objects.create(**search_data)
        participant = NameSearchParticipant.objects.create(
            search=search,
            profile=profile or self.profile,
            role=role,
            invitation_status=invitation_status,
        )
        return search, participant

    def test_route_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse(
                "next-first-name",
                kwargs={"search_id": 1},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_creating_search_saves_gender_filters(self):
        response = self.client.post(
            reverse("name-search-list-create"),
            {
                "title": "Fille ou prénom mixte",
                "genders": [
                    FirstName.Gender.FEMALE,
                    FirstName.Gender.MIXED,
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["genders"],
            [FirstName.Gender.FEMALE, FirstName.Gender.MIXED],
        )

        search = NameSearch.objects.get(id=response.data["id"])
        self.assertEqual(
            search.genders,
            [FirstName.Gender.FEMALE, FirstName.Gender.MIXED],
        )

    def test_creating_search_rejects_invalid_gender_filters(self):
        invalid_gender_lists = (
            [],
            ["unknown"],
        )

        for genders in invalid_gender_lists:
            with self.subTest(genders=genders):
                response = self.client.post(
                    reverse("name-search-list-create"),
                    {
                        "title": "Recherche invalide",
                        "genders": genders,
                    },
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn("genders", response.data)

    def test_default_filters_include_every_gender(self):
        search, _ = self.create_search()

        self.assertEqual(
            search.genders,
            [
                FirstName.Gender.FEMALE,
                FirstName.Gender.MALE,
                FirstName.Gender.MIXED,
            ],
        )

    def test_next_first_name_respects_each_gender_filter(self):
        first_names_by_gender = {
            FirstName.Gender.FEMALE: self.female_first_name,
            FirstName.Gender.MALE: self.male_first_name,
            FirstName.Gender.MIXED: self.mixed_first_name,
        }

        for gender, expected_first_name in first_names_by_gender.items():
            with self.subTest(gender=gender):
                search, _ = self.create_search(
                    title=f"Recherche {gender}",
                    genders=[gender],
                )

                response = self.client.get(
                    reverse(
                        "next-first-name",
                        kwargs={"search_id": search.id},
                    )
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )
                self.assertEqual(
                    response.data["id"],
                    expected_first_name.id,
                )

    def test_next_first_name_excludes_decided_and_inactive_names(self):
        search, participant = self.create_search(
            genders=[FirstName.Gender.FEMALE],
        )
        NameDecision.objects.create(
            participant=participant,
            first_name=self.female_first_name,
            choice=NameDecision.Choice.REJECTED,
        )

        response = self.client.get(
            reverse(
                "next-first-name",
                kwargs={"search_id": search.id},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertIsNone(response.data)

    def test_other_participant_decisions_do_not_hide_a_name(self):
        search, _ = self.create_search(
            creator=self.other_profile,
            role=NameSearchParticipant.Role.MEMBER,
            genders=[FirstName.Gender.FEMALE],
        )
        other_participant = NameSearchParticipant.objects.create(
            search=search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        NameDecision.objects.create(
            participant=other_participant,
            first_name=self.female_first_name,
            choice=NameDecision.Choice.REJECTED,
        )

        response = self.client.get(
            reverse(
                "next-first-name",
                kwargs={"search_id": search.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.female_first_name.id)

    def test_decisions_remain_isolated_between_searches(self):
        _, first_participant = self.create_search(
            title="Premier enfant",
            genders=[FirstName.Gender.FEMALE],
        )
        NameDecision.objects.create(
            participant=first_participant,
            first_name=self.female_first_name,
            choice=NameDecision.Choice.REJECTED,
        )

        second_search, _ = self.create_search(
            title="Deuxième enfant",
            genders=[FirstName.Gender.FEMALE],
        )

        response = self.client.get(
            reverse(
                "next-first-name",
                kwargs={"search_id": second_search.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.female_first_name.id)

    def test_pending_and_private_searches_are_hidden(self):
        pending_search, _ = self.create_search(
            title="Invitation en attente",
            creator=self.other_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.PENDING
            ),
        )
        private_search, _ = self.create_search(
            title="Recherche privée",
            creator=self.other_profile,
            profile=self.other_profile,
        )

        for search in (pending_search, private_search):
            with self.subTest(search=search.id):
                response = self.client.get(
                    reverse(
                        "next-first-name",
                        kwargs={"search_id": search.id},
                    )
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_404_NOT_FOUND,
                )