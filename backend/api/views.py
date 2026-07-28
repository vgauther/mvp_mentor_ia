from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    FirstName,
    NameDecision,
    NameSearch,
    NameSearchParticipant,
)
from .serializers import (
    FirstNameSerializer,
    NameDecisionSerializer,
    NameSearchSerializer,
)

class PublicView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "message": "La route publique fonctionne.",
            }
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "roles": sorted(request.user.roles),
            }
        )


class AdminView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(
            {
                "message": "La route administrateur fonctionne.",
                "username": request.user.username,
            }
        )


class FirstNameListView(ListAPIView):
    serializer_class = FirstNameSerializer

    def get_queryset(self):
        return FirstName.objects.filter(is_active=True)


class NameSearchListCreateView(ListCreateAPIView):
    serializer_class = NameSearchSerializer

    def get_queryset(self):
        return (
            NameSearch.objects.filter(
                participants__profile=self.request.user.profile,
                participants__invitation_status=(
                    NameSearchParticipant.InvitationStatus.ACCEPTED
                ),
            )
            .select_related("creator")
            .prefetch_related("participants__profile")
            .distinct()
        )

    @transaction.atomic
    def perform_create(self, serializer):
        search = serializer.save(
            creator=self.request.user.profile,
        )

        NameSearchParticipant.objects.create(
            search=search,
            profile=self.request.user.profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

class NameDecisionListCreateView(APIView):
    def get_participant(self, search_id):
        return get_object_or_404(
            NameSearchParticipant.objects.select_related(
                "profile",
                "search",
            ),
            search_id=search_id,
            profile=self.request.user.profile,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

    def get(self, request, search_id):
        participant = self.get_participant(search_id)

        decisions = (
            NameDecision.objects.filter(participant=participant)
            .select_related(
                "participant__profile",
                "participant__search",
                "first_name",
            )
        )

        serializer = NameDecisionSerializer(decisions, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request, search_id):
        participant = self.get_participant(search_id)

        serializer = NameDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decision, created = NameDecision.objects.update_or_create(
            participant=participant,
            first_name=serializer.validated_data["first_name"],
            defaults={
                "choice": serializer.validated_data["choice"],
            },
        )

        response_serializer = NameDecisionSerializer(decision)

        return Response(
            response_serializer.data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )