from types import SimpleNamespace

from django.db import connection
from django.test.utils import CaptureQueriesContext
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
        origins=None,
        min_length=None,
        max_length=None,
        first_letters=None,
    ):
        search_data = {
            "creator": creator or self.profile,
            "title": title,
        }
        if genders is not None:
            search_data["genders"] = genders
        if origins is not None:
            search_data["origins"] = origins
        if min_length is not None:
            search_data["min_length"] = min_length
        if max_length is not None:
            search_data["max_length"] = max_length
        if first_letters is not None:
            search_data["first_letters"] = first_letters

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

    def test_creating_search_saves_additional_filters(self):
        response = self.client.post(
            reverse("name-search-list-create"),
            {
                "title": "Filtres précis",
                "origins": ["latine", "grecque", "latine"],
                "min_length": 4,
                "max_length": 8,
                "first_letters": ["a", "E", "a"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["origins"], ["latine", "grecque"])
        self.assertEqual(response.data["min_length"], 4)
        self.assertEqual(response.data["max_length"], 8)
        self.assertEqual(response.data["first_letters"], ["A", "E"])

        search = NameSearch.objects.get(id=response.data["id"])
        self.assertEqual(search.origins, ["latine", "grecque"])
        self.assertEqual(search.min_length, 4)
        self.assertEqual(search.max_length, 8)
        self.assertEqual(search.first_letters, ["A", "E"])

    def test_creating_search_rejects_invalid_additional_filters(self):
        invalid_payloads = (
            {"origins": ["unknown"]},
            {"min_length": 0},
            {"max_length": 101},
            {"min_length": 8, "max_length": 4},
            {"first_letters": ["É"]},
            {"first_letters": ["AB"]},
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    reverse("name-search-list-create"),
                    {
                        "title": "Recherche invalide",
                        **payload,
                    },
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

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
        self.assertEqual(search.origins, [])
        self.assertIsNone(search.min_length)
        self.assertIsNone(search.max_length)
        self.assertEqual(search.first_letters, [])

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

    def test_next_first_name_respects_origin_filter(self):
        expected_first_name = FirstName.objects.create(
            name="Flora",
            gender=FirstName.Gender.FEMALE,
            origin="latine",
        )
        FirstName.objects.create(
            name="Freya",
            gender=FirstName.Gender.FEMALE,
            origin="nordique_balte",
        )
        search, _ = self.create_search(
            genders=[FirstName.Gender.FEMALE],
            origins=["latine"],
        )

        response = self.client.get(
            reverse("next-first-name", kwargs={"search_id": search.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], expected_first_name.id)

    def test_next_first_name_balances_selected_origins(self):
        french_first_name = FirstName.objects.create(
            name="Fleur",
            gender=FirstName.Gender.FEMALE,
            origin="francaise",
        )
        arabic_first_names = [
            FirstName.objects.create(
                name=name,
                gender=FirstName.Gender.FEMALE,
                origin="arabe",
            )
            for name in ("Aya", "Inaya", "Yasmine")
        ]
        search, participant = self.create_search(
            genders=[FirstName.Gender.FEMALE],
            origins=["francaise", "arabe"],
        )

        first_response = self.client.get(
            reverse("next-first-name", kwargs={"search_id": search.id})
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.data["id"], french_first_name.id)

        NameDecision.objects.create(
            participant=participant,
            first_name=french_first_name,
            choice=NameDecision.Choice.REJECTED,
        )

        second_response = self.client.get(
            reverse("next-first-name", kwargs={"search_id": search.id})
        )

        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertIn(
            second_response.data["id"],
            [first_name.id for first_name in arabic_first_names],
        )

    def test_origin_balance_uses_previous_decisions(self):
        french_first_name = FirstName.objects.create(
            name="Fleur",
            gender=FirstName.Gender.FEMALE,
            origin="francaise",
        )
        arabic_first_name = FirstName.objects.create(
            name="Aya",
            gender=FirstName.Gender.FEMALE,
            origin="arabe",
        )
        search, participant = self.create_search(
            genders=[FirstName.Gender.FEMALE],
            origins=["francaise", "arabe"],
        )
        already_decided_french_name = FirstName.objects.create(
            name="Garance",
            gender=FirstName.Gender.FEMALE,
            origin="francaise",
        )
        NameDecision.objects.create(
            participant=participant,
            first_name=already_decided_french_name,
            choice=NameDecision.Choice.REJECTED,
        )

        response = self.client.get(
            reverse("next-first-name", kwargs={"search_id": search.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], arabic_first_name.id)
        self.assertNotEqual(response.data["id"], french_first_name.id)

    def test_origin_balance_restarts_after_filters_are_updated(self):
        french_first_name = FirstName.objects.create(
            name="Fleur",
            gender=FirstName.Gender.FEMALE,
            origin="francaise",
        )
        italian_first_name = FirstName.objects.create(
            name="Giulia",
            gender=FirstName.Gender.FEMALE,
            origin="italienne",
        )
        hispanic_first_name = FirstName.objects.create(
            name="Ines",
            gender=FirstName.Gender.FEMALE,
            origin="hispanique",
        )
        lusophone_first_name = FirstName.objects.create(
            name="Beatriz",
            gender=FirstName.Gender.FEMALE,
            origin="lusophone",
        )
        search, participant = self.create_search(
            genders=[FirstName.Gender.FEMALE],
            origins=["francaise", "italienne", "hispanique"],
        )

        for index in range(3):
            decided_french_name = FirstName.objects.create(
                name=f"AncienFrancais{index}",
                gender=FirstName.Gender.FEMALE,
                origin="francaise",
            )
            NameDecision.objects.create(
                participant=participant,
                first_name=decided_french_name,
                choice=NameDecision.Choice.REJECTED,
            )

        response = self.client.patch(
            reverse(
                "name-search-update",
                kwargs={"search_id": search.id},
            ),
            {
                "origins": [
                    "francaise",
                    "italienne",
                    "hispanique",
                    "lusophone",
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for expected_first_name in (
            french_first_name,
            italian_first_name,
            hispanic_first_name,
            lusophone_first_name,
        ):
            response = self.client.get(
                reverse(
                    "next-first-name",
                    kwargs={"search_id": search.id},
                )
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["id"], expected_first_name.id)

            NameDecision.objects.create(
                participant=participant,
                first_name=expected_first_name,
                choice=NameDecision.Choice.REJECTED,
            )

    def test_origin_balance_falls_back_when_an_origin_is_exhausted(self):
        french_first_name = FirstName.objects.create(
            name="Fleur",
            gender=FirstName.Gender.FEMALE,
            origin="francaise",
        )
        arabic_first_name = FirstName.objects.create(
            name="Aya",
            gender=FirstName.Gender.FEMALE,
            origin="arabe",
        )
        search, participant = self.create_search(
            genders=[FirstName.Gender.FEMALE],
            origins=["francaise", "arabe"],
        )
        NameDecision.objects.create(
            participant=participant,
            first_name=french_first_name,
            choice=NameDecision.Choice.REJECTED,
        )

        response = self.client.get(
            reverse("next-first-name", kwargs={"search_id": search.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], arabic_first_name.id)

    def test_partner_priority_remains_stronger_than_origin_balance(self):
        french_first_name = FirstName.objects.create(
            name="Fleur",
            gender=FirstName.Gender.FEMALE,
            origin="francaise",
        )
        partner_liked_arabic_name = FirstName.objects.create(
            name="Aya",
            gender=FirstName.Gender.FEMALE,
            origin="arabe",
        )
        search, participant = self.create_search(
            genders=[FirstName.Gender.FEMALE],
            origins=["francaise", "arabe"],
        )
        partner = NameSearchParticipant.objects.create(
            search=search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        already_decided_arabic_name = FirstName.objects.create(
            name="Inaya",
            gender=FirstName.Gender.FEMALE,
            origin="arabe",
        )
        NameDecision.objects.create(
            participant=participant,
            first_name=already_decided_arabic_name,
            choice=NameDecision.Choice.REJECTED,
        )
        NameDecision.objects.create(
            participant=partner,
            first_name=partner_liked_arabic_name,
            choice=NameDecision.Choice.LIKED,
        )

        response = self.client.get(
            reverse("next-first-name", kwargs={"search_id": search.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], partner_liked_arabic_name.id)
        self.assertNotEqual(response.data["id"], french_first_name.id)

    def test_next_first_name_respects_length_range(self):
        expected_first_name = FirstName.objects.create(
            name="Louise",
            gender=FirstName.Gender.FEMALE,
        )
        search, _ = self.create_search(
            genders=[FirstName.Gender.FEMALE],
            min_length=6,
            max_length=6,
        )

        response = self.client.get(
            reverse("next-first-name", kwargs={"search_id": search.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], expected_first_name.id)

    def test_first_letter_filter_includes_accented_variants(self):
        expected_first_name = FirstName.objects.create(
            name="Élodie",
            gender=FirstName.Gender.FEMALE,
            origin="francaise",
        )
        search, _ = self.create_search(
            genders=[FirstName.Gender.FEMALE],
            origins=["francaise"],
            first_letters=["E"],
        )

        response = self.client.get(
            reverse("next-first-name", kwargs={"search_id": search.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], expected_first_name.id)

    def test_next_first_name_combines_all_filters(self):
        expected_first_name = FirstName.objects.create(
            name="Amalia",
            gender=FirstName.Gender.FEMALE,
            origin="germanique",
        )
        FirstName.objects.create(
            name="Amélia",
            gender=FirstName.Gender.FEMALE,
            origin="latine",
        )
        search, _ = self.create_search(
            genders=[FirstName.Gender.FEMALE],
            origins=["germanique"],
            min_length=6,
            max_length=6,
            first_letters=["A"],
        )

        response = self.client.get(
            reverse("next-first-name", kwargs={"search_id": search.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], expected_first_name.id)

    def test_next_first_name_uses_random_database_order(self):
        search, _ = self.create_search()

        with CaptureQueriesContext(connection) as captured_queries:
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

        executed_sql = " ".join(
            query["sql"].upper()
            for query in captured_queries.captured_queries
        )

        self.assertRegex(
            executed_sql,
            r"ORDER BY (?:RANDOM|RAND)\(\)",
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

    def test_first_turn_prefers_a_normal_name_over_a_partner_liked_name(self):
        search, _ = self.create_search(
            genders=[FirstName.Gender.FEMALE],
        )
        partner = NameSearchParticipant.objects.create(
            search=search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        normal_candidate = FirstName.objects.create(
            name="Louise",
            gender=FirstName.Gender.FEMALE,
        )
        NameDecision.objects.create(
            participant=partner,
            first_name=self.female_first_name,
            choice=NameDecision.Choice.LIKED,
        )

        response = self.client.get(
            reverse(
                "next-first-name",
                kwargs={"search_id": search.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], normal_candidate.id)

    def test_every_second_turn_prioritizes_a_name_liked_by_partner(self):
        search, participant = self.create_search(
            genders=[FirstName.Gender.FEMALE],
        )
        partner = NameSearchParticipant.objects.create(
            search=search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        already_decided = FirstName.objects.create(
            name="Alice",
            gender=FirstName.Gender.FEMALE,
        )
        normal_candidate = FirstName.objects.create(
            name="Louise",
            gender=FirstName.Gender.FEMALE,
        )
        NameDecision.objects.create(
            participant=participant,
            first_name=already_decided,
            choice=NameDecision.Choice.REJECTED,
        )
        NameDecision.objects.create(
            participant=partner,
            first_name=self.female_first_name,
            choice=NameDecision.Choice.LIKED,
        )

        response = self.client.get(
            reverse(
                "next-first-name",
                kwargs={"search_id": search.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.female_first_name.id)
        self.assertNotEqual(response.data["id"], normal_candidate.id)

    def test_partner_priority_falls_back_to_normal_candidates(self):
        search, participant = self.create_search(
            genders=[FirstName.Gender.FEMALE],
        )
        partner = NameSearchParticipant.objects.create(
            search=search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        NameDecision.objects.create(
            participant=participant,
            first_name=self.mixed_first_name,
            choice=NameDecision.Choice.REJECTED,
        )
        NameDecision.objects.create(
            participant=partner,
            first_name=self.male_first_name,
            choice=NameDecision.Choice.LIKED,
        )

        response = self.client.get(
            reverse(
                "next-first-name",
                kwargs={"search_id": search.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.female_first_name.id)

    def test_partner_priority_excludes_names_already_decided(self):
        search, participant = self.create_search(
            genders=[FirstName.Gender.FEMALE],
        )
        partner = NameSearchParticipant.objects.create(
            search=search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        remaining_first_name = FirstName.objects.create(
            name="Louise",
            gender=FirstName.Gender.FEMALE,
        )
        NameDecision.objects.create(
            participant=participant,
            first_name=self.female_first_name,
            choice=NameDecision.Choice.REJECTED,
        )
        NameDecision.objects.create(
            participant=partner,
            first_name=self.female_first_name,
            choice=NameDecision.Choice.LIKED,
        )

        response = self.client.get(
            reverse(
                "next-first-name",
                kwargs={"search_id": search.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], remaining_first_name.id)

    def test_normal_turn_uses_partner_liked_name_when_nothing_else_remains(self):
        search, _ = self.create_search(
            genders=[FirstName.Gender.FEMALE],
        )
        partner = NameSearchParticipant.objects.create(
            search=search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        NameDecision.objects.create(
            participant=partner,
            first_name=self.female_first_name,
            choice=NameDecision.Choice.LIKED,
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
