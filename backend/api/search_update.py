from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import NameSearch
from .serializers import NameSearchSerializer


class NameSearchUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, search_id):
        search = get_object_or_404(
            NameSearch.objects.select_for_update()
            .select_related("creator")
            .prefetch_related("participants__profile"),
            id=search_id,
            creator=request.user.profile,
        )

        serializer = NameSearchSerializer(
            search,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)