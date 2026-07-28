from django.contrib import admin

from .models import (
    FirstName,
    NameDecision,
    NameSearch,
    NameSearchParticipant,
    Profile,
)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "display_name",
        "email",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "username",
        "display_name",
        "email",
        "keycloak_id",
    )
    readonly_fields = (
        "keycloak_id",
        "created_at",
        "updated_at",
    )


@admin.register(FirstName)
class FirstNameAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "gender",
        "origin",
        "is_active",
        "created_at",
    )
    list_filter = (
        "gender",
        "is_active",
    )
    search_fields = (
        "name",
        "origin",
    )
    ordering = ("name",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )

@admin.register(NameSearch)
class NameSearchAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "creator",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "status",
        "created_at",
    )
    search_fields = (
        "title",
        "creator__username",
        "creator__display_name",
        "creator__email",
    )
    autocomplete_fields = ("creator",)
    ordering = ("-created_at",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )

@admin.register(NameSearchParticipant)
class NameSearchParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "search",
        "role",
        "invitation_status",
        "created_at",
    )
    list_filter = (
        "role",
        "invitation_status",
        "created_at",
    )
    search_fields = (
        "search__title",
        "profile__username",
        "profile__display_name",
        "profile__email",
    )
    autocomplete_fields = (
        "search",
        "profile",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )

@admin.register(NameDecision)
class NameDecisionAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "participant",
        "choice",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "choice",
        "participant__search",
        "created_at",
    )
    search_fields = (
        "first_name__name",
        "participant__profile__username",
        "participant__profile__display_name",
        "participant__search__title",
    )
    autocomplete_fields = (
        "participant",
        "first_name",
    )
    ordering = ("-updated_at",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )