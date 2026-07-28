from django.db import models
from django.db.models.functions import Lower


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


class FirstName(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "female", "Féminin"
        MALE = "male", "Masculin"
        MIXED = "mixed", "Mixte"

    name = models.CharField(max_length=100)
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        db_index=True,
    )
    origin = models.CharField(
        max_length=150,
        blank=True,
    )
    meaning = models.TextField(blank=True)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "prénom"
        verbose_name_plural = "prénoms"
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="unique_first_name_case_insensitive",
            ),
        ]

    def __str__(self) -> str:
        return self.name