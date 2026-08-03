from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
)
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
    Profile,
)
from .serializers import (
    CurrentProfileSerializer,
    FirstNameSerializer,
    NameDecisionSerializer,
    NameSearchSerializer,
    ProfileLookupQuerySerializer,
    ProfileLookupSerializer,
)


class PublicView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "message": "La route publique fonctionne.",
            }
        )


class MeView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CurrentProfileSerializer
    http_method_names = [
        "get",
        "patch",
        "head",
        "options",
    ]

    def get_object(self):
        return self.request.user.profile


class ProfileLookupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_serializer = ProfileLookupQuerySerializer(
            data=request.query_params,
        )
        query_serializer.is_valid(raise_exception=True)

        email = query_serializer.validated_data["email"]

        profiles = list(
            Profile.objects.filter(
                email__iexact=email,
            ).order_by("id")[:2]
        )

        if not profiles:
            raise NotFound(
                "Aucun profil ne correspond à cette adresse e-mail."
            )

        if len(profiles) > 1:
            return Response(
                {
                    "detail": (
                        "Plusieurs profils utilisent cette adresse e-mail."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = ProfileLookupSerializer(profiles[0])
        return Response(serializer.data)


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


class NextFirstNameView(APIView):
    def get_participant(self, search_id):
        return get_object_or_404(
            NameSearchParticipant.objects.select_related("search"),
            search_id=search_id,
            profile=self.request.user.profile,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

    def get(self, request, search_id):
        participant = self.get_participant(search_id)

        decided_first_name_ids = NameDecision.objects.filter(
            participant=participant,
        ).values("first_name_id")

        first_name = (
            FirstName.objects.filter(
                is_active=True,
                gender__in=participant.search.genders,
            )
            .exclude(id__in=decided_first_name_ids)
            .order_by("id")
            .first()
        )

        if first_name is None:
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = FirstNameSerializer(first_name)
        return Response(serializer.data)


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