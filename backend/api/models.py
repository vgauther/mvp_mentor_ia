from django.db import models


class Profile(models.Model):
    keycloak_id = models.CharField(
        max_length=255,
        unique=True,
        editable=False,
    )
    username = models.CharField(max_length=150)
    email = models.EmailField(
        null=True,
        blank=True,
        db_index=True,
    )
    display_name = models.CharField(
        max_length=150,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name or self.username