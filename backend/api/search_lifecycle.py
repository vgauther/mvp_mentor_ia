from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import NameSearch, NameSearchParticipant
from .serializers import (
    NameSearchSerializer,
    SearchInvitationResponseSerializer,
)
from .views import (
    NameDecisionListCreateView,
    NextFirstNameView,
    SearchInvitationResponseView,
)


class SearchNotActive(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Cette recherche n’est plus active."
    default_code = "search_not_active"


class SearchStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=NameSearch.Status.choices,
    )


class SearchStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    allowed_transitions = {
        NameSearch.Status.ACTIVE: {
            NameSearch.Status.COMPLETED,
        },
        NameSearch.Status.COMPLETED: {
            NameSearch.Status.ACTIVE,
            NameSearch.Status.ARCHIVED,
        },
        NameSearch.Status.ARCHIVED: {
            NameSearch.Status.COMPLETED,
        },
    }

    @transaction.atomic
    def patch(self, request, search_id):
        search = get_object_or_404(
            NameSearch.objects.select_for_update(),
            id=search_id,
            creator=request.user.profile,
        )

        input_serializer = SearchStatusUpdateSerializer(
            data=request.data,
        )
        input_serializer.is_valid(raise_exception=True)

        new_status = input_serializer.validated_data["status"]

        if new_status == search.status:
            output_serializer = NameSearchSerializer(search)
            return Response(output_serializer.data)

        allowed_statuses = self.allowed_transitions.get(
            search.status,
            set(),
        )

        if new_status not in allowed_statuses:
            return Response(
                {
                    "detail": (
                        "Cette transition d’état n’est pas autorisée."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        search.status = new_status
        search.save(update_fields=("status", "updated_at"))

        output_serializer = NameSearchSerializer(search)
        return Response(output_serializer.data)


class LifecycleSearchInvitationResponseView(
    SearchInvitationResponseView
):
    @transaction.atomic
    def patch(self, request, invitation_id):
        invitation = get_object_or_404(
            NameSearchParticipant.objects.select_for_update().select_related(
                "search",
            ),
            id=invitation_id,
            profile=request.user.profile,
            role=NameSearchParticipant.Role.MEMBER,
        )

        if (
            invitation.invitation_status
            == NameSearchParticipant.InvitationStatus.PENDING
        ):
            input_serializer = SearchInvitationResponseSerializer(
                data=request.data,
            )
            input_serializer.is_valid(raise_exception=True)

            new_invitation_status = (
                input_serializer.validated_data["invitation_status"]
            )

            if (
                new_invitation_status
                == NameSearchParticipant.InvitationStatus.ACCEPTED
                and invitation.search.status
                != NameSearch.Status.ACTIVE
            ):
                raise SearchNotActive()

        return super().patch(request, invitation_id)


class LifecycleNextFirstNameView(NextFirstNameView):
    def get_participant(self, search_id):
        participant = super().get_participant(search_id)

        if participant.search.status != NameSearch.Status.ACTIVE:
            raise SearchNotActive()

        return participant


class LifecycleNameDecisionListCreateView(
    NameDecisionListCreateView
):
    def get_participant(self, search_id):
        participant = super().get_participant(search_id)

        if (
            self.request.method == "POST"
            and participant.search.status
            != NameSearch.Status.ACTIVE
        ):
            raise SearchNotActive()

        return participant