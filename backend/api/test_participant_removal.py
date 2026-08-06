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


class SearchParticipantRemovalTests(APITestCase):
    def setUp(self):
        self.owner_profile = Profile.objects.create(
            keycloak_id="removal-owner",
            username="removal-owner",
            email="removal-owner@example.com",
        )
        self.member_profile = Profile.objects.create(
            keycloak_id="removal-member",
            username="removal-member",
            email="removal-member@example.com",
        )
        self.outsider_profile = Profile.objects.create(
            keycloak_id="removal-outsider",
            username="removal-outsider",
            email="removal-outsider@example.com",
        )

        self.search = NameSearch.objects.create(
            creator=self.owner_profile,
            title="Notre recherche",
            genders=[FirstName.Gender.FEMALE],
        )
        self.owner_participant = NameSearchParticipant.objects.create(
            search=self.search,
            profile=self.owner_profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        self.first_name = FirstName.objects.create(
            name="Emma",
            gender=FirstName.Gender.FEMALE,
            is_active=True,
        )

        self.authenticate(self.owner_profile)

    def authenticate(self, profile):
        user = SimpleNamespace(
            is_authenticated=True,
            profile=profile,
        )
        self.client.force_authenticate(user=user)

    def create_member(
        self,
        *,
        invitation_status=(
            NameSearchParticipant.InvitationStatus.ACCEPTED
        ),
    ):
        return NameSearchParticipant.objects.create(
            search=self.search,
            profile=self.member_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=invitation_status,
        )

    def removal_url(self, participant):
        return reverse(
            "search-participant-removal",
            kwargs={
                "search_id": self.search.id,
                "participant_id": participant.id,
            },
        )

    def leave_url(self):
        return reverse(
            "search-participant-leave",
            kwargs={"search_id": self.search.id},
        )

    def test_owner_can_cancel_pending_invitation(self):
        participant = self.create_member(
            invitation_status=(
                NameSearchParticipant.InvitationStatus.PENDING
            ),
        )

        response = self.client.delete(self.removal_url(participant))

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            NameSearchParticipant.objects.filter(id=participant.id).exists()
        )

    def test_owner_can_remove_accepted_member_and_their_decisions(self):
        participant = self.create_member()
        decision = NameDecision.objects.create(
            participant=participant,
            first_name=self.first_name,
            choice=NameDecision.Choice.LIKED,
        )

        response = self.client.delete(self.removal_url(participant))

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            NameSearchParticipant.objects.filter(id=participant.id).exists()
        )
        self.assertFalse(
            NameDecision.objects.filter(id=decision.id).exists()
        )

    def test_removed_profile_can_be_invited_again(self):
        participant = self.create_member()
        self.client.delete(self.removal_url(participant))

        response = self.client.post(
            reverse(
                "search-invitation-create",
                kwargs={"search_id": self.search.id},
            ),
            {"profile_id": self.member_profile.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        invitation = NameSearchParticipant.objects.get(
            search=self.search,
            profile=self.member_profile,
        )
        self.assertEqual(
            invitation.invitation_status,
            NameSearchParticipant.InvitationStatus.PENDING,
        )

    def test_accepted_member_can_leave_and_their_decisions_are_deleted(self):
        participant = self.create_member()
        decision = NameDecision.objects.create(
            participant=participant,
            first_name=self.first_name,
            choice=NameDecision.Choice.LIKED,
        )
        self.authenticate(self.member_profile)

        response = self.client.delete(self.leave_url())

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            NameSearchParticipant.objects.filter(id=participant.id).exists()
        )
        self.assertFalse(
            NameDecision.objects.filter(id=decision.id).exists()
        )

    def test_pending_recipient_cannot_use_leave_route(self):
        participant = self.create_member(
            invitation_status=(
                NameSearchParticipant.InvitationStatus.PENDING
            ),
        )
        self.authenticate(self.member_profile)

        response = self.client.delete(self.leave_url())

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(
            NameSearchParticipant.objects.filter(id=participant.id).exists()
        )

    def test_owner_cannot_leave_their_own_search(self):
        response = self.client.delete(self.leave_url())

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(
            NameSearchParticipant.objects.filter(
                id=self.owner_participant.id
            ).exists()
        )

    def test_member_cannot_remove_a_participant(self):
        participant = self.create_member()
        self.authenticate(self.member_profile)

        response = self.client.delete(self.removal_url(participant))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(
            NameSearchParticipant.objects.filter(id=participant.id).exists()
        )

    def test_outsider_cannot_remove_a_participant(self):
        participant = self.create_member()
        self.authenticate(self.outsider_profile)

        response = self.client.delete(self.removal_url(participant))

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(
            NameSearchParticipant.objects.filter(id=participant.id).exists()
        )

    def test_owner_cannot_remove_themselves(self):
        response = self.client.delete(
            self.removal_url(self.owner_participant)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(
            NameSearchParticipant.objects.filter(
                id=self.owner_participant.id
            ).exists()
        )

    def test_removal_requires_authentication(self):
        participant = self.create_member()
        self.client.force_authenticate(user=None)

        response = self.client.delete(self.removal_url(participant))

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertTrue(
            NameSearchParticipant.objects.filter(id=participant.id).exists()
        )

    def test_routes_only_accept_delete(self):
        participant = self.create_member()
        routes = (
            self.removal_url(participant),
            self.leave_url(),
        )
        methods = (
            self.client.get,
            self.client.post,
            self.client.patch,
            self.client.put,
        )

        for route in routes:
            for method in methods:
                with self.subTest(route=route, method=method.__name__):
                    response = method(route, {}, format="json")

                    self.assertEqual(
                        response.status_code,
                        status.HTTP_405_METHOD_NOT_ALLOWED,
                    )