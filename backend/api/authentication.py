from dataclasses import dataclass
from typing import Any

import jwt
from django.conf import settings
from django.db import connection, transaction
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError
from rest_framework.authentication import (
    BaseAuthentication,
    get_authorization_header,
)
from rest_framework.exceptions import AuthenticationFailed

from .models import Profile


jwks_client = PyJWKClient(settings.KEYCLOAK_JWKS_URL)


@dataclass(frozen=True)
class KeycloakUser:
    id: str
    username: str
    email: str | None
    roles: frozenset[str]
    claims: dict[str, Any]
    profile: Profile

    @property
    def pk(self) -> str:
        return self.id

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    @property
    def is_staff(self) -> bool:
        return self.profile.role == Profile.Role.ADMIN

    @property
    def is_superuser(self) -> bool:
        return self.profile.role == Profile.Role.ADMIN


@transaction.atomic
def get_or_sync_profile(
    *,
    keycloak_id: str,
    username: str,
    email: str | None,
) -> Profile:
    # PostgreSQL sérialise la création du premier profil afin qu'un seul compte
    # puisse recevoir automatiquement le rôle administrateur.
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                "LOCK TABLE api_profile IN SHARE ROW EXCLUSIVE MODE"
            )

    try:
        profile = Profile.objects.get(keycloak_id=keycloak_id)
    except Profile.DoesNotExist:
        is_first_profile = not Profile.objects.exists()
        profile = Profile.objects.create(
            keycloak_id=keycloak_id,
            username=username,
            email=email,
            role=(
                Profile.Role.ADMIN
                if is_first_profile
                else Profile.Role.LEARNER
            ),
        )

    changed_fields = []

    if profile.username != username:
        profile.username = username
        changed_fields.append("username")

    if profile.email != email:
        profile.email = email
        changed_fields.append("email")

    if changed_fields:
        profile.save(
            update_fields=[
                *changed_fields,
                "updated_at",
            ]
        )

    return profile


class KeycloakAuthentication(BaseAuthentication):
    keyword = b"bearer"

    def authenticate(self, request):
        authorization = get_authorization_header(request).split()

        if not authorization:
            return None

        if authorization[0].lower() != self.keyword:
            return None

        if len(authorization) != 2:
            raise AuthenticationFailed(
                "L'en-tête Authorization doit contenir un jeton Bearer."
            )

        try:
            token = authorization[1].decode("ascii")
        except UnicodeError as error:
            raise AuthenticationFailed(
                "Le jeton d'authentification est invalide."
            ) from error

        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.KEYCLOAK_AUDIENCE,
                issuer=settings.KEYCLOAK_ISSUER,
                options={
                    "require": [
                        "exp",
                        "iat",
                        "iss",
                        "aud",
                        "sub",
                    ],
                },
            )
        except (InvalidTokenError, PyJWKClientError) as error:
            raise AuthenticationFailed(
                "Le jeton Keycloak est invalide ou expiré."
            ) from error

        username = claims.get("preferred_username") or claims["sub"]
        email = claims.get("email") or None

        profile = get_or_sync_profile(
            keycloak_id=claims["sub"],
            username=username,
            email=email,
        )

        user = KeycloakUser(
            id=claims["sub"],
            username=username,
            email=email,
            roles=frozenset({profile.role}),
            claims=claims,
            profile=profile,
        )

        return user, claims

    def authenticate_header(self, request):
        return "Bearer"
