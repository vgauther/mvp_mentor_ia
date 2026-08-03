from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FirstName, NameDecision, NameSearchParticipant
from .serializers import FirstNameSerializer


class SearchLikedFirstNameListView(APIView):
    permission_classes = [IsAuthenticated]

    def get_participant(self, search_id):
        return get_object_or_404(
            NameSearchParticipant,
            search_id=search_id,
            profile=self.request.user.profile,
            invitation_status=(
                NameSearchParticipant.InvitationStatus.ACCEPTED
            ),
        )

    def get(self, request, search_id):
        participant = self.get_participant(search_id)

        first_names = (
            FirstName.objects.filter(
                decisions__participant=participant,
                decisions__choice=NameDecision.Choice.LIKED,
                is_active=True,
            )
            .order_by("name", "id")
            .distinct()
        )

        serializer = FirstNameSerializer(first_names, many=True)
        return Response(serializer.data)