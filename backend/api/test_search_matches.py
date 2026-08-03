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


class SearchMatchTests(APITestCase):
    def setUp(self):
        self.owner_profile = Profile.objects.create(
            keycloak_id="match-owner",
            username="match-owner",
            email="match-owner@example.com",
        )
        self.member_profile = Profile.objects.create(
            keycloak_id="match-member",
            username="match-member",
            email="match-member@example.com",
        )
        self.outsider_profile = Profile.objects.create(
            keycloak_id="match-outsider",
            username="match-outsider",
            email="match-outsider@example.com",
        )

        self.first_name = FirstName.objects.create(
            name="Emma",
            gender=FirstName.Gender.FEMALE,
            origin="Germanique",
            meaning="Universelle",
            is_active=True,
        )
        self.other_first_name = FirstName.objects.create(
            name="Jules",
            gender=FirstName.Gender.MALE,
            origin="Latine",
            meaning="Jeune",
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

    def matches_url(self, search):
        return reverse(
            "search-match-list",
            kwargs={"search_id": search.id},
        )

    def test_name_liked_by_both_participants_is_a_match(self):
        search, owner_participant, member_participant = (
            self.create_search()
        )

        self.create_decision(
            owner_participant,
            self.first_name,
        )
        self.create_decision(
            member_participant,
            self.first_name,
        )

        self.create_decision(
            owner_participant,
            self.other_first_name,
        )

        response = self.client.get(self.matches_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            self.first_name.id,
        )

    def test_rejected_name_is_not_a_match(self):
        search, owner_participant, member_participant = (
            self.create_search()
        )

        self.create_decision(
            owner_participant,
            self.first_name,
        )
        self.create_decision(
            member_participant,
            self.first_name,
            choice=NameDecision.Choice.REJECTED,
        )

        response = self.client.get(self.matches_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_matches_only_use_decisions_from_requested_search(self):
        search, owner_participant, member_participant = (
            self.create_search()
        )
        other_search, other_owner, other_member = self.create_search()

        self.create_decision(
            owner_participant,
            self.first_name,
        )
        self.create_decision(
            other_owner,
            self.first_name,
        )
        self.create_decision(
            other_member,
            self.first_name,
        )

        response = self.client.get(self.matches_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        other_response = self.client.get(
            self.matches_url(other_search)
        )

        self.assertEqual(
            other_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(other_response.data), 1)

    def test_search_without_second_participant_has_no_match(self):
        search, owner_participant, _ = self.create_search(
            member_status=None,
        )

        self.create_decision(
            owner_participant,
            self.first_name,
        )

        response = self.client.get(self.matches_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_pending_participant_does_not_create_match(self):
        search, owner_participant, pending_participant = (
            self.create_search(
                member_status=(
                    NameSearchParticipant.InvitationStatus.PENDING
                ),
            )
        )

        self.create_decision(
            owner_participant,
            self.first_name,
        )
        self.create_decision(
            pending_participant,
            self.first_name,
        )

        response = self.client.get(self.matches_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_outsider_cannot_view_matches(self):
        search, owner_participant, member_participant = (
            self.create_search()
        )

        self.create_decision(
            owner_participant,
            self.first_name,
        )
        self.create_decision(
            member_participant,
            self.first_name,
        )

        self.authenticate(self.outsider_profile)

        response = self.client.get(self.matches_url(search))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_pending_participant_cannot_view_matches(self):
        search, _, _ = self.create_search(
            member_status=(
                NameSearchParticipant.InvitationStatus.PENDING
            ),
        )

        self.authenticate(self.member_profile)

        response = self.client.get(self.matches_url(search))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_match_route_requires_authentication(self):
        search, _, _ = self.create_search()

        self.client.force_authenticate(user=None)

        response = self.client.get(self.matches_url(search))

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_inactive_first_name_is_not_returned_as_match(self):
        search, owner_participant, member_participant = (
            self.create_search()
        )

        self.create_decision(
            owner_participant,
            self.inactive_first_name,
        )
        self.create_decision(
            member_participant,
            self.inactive_first_name,
        )

        response = self.client.get(self.matches_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])