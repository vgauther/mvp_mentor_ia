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

class BusinessViewTests(APITestCase):
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
        )

        self.user = SimpleNamespace(
            is_authenticated=True,
            profile=self.profile,
        )
        self.client.force_authenticate(user=self.user)

        self.active_first_name = FirstName.objects.create(
            name="Emma",
            gender=FirstName.Gender.FEMALE,
            origin="Germanique",
            meaning="Universelle",
            is_active=True,
        )
        self.inactive_first_name = FirstName.objects.create(
            name="Alba",
            gender=FirstName.Gender.FEMALE,
            origin="Latine",
            meaning="Aube",
            is_active=False,
        )

    def test_business_routes_require_authentication(self):
        self.client.force_authenticate(user=None)

        first_names_response = self.client.get(
            reverse("first-name-list")
        )
        searches_response = self.client.get(
            reverse("name-search-list-create")
        )

        self.assertEqual(
            first_names_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            searches_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_first_name_list_only_returns_active_names(self):
        response = self.client.get(reverse("first-name-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            self.active_first_name.id,
        )
        self.assertEqual(response.data[0]["name"], "Emma")

    def test_search_list_only_returns_accepted_searches(self):
        accepted_search = NameSearch.objects.create(
            creator=self.other_profile,
            title="Recherche acceptée",
        )
        NameSearchParticipant.objects.create(
            search=accepted_search,
            profile=self.profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        pending_search = NameSearch.objects.create(
            creator=self.other_profile,
            title="Invitation en attente",
        )
        NameSearchParticipant.objects.create(
            search=pending_search,
            profile=self.profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.PENDING
            ),
        )

        private_search = NameSearch.objects.create(
            creator=self.other_profile,
            title="Recherche d’un autre utilisateur",
        )
        NameSearchParticipant.objects.create(
            search=private_search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        response = self.client.get(
            reverse("name-search-list-create")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [search["id"] for search in response.data],
            [accepted_search.id],
        )

    def test_creating_search_assigns_authenticated_profile(self):
        response = self.client.post(
            reverse("name-search-list-create"),
            {
                "title": "Notre recherche",
                "creator": self.other_profile.id,
                "status": NameSearch.Status.ARCHIVED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        search = NameSearch.objects.get(id=response.data["id"])
        self.assertEqual(search.creator, self.profile)
        self.assertEqual(search.status, NameSearch.Status.ACTIVE)

        participant = NameSearchParticipant.objects.get(
            search=search,
            profile=self.profile,
        )
        self.assertEqual(
            participant.role,
            NameSearchParticipant.Role.OWNER,
        )
        self.assertEqual(
            participant.invitation_status,
            NameSearchParticipant.InvitationStatus.ACCEPTED,
        )

    def test_creating_search_rejects_blank_title(self):
        response = self.client.post(
            reverse("name-search-list-create"),
            {"title": ""},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)
        self.assertEqual(NameSearch.objects.count(), 0)

    def test_decision_list_only_returns_current_participant_decisions(self):
        search = NameSearch.objects.create(
            creator=self.profile,
            title="Recherche commune",
        )
        participant = NameSearchParticipant.objects.create(
            search=search,
            profile=self.profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        other_participant = NameSearchParticipant.objects.create(
            search=search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        own_decision = NameDecision.objects.create(
            participant=participant,
            first_name=self.active_first_name,
            choice=NameDecision.Choice.LIKED,
        )
        NameDecision.objects.create(
            participant=other_participant,
            first_name=self.active_first_name,
            choice=NameDecision.Choice.REJECTED,
        )

        response = self.client.get(
            reverse(
                "name-decision-list-create",
                kwargs={"search_id": search.id},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], own_decision.id)

    def test_creating_decision_assigns_current_participant(self):
        search = NameSearch.objects.create(
            creator=self.other_profile,
            title="Recherche partagée",
        )
        other_participant = NameSearchParticipant.objects.create(
            search=search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        participant = NameSearchParticipant.objects.create(
            search=search,
            profile=self.profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        response = self.client.post(
            reverse(
                "name-decision-list-create",
                kwargs={"search_id": search.id},
            ),
            {
                "participant": other_participant.id,
                "first_name_id": self.active_first_name.id,
                "choice": NameDecision.Choice.LIKED,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        decision = NameDecision.objects.get(
            first_name=self.active_first_name,
        )
        self.assertEqual(decision.participant, participant)
        self.assertEqual(decision.choice, NameDecision.Choice.LIKED)

    def test_posting_existing_decision_updates_it(self):
        search = NameSearch.objects.create(
            creator=self.profile,
            title="Recherche à modifier",
        )
        participant = NameSearchParticipant.objects.create(
            search=search,
            profile=self.profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        decision = NameDecision.objects.create(
            participant=participant,
            first_name=self.active_first_name,
            choice=NameDecision.Choice.LIKED,
        )

        response = self.client.post(
            reverse(
                "name-decision-list-create",
                kwargs={"search_id": search.id},
            ),
            {
                "first_name_id": self.active_first_name.id,
                "choice": NameDecision.Choice.REJECTED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        decision.refresh_from_db()
        self.assertEqual(decision.choice, NameDecision.Choice.REJECTED)
        self.assertEqual(NameDecision.objects.count(), 1)

    def test_decision_route_hides_inaccessible_searches(self):
        pending_search = NameSearch.objects.create(
            creator=self.other_profile,
            title="Invitation en attente",
        )
        NameSearchParticipant.objects.create(
            search=pending_search,
            profile=self.profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.PENDING
            ),
        )

        private_search = NameSearch.objects.create(
            creator=self.other_profile,
            title="Recherche privée",
        )
        NameSearchParticipant.objects.create(
            search=private_search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        pending_response = self.client.get(
            reverse(
                "name-decision-list-create",
                kwargs={"search_id": pending_search.id},
            )
        )
        private_response = self.client.get(
            reverse(
                "name-decision-list-create",
                kwargs={"search_id": private_search.id},
            )
        )

        self.assertEqual(
            pending_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            private_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_creating_decision_rejects_invalid_choice(self):
        search = NameSearch.objects.create(
            creator=self.profile,
            title="Recherche avec choix invalide",
        )
        NameSearchParticipant.objects.create(
            search=search,
            profile=self.profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        response = self.client.post(
            reverse(
                "name-decision-list-create",
                kwargs={"search_id": search.id},
            ),
            {
                "first_name_id": self.active_first_name.id,
                "choice": "invalid",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("choice", response.data)
        self.assertEqual(NameDecision.objects.count(), 0)
