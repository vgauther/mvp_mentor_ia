from types import SimpleNamespace

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    NameSearch,
    NameSearchParticipant,
    Profile,
)


class SearchInvitationTests(APITestCase):
    def setUp(self):
        self.owner_profile = Profile.objects.create(
            keycloak_id="invitation-owner",
            username="invitation-owner",
            email="owner@example.com",
        )
        self.invited_profile = Profile.objects.create(
            keycloak_id="invitation-recipient",
            username="invitation-recipient",
            email="recipient@example.com",
        )
        self.other_profile = Profile.objects.create(
            keycloak_id="invitation-other",
            username="invitation-other",
            email="other@example.com",
        )

        self.authenticate(self.owner_profile)

        self.search = NameSearch.objects.create(
            creator=self.owner_profile,
            title="Notre recherche",
        )
        self.owner_participant = NameSearchParticipant.objects.create(
            search=self.search,
            profile=self.owner_profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

    def authenticate(self, profile):
        user = SimpleNamespace(
            is_authenticated=True,
            profile=profile,
        )
        self.client.force_authenticate(user=user)

    def invitation_create_url(self):
        return reverse(
            "search-invitation-create",
            kwargs={"search_id": self.search.id},
        )

    def create_invitation(
        self,
        *,
        profile=None,
        invitation_status=(
            NameSearchParticipant.InvitationStatus.PENDING
        ),
    ):
        return NameSearchParticipant.objects.create(
            search=self.search,
            profile=profile or self.invited_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=invitation_status,
        )

    def test_owner_can_invite_a_profile(self):
        response = self.client.post(
            self.invitation_create_url(),
            {"profile_id": self.invited_profile.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        invitation = NameSearchParticipant.objects.get(
            search=self.search,
            profile=self.invited_profile,
        )
        self.assertEqual(
            invitation.role,
            NameSearchParticipant.Role.MEMBER,
        )
        self.assertEqual(
            invitation.invitation_status,
            NameSearchParticipant.InvitationStatus.PENDING,
        )

    def test_user_cannot_invite_themselves(self):
        response = self.client.post(
            self.invitation_create_url(),
            {"profile_id": self.owner_profile.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_non_owner_cannot_invite_a_profile(self):
        NameSearchParticipant.objects.create(
            search=self.search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        self.authenticate(self.other_profile)

        response = self.client.post(
            self.invitation_create_url(),
            {"profile_id": self.invited_profile.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_duplicate_pending_invitation_is_rejected(self):
        self.create_invitation()

        response = self.client.post(
            self.invitation_create_url(),
            {"profile_id": self.invited_profile.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

    def test_declined_invitation_can_be_sent_again(self):
        invitation = self.create_invitation(
            invitation_status=(
                NameSearchParticipant.InvitationStatus.DECLINED
            ),
        )

        response = self.client.post(
            self.invitation_create_url(),
            {"profile_id": self.invited_profile.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        invitation.refresh_from_db()
        self.assertEqual(
            invitation.invitation_status,
            NameSearchParticipant.InvitationStatus.PENDING,
        )

    def test_search_cannot_have_two_guests(self):
        self.create_invitation(profile=self.other_profile)

        response = self.client.post(
            self.invitation_create_url(),
            {"profile_id": self.invited_profile.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

    def test_completed_search_cannot_send_invitation(self):
        self.search.status = NameSearch.Status.COMPLETED
        self.search.save(update_fields=("status", "updated_at"))

        response = self.client.post(
            self.invitation_create_url(),
            {"profile_id": self.invited_profile.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_user_only_sees_their_pending_invitations(self):
        expected_invitation = self.create_invitation()

        second_search = NameSearch.objects.create(
            creator=self.owner_profile,
            title="Autre recherche",
        )
        NameSearchParticipant.objects.create(
            search=second_search,
            profile=self.owner_profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        NameSearchParticipant.objects.create(
            search=second_search,
            profile=self.other_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.PENDING
            ),
        )

        self.authenticate(self.invited_profile)

        response = self.client.get(
            reverse("search-invitation-list"),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            expected_invitation.id,
        )
        self.assertEqual(
            response.data[0]["search"]["id"],
            self.search.id,
        )

    def test_recipient_can_accept_invitation(self):
        invitation = self.create_invitation()
        self.authenticate(self.invited_profile)

        response = self.client.patch(
            reverse(
                "search-invitation-response",
                kwargs={"invitation_id": invitation.id},
            ),
            {
                "invitation_status": (
                    NameSearchParticipant.InvitationStatus.ACCEPTED
                )
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        invitation.refresh_from_db()
        self.assertEqual(
            invitation.invitation_status,
            NameSearchParticipant.InvitationStatus.ACCEPTED,
        )

        searches_response = self.client.get(
            reverse("name-search-list-create"),
        )
        returned_search_ids = [
            search["id"] for search in searches_response.data
        ]
        self.assertIn(self.search.id, returned_search_ids)

    def test_recipient_can_decline_invitation(self):
        invitation = self.create_invitation()
        self.authenticate(self.invited_profile)

        response = self.client.patch(
            reverse(
                "search-invitation-response",
                kwargs={"invitation_id": invitation.id},
            ),
            {
                "invitation_status": (
                    NameSearchParticipant.InvitationStatus.DECLINED
                )
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        invitation.refresh_from_db()
        self.assertEqual(
            invitation.invitation_status,
            NameSearchParticipant.InvitationStatus.DECLINED,
        )

    def test_user_cannot_answer_another_users_invitation(self):
        invitation = self.create_invitation()
        self.authenticate(self.other_profile)

        response = self.client.patch(
            reverse(
                "search-invitation-response",
                kwargs={"invitation_id": invitation.id},
            ),
            {
                "invitation_status": (
                    NameSearchParticipant.InvitationStatus.ACCEPTED
                )
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_invitation_cannot_be_answered_twice(self):
        invitation = self.create_invitation()
        self.authenticate(self.invited_profile)

        response_url = reverse(
            "search-invitation-response",
            kwargs={"invitation_id": invitation.id},
        )

        first_response = self.client.patch(
            response_url,
            {
                "invitation_status": (
                    NameSearchParticipant.InvitationStatus.ACCEPTED
                )
            },
            format="json",
        )
        second_response = self.client.patch(
            response_url,
            {
                "invitation_status": (
                    NameSearchParticipant.InvitationStatus.DECLINED
                )
            },
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_409_CONFLICT,
        )