from django.db import transaction
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FirstName, NameSearch, NameSearchParticipant
from .serializers import FirstNameSerializer, NameSearchSerializer


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