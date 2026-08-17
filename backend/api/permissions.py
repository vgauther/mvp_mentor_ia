from rest_framework.permissions import BasePermission

from .models import Profile


class IsProfileAdmin(BasePermission):
    message = "Cette action est réservée aux administrateurs."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.profile.role == Profile.Role.ADMIN
        )
