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


def default_search_genders():
    return [
        FirstName.Gender.FEMALE,
        FirstName.Gender.MALE,
        FirstName.Gender.MIXED,
    ]


class NameSearch(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Terminée"
        ARCHIVED = "archived", "Archivée"

    creator = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="name_searches",
    )
    title = models.CharField(max_length=150)
    genders = models.JSONField(default=default_search_genders)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "recherche de prénoms"
        verbose_name_plural = "recherches de prénoms"
        indexes = [
            models.Index(
                fields=("creator", "status"),
                name="search_creator_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class NameSearchParticipant(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Propriétaire"
        MEMBER = "member", "Participant"

    class InvitationStatus(models.TextChoices):
        PENDING = "pending", "En attente"
        ACCEPTED = "accepted", "Acceptée"
        DECLINED = "declined", "Refusée"

    search = models.ForeignKey(
        NameSearch,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="search_participations",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    invitation_status = models.CharField(
        max_length=10,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at",)
        verbose_name = "participant à une recherche"
        verbose_name_plural = "participants aux recherches"
        constraints = [
            models.UniqueConstraint(
                fields=("search", "profile"),
                name="unique_search_participant",
            ),
        ]
        indexes = [
            models.Index(
                fields=("profile", "invitation_status"),
                name="participant_invite_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.profile} — {self.search}"


class NameDecision(models.Model):
    class Choice(models.TextChoices):
        LIKED = "liked", "Aimé"
        REJECTED = "rejected", "Refusé"
        SKIPPED = "skipped", "Passé"

    participant = models.ForeignKey(
        NameSearchParticipant,
        on_delete=models.CASCADE,
        related_name="decisions",
    )
    first_name = models.ForeignKey(
        FirstName,
        on_delete=models.CASCADE,
        related_name="decisions",
    )
    choice = models.CharField(
        max_length=8,
        choices=Choice.choices,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "décision sur un prénom"
        verbose_name_plural = "décisions sur les prénoms"
        constraints = [
            models.UniqueConstraint(
                fields=("participant", "first_name"),
                name="unique_participant_first_name",
            ),
        ]
        indexes = [
            models.Index(
                fields=("participant", "choice"),
                name="decision_part_choice_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.participant.profile} — "
            f"{self.first_name}: {self.get_choice_display()}"
        )