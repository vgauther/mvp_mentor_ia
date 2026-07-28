from django.contrib import admin

from .models import FirstName, NameSearch, Profile


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