from dataclasses import dataclass
from typing import Any

import jwt
from django.conf import settings
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError
from rest_framework.authentication import (
    BaseAuthentication,
    get_authorization_header,
)
from rest_framework.exceptions import AuthenticationFailed


jwks_client = PyJWKClient(settings.KEYCLOAK_JWKS_URL)


@dataclass(frozen=True)
class KeycloakUser:
    id: str
    username: str
    email: str | None
    roles: frozenset[str]
    claims: dict[str, Any]

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
        return "admin" in self.roles

    @property
    def is_superuser(self) -> bool:
        return "admin" in self.roles


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

        realm_access = claims.get("realm_access", {})
        roles = frozenset(realm_access.get("roles", []))

        user = KeycloakUser(
            id=claims["sub"],
            username=claims.get(
                "preferred_username",
                claims["sub"],
            ),
            email=claims.get("email"),
            roles=roles,
            claims=claims,
        )

        return user, claims

    def authenticate_header(self, request):
        return "Bearer"