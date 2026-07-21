from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView


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