from django.db import transaction
from django.db.models.functions import Length
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

from .first_name_filters import build_first_letter_regex
from .first_name_origins import FIRST_NAME_ORIGINS
from .models import (
    FirstName,
    NameDecision,
    NameSearch,
    NameSearchParticipant,
    Profile,
)
from .serializers import (
    CurrentProfileSerializer,
    FirstNameOriginSerializer,
    FirstNameSerializer,
    NameDecisionSerializer,
    NameSearchSerializer,
    ProfileLookupQuerySerializer,
    ProfileLookupSerializer,
    SearchInvitationCreateSerializer,
    SearchInvitationResponseSerializer,
    SearchInvitationSerializer,
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


class FirstNameOriginListView(APIView):
    def get(self, request):
        origins = [
            {
                "id": origin_id,
                "label": label,
                "description": description,
            }
            for origin_id, label, description in FIRST_NAME_ORIGINS
        ]
        serializer = FirstNameOriginSerializer(
            origins,
            many=True,
        )

        return Response(serializer.data)


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


class SearchInvitationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_owner_participant(self, search_id):
        return get_object_or_404(
            NameSearchParticipant.objects.select_for_update().select_related(
                "search",
            ),
            search_id=search_id,
            profile=self.request.user.profile,
            role=NameSearchParticipant.Role.OWNER,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

    @transaction.atomic
    def post(self, request, search_id):
        owner_participant = self.get_owner_participant(search_id)
        search = owner_participant.search

        if search.status != NameSearch.Status.ACTIVE:
            return Response(
                {
                    "detail": (
                        "Il est impossible d'inviter un participant dans "
                        "une recherche terminée ou archivée."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        input_serializer = SearchInvitationCreateSerializer(
            data=request.data,
        )
        input_serializer.is_valid(raise_exception=True)

        invited_profile = input_serializer.validated_data["profile"]

        if invited_profile == request.user.profile:
            return Response(
                {
                    "detail": (
                        "Vous ne pouvez pas vous inviter dans votre propre "
                        "recherche."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_invitation = (
            NameSearchParticipant.objects.select_for_update()
            .filter(
                search=search,
                profile=invited_profile,
            )
            .first()
        )

        if (
            existing_invitation is not None
            and existing_invitation.invitation_status
            in (
                NameSearchParticipant.InvitationStatus.PENDING,
                NameSearchParticipant.InvitationStatus.ACCEPTED,
            )
        ):
            return Response(
                {
                    "detail": (
                        "Ce profil participe déjà à cette recherche ou possède "
                        "déjà une invitation en attente."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        another_guest_exists = (
            NameSearchParticipant.objects.filter(
                search=search,
                role=NameSearchParticipant.Role.MEMBER,
                invitation_status__in=(
                    NameSearchParticipant.InvitationStatus.PENDING,
                    NameSearchParticipant.InvitationStatus.ACCEPTED,
                ),
            )
            .exclude(profile=invited_profile)
            .exists()
        )

        if another_guest_exists:
            return Response(
                {
                    "detail": (
                        "Cette recherche possède déjà un participant ou une "
                        "invitation en attente."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if existing_invitation is not None:
            existing_invitation.role = NameSearchParticipant.Role.MEMBER
            existing_invitation.invitation_status = (
                NameSearchParticipant.InvitationStatus.PENDING
            )
            existing_invitation.save(
                update_fields=(
                    "role",
                    "invitation_status",
                    "updated_at",
                )
            )
            invitation = existing_invitation
            response_status = status.HTTP_200_OK
        else:
            invitation = NameSearchParticipant.objects.create(
                search=search,
                profile=invited_profile,
                role=NameSearchParticipant.Role.MEMBER,
                invitation_status=(
                    NameSearchParticipant.InvitationStatus.PENDING
                ),
            )
            response_status = status.HTTP_201_CREATED

        output_serializer = SearchInvitationSerializer(invitation)

        return Response(
            output_serializer.data,
            status=response_status,
        )


class SearchInvitationListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SearchInvitationSerializer

    def get_queryset(self):
        return (
            NameSearchParticipant.objects.filter(
                profile=self.request.user.profile,
                role=NameSearchParticipant.Role.MEMBER,
                invitation_status=(
                    NameSearchParticipant.InvitationStatus.PENDING
                ),
            )
            .select_related(
                "profile",
                "search",
                "search__creator",
            )
            .order_by("-created_at")
        )


class SearchInvitationResponseView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, invitation_id):
        invitation = get_object_or_404(
            NameSearchParticipant.objects.select_for_update().select_related(
                "profile",
                "search",
                "search__creator",
            ),
            id=invitation_id,
            profile=request.user.profile,
            role=NameSearchParticipant.Role.MEMBER,
        )

        if (
            invitation.invitation_status
            != NameSearchParticipant.InvitationStatus.PENDING
        ):
            return Response(
                {
                    "detail": (
                        "Cette invitation a déjà été acceptée ou refusée."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        input_serializer = SearchInvitationResponseSerializer(
            data=request.data,
        )
        input_serializer.is_valid(raise_exception=True)

        invitation.invitation_status = input_serializer.validated_data[
            "invitation_status"
        ]
        invitation.save(
            update_fields=(
                "invitation_status",
                "updated_at",
            )
        )

        output_serializer = SearchInvitationSerializer(invitation)

        return Response(output_serializer.data)


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
        search = participant.search

        decided_first_name_ids = NameDecision.objects.filter(
            participant=participant,
        ).values("first_name_id")

        first_names = FirstName.objects.filter(
            is_active=True,
            gender__in=search.genders,
        ).exclude(id__in=decided_first_name_ids)

        if search.origins:
            first_names = first_names.filter(origin__in=search.origins)

        if search.min_length is not None or search.max_length is not None:
            first_names = first_names.annotate(name_length=Length("name"))

            if search.min_length is not None:
                first_names = first_names.filter(
                    name_length__gte=search.min_length,
                )

            if search.max_length is not None:
                first_names = first_names.filter(
                    name_length__lte=search.max_length,
                )

        if search.first_letters:
            first_names = first_names.filter(
                name__iregex=build_first_letter_regex(search.first_letters),
            )

        other_liked_first_name_ids = NameDecision.objects.filter(
            participant__search=search,
            participant__invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
            choice=NameDecision.Choice.LIKED,
        ).exclude(
            participant=participant,
        ).values("first_name_id")

        if decided_first_name_ids.count() % 2 == 1:
            preferred_first_names = first_names.filter(
                id__in=other_liked_first_name_ids,
            )
        else:
            preferred_first_names = first_names.exclude(
                id__in=other_liked_first_name_ids,
            )

        first_name = preferred_first_names.order_by("?").first()

        if first_name is None:
            first_name = first_names.order_by("?").first()

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

        decisions = NameDecision.objects.filter(
            participant=participant,
        ).select_related(
            "participant__profile",
            "participant__search",
            "first_name",
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


class SearchMatchListView(APIView):
    permission_classes = [IsAuthenticated]

    def get_search(self, search_id):
        participant = get_object_or_404(
            NameSearchParticipant.objects.select_related("search"),
            search_id=search_id,
            profile=self.request.user.profile,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )
        return participant.search

    def get(self, request, search_id):
        search = self.get_search(search_id)

        participant_ids = list(
            NameSearchParticipant.objects.filter(
                search=search,
                invitation_status=(
                    NameSearchParticipant.InvitationStatus.ACCEPTED
                ),
            )
            .order_by("id")
            .values_list("id", flat=True)
        )

        if len(participant_ids) != 2:
            return Response([])

        common_liked_first_name_ids = None

        for participant_id in participant_ids:
            liked_first_name_ids = set(
                NameDecision.objects.filter(
                    participant_id=participant_id,
                    choice=NameDecision.Choice.LIKED,
                ).values_list("first_name_id", flat=True)
            )

            if common_liked_first_name_ids is None:
                common_liked_first_name_ids = liked_first_name_ids
            else:
                common_liked_first_name_ids.intersection_update(
                    liked_first_name_ids
                )

            if not common_liked_first_name_ids:
                return Response([])

        first_names = FirstName.objects.filter(
            id__in=common_liked_first_name_ids,
            is_active=True,
        ).order_by("name", "id")

        serializer = FirstNameSerializer(first_names, many=True)
        return Response(serializer.data)
