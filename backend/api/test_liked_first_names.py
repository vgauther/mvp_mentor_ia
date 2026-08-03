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


class LikedFirstNameTests(APITestCase):
    def setUp(self):
        self.owner_profile = Profile.objects.create(
            keycloak_id="liked-owner",
            username="liked-owner",
            email="liked-owner@example.com",
        )
        self.member_profile = Profile.objects.create(
            keycloak_id="liked-member",
            username="liked-member",
            email="liked-member@example.com",
        )
        self.outsider_profile = Profile.objects.create(
            keycloak_id="liked-outsider",
            username="liked-outsider",
            email="liked-outsider@example.com",
        )

        self.emma = FirstName.objects.create(
            name="Emma",
            gender=FirstName.Gender.FEMALE,
            origin="Germanique",
            meaning="Universelle",
            is_active=True,
        )
        self.jules = FirstName.objects.create(
            name="Jules",
            gender=FirstName.Gender.MALE,
            origin="Latine",
            meaning="Jeune",
            is_active=True,
        )
        self.alice = FirstName.objects.create(
            name="Alice",
            gender=FirstName.Gender.FEMALE,
            origin="Germanique",
            meaning="Noble",
            is_active=True,
        )
        self.inactive_first_name = FirstName.objects.create(
            name="Alba",
            gender=FirstName.Gender.FEMALE,
            origin="Latine",
            meaning="Aube",
            is_active=False,
        )

        self.authenticate(self.owner_profile)

    def authenticate(self, profile):
        user = SimpleNamespace(
            is_authenticated=True,
            profile=profile,
        )
        self.client.force_authenticate(user=user)

    def create_search(
        self,
        *,
        member_status=(
            NameSearchParticipant.InvitationStatus.ACCEPTED
        ),
    ):
        search = NameSearch.objects.create(
            creator=self.owner_profile,
            title="Notre recherche",
        )
        owner_participant = NameSearchParticipant.objects.create(
            search=search,
            profile=self.owner_profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        member_participant = None

        if member_status is not None:
            member_participant = NameSearchParticipant.objects.create(
                search=search,
                profile=self.member_profile,
                role=NameSearchParticipant.Role.MEMBER,
                invitation_status=member_status,
            )

        return search, owner_participant, member_participant

    def create_decision(
        self,
        participant,
        first_name,
        choice=NameDecision.Choice.LIKED,
    ):
        return NameDecision.objects.create(
            participant=participant,
            first_name=first_name,
            choice=choice,
        )

    def liked_url(self, search):
        return reverse(
            "search-liked-first-name-list",
            kwargs={"search_id": search.id},
        )

    def test_returns_names_liked_by_current_participant(self):
        search, owner_participant, _ = self.create_search()

        self.create_decision(owner_participant, self.emma)
        self.create_decision(
            owner_participant,
            self.jules,
            choice=NameDecision.Choice.REJECTED,
        )

        response = self.client.get(self.liked_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.emma.id)

    def test_does_not_return_names_liked_only_by_other_participant(self):
        search, _, member_participant = self.create_search()

        self.create_decision(member_participant, self.emma)

        response = self.client.get(self.liked_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_only_returns_decisions_from_requested_search(self):
        search, owner_participant, _ = self.create_search()
        other_search, other_owner, _ = self.create_search()

        self.create_decision(other_owner, self.emma)
        self.create_decision(owner_participant, self.jules)

        response = self.client.get(self.liked_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.jules.id)

        other_response = self.client.get(
            self.liked_url(other_search)
        )

        self.assertEqual(
            other_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(other_response.data), 1)
        self.assertEqual(
            other_response.data[0]["id"],
            self.emma.id,
        )

    def test_accepted_member_can_view_their_own_liked_names(self):
        search, owner_participant, member_participant = (
            self.create_search()
        )

        self.create_decision(owner_participant, self.emma)
        self.create_decision(member_participant, self.jules)

        self.authenticate(self.member_profile)

        response = self.client.get(self.liked_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.jules.id)

    def test_inactive_first_name_is_not_returned(self):
        search, owner_participant, _ = self.create_search()

        self.create_decision(
            owner_participant,
            self.inactive_first_name,
        )

        response = self.client.get(self.liked_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_liked_names_are_ordered_alphabetically(self):
        search, owner_participant, _ = self.create_search()

        self.create_decision(owner_participant, self.jules)
        self.create_decision(owner_participant, self.emma)
        self.create_decision(owner_participant, self.alice)

        response = self.client.get(self.liked_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [first_name["name"] for first_name in response.data],
            ["Alice", "Emma", "Jules"],
        )

    def test_outsider_cannot_view_liked_names(self):
        search, owner_participant, _ = self.create_search()

        self.create_decision(owner_participant, self.emma)
        self.authenticate(self.outsider_profile)

        response = self.client.get(self.liked_url(search))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_pending_participant_cannot_view_liked_names(self):
        search, _, pending_participant = self.create_search(
            member_status=(
                NameSearchParticipant.InvitationStatus.PENDING
            ),
        )

        self.create_decision(pending_participant, self.emma)
        self.authenticate(self.member_profile)

        response = self.client.get(self.liked_url(search))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_liked_name_route_requires_authentication(self):
        search, _, _ = self.create_search()

        self.client.force_authenticate(user=None)

        response = self.client.get(self.liked_url(search))

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )