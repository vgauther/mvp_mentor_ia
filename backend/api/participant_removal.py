from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import NameSearchParticipant


class SearchParticipantRemovalView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, search_id, participant_id):
        get_object_or_404(
            NameSearchParticipant.objects.select_for_update(),
            search_id=search_id,
            profile=request.user.profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        participant = get_object_or_404(
            NameSearchParticipant.objects.select_for_update(),
            id=participant_id,
            search_id=search_id,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status__in=(
                NameSearchParticipant.InvitationStatus.PENDING,
                NameSearchParticipant.InvitationStatus.ACCEPTED,
            ),
        )

        participant.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class SearchParticipantLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, search_id):
        participant = get_object_or_404(
            NameSearchParticipant.objects.select_for_update(),
            search_id=search_id,
            profile=request.user.profile,
            role=NameSearchParticipant.Role.MEMBER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

        participant.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)