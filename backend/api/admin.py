from django.contrib import admin

from .models import CourseUnit, LearningObjective, Profile, RawMaterial, Training


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "display_name",
        "role",
        "created_at",
    )
    list_filter = ("role",)
    search_fields = ("username", "email", "display_name", "keycloak_id")
    readonly_fields = ("keycloak_id", "created_at", "updated_at")


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "created_by", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LearningObjective)
class LearningObjectiveAdmin(admin.ModelAdmin):
    list_display = ("title", "training", "position")
    list_filter = ("training",)
    search_fields = ("title", "description")


@admin.register(CourseUnit)
class CourseUnitAdmin(admin.ModelAdmin):
    list_display = ("working_title", "kind", "training", "parent", "position")
    list_filter = ("kind", "training")
    search_fields = ("working_title", "notes")
    filter_horizontal = ("objectives",)


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ("display_name", "kind", "training", "size", "created_at")
    list_filter = ("kind", "training")
    readonly_fields = (
        "original_filename",
        "mime_type",
        "size",
        "created_at",
    )
