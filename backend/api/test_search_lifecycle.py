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


class SearchLifecycleTests(APITestCase):
    def setUp(self):
        self.owner_profile = Profile.objects.create(
            keycloak_id="lifecycle-owner",
            username="lifecycle-owner",
            email="lifecycle-owner@example.com",
        )
        self.member_profile = Profile.objects.create(
            keycloak_id="lifecycle-member",
            username="lifecycle-member",
            email="lifecycle-member@example.com",
        )
        self.outsider_profile = Profile.objects.create(
            keycloak_id="lifecycle-outsider",
            username="lifecycle-outsider",
            email="lifecycle-outsider@example.com",
        )

        self.first_name = FirstName.objects.create(
            name="Emma",
            gender=FirstName.Gender.FEMALE,
            origin="Germanique",
            meaning="Universelle",
            is_active=True,
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
        search_status=NameSearch.Status.ACTIVE,
        member_status=(
            NameSearchParticipant.InvitationStatus.ACCEPTED
        ),
    ):
        search = NameSearch.objects.create(
            creator=self.owner_profile,
            title="Notre recherche",
            status=search_status,
            genders=[FirstName.Gender.FEMALE],
        )

        owner_participant = NameSearchParticipant.objects.create(
            search=search,
            profile=self.owner_profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        member_participant = NameSearchParticipant.objects.create(
            search=search,
            profile=self.member_profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=member_status,
        )

        return search, owner_participant, member_participant

    def status_url(self, search):
        return reverse(
            "search-status-update",
            kwargs={"search_id": search.id},
        )

    def next_first_name_url(self, search):
        return reverse(
            "next-first-name",
            kwargs={"search_id": search.id},
        )

    def decisions_url(self, search):
        return reverse(
            "name-decision-list-create",
            kwargs={"search_id": search.id},
        )

    def invitation_url(self, invitation):
        return reverse(
            "search-invitation-response",
            kwargs={"invitation_id": invitation.id},
        )

    def update_status(self, search, new_status):
        return self.client.patch(
            self.status_url(search),
            {"status": new_status},
            format="json",
        )

    def test_owner_can_complete_active_search(self):
        search, _, _ = self.create_search()

        response = self.update_status(
            search,
            NameSearch.Status.COMPLETED,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        search.refresh_from_db()
        self.assertEqual(search.status, NameSearch.Status.COMPLETED)

    def test_owner_can_reopen_completed_search(self):
        search, _, _ = self.create_search(
            search_status=NameSearch.Status.COMPLETED,
        )

        response = self.update_status(
            search,
            NameSearch.Status.ACTIVE,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        search.refresh_from_db()
        self.assertEqual(search.status, NameSearch.Status.ACTIVE)

    def test_owner_can_archive_completed_search(self):
        search, _, _ = self.create_search(
            search_status=NameSearch.Status.COMPLETED,
        )

        response = self.update_status(
            search,
            NameSearch.Status.ARCHIVED,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        search.refresh_from_db()
        self.assertEqual(search.status, NameSearch.Status.ARCHIVED)

    def test_owner_can_unarchive_search(self):
        search, _, _ = self.create_search(
            search_status=NameSearch.Status.ARCHIVED,
        )

        response = self.update_status(
            search,
            NameSearch.Status.COMPLETED,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        search.refresh_from_db()
        self.assertEqual(search.status, NameSearch.Status.COMPLETED)

    def test_active_search_cannot_be_archived_directly(self):
        search, _, _ = self.create_search()

        response = self.update_status(
            search,
            NameSearch.Status.ARCHIVED,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        search.refresh_from_db()
        self.assertEqual(search.status, NameSearch.Status.ACTIVE)

    def test_archived_search_cannot_be_reopened_directly(self):
        search, _, _ = self.create_search(
            search_status=NameSearch.Status.ARCHIVED,
        )

        response = self.update_status(
            search,
            NameSearch.Status.ACTIVE,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

        search.refresh_from_db()
        self.assertEqual(search.status, NameSearch.Status.ARCHIVED)

    def test_setting_current_status_is_idempotent(self):
        search, _, _ = self.create_search()

        response = self.update_status(
            search,
            NameSearch.Status.ACTIVE,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        search.refresh_from_db()
        self.assertEqual(search.status, NameSearch.Status.ACTIVE)

    def test_member_cannot_change_search_status(self):
        search, _, _ = self.create_search()
        self.authenticate(self.member_profile)

        response = self.update_status(
            search,
            NameSearch.Status.COMPLETED,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_outsider_cannot_change_search_status(self):
        search, _, _ = self.create_search()
        self.authenticate(self.outsider_profile)

        response = self.update_status(
            search,
            NameSearch.Status.COMPLETED,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_status_route_requires_authentication(self):
        search, _, _ = self.create_search()
        self.client.force_authenticate(user=None)

        response = self.update_status(
            search,
            NameSearch.Status.COMPLETED,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_invalid_status_is_rejected(self):
        search, _, _ = self.create_search()

        response = self.update_status(search, "invalid")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        search.refresh_from_db()
        self.assertEqual(search.status, NameSearch.Status.ACTIVE)

    def test_inactive_search_has_no_next_first_name(self):
        search, _, _ = self.create_search()

        for search_status in (
            NameSearch.Status.COMPLETED,
            NameSearch.Status.ARCHIVED,
        ):
            with self.subTest(search_status=search_status):
                search.status = search_status
                search.save(
                    update_fields=("status", "updated_at"),
                )

                response = self.client.get(
                    self.next_first_name_url(search),
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_409_CONFLICT,
                )

    def test_inactive_search_cannot_record_decision(self):
        search, _, _ = self.create_search()

        for search_status in (
            NameSearch.Status.COMPLETED,
            NameSearch.Status.ARCHIVED,
        ):
            with self.subTest(search_status=search_status):
                search.status = search_status
                search.save(
                    update_fields=("status", "updated_at"),
                )

                response = self.client.post(
                    self.decisions_url(search),
                    {
                        "first_name": self.first_name.id,
                        "choice": NameDecision.Choice.LIKED,
                    },
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_409_CONFLICT,
                )
                self.assertEqual(
                    NameDecision.objects.count(),
                    0,
                )

    def test_existing_decisions_remain_readable(self):
        search, owner_participant, _ = self.create_search(
            search_status=NameSearch.Status.COMPLETED,
        )
        decision = NameDecision.objects.create(
            participant=owner_participant,
            first_name=self.first_name,
            choice=NameDecision.Choice.LIKED,
        )

        response = self.client.get(self.decisions_url(search))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], decision.id)

    def test_inactive_search_invitation_cannot_be_accepted(self):
        search, _, invitation = self.create_search(
            member_status=(
                NameSearchParticipant.InvitationStatus.PENDING
            ),
        )
        self.authenticate(self.member_profile)

        for search_status in (
            NameSearch.Status.COMPLETED,
            NameSearch.Status.ARCHIVED,
        ):
            with self.subTest(search_status=search_status):
                search.status = search_status
                search.save(
                    update_fields=("status", "updated_at"),
                )

                response = self.client.patch(
                    self.invitation_url(invitation),
                    {
                        "invitation_status": (
                            NameSearchParticipant
                            .InvitationStatus.ACCEPTED
                        )
                    },
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_409_CONFLICT,
                )

                invitation.refresh_from_db()
                self.assertEqual(
                    invitation.invitation_status,
                    NameSearchParticipant.InvitationStatus.PENDING,
                )