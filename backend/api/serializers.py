from rest_framework import serializers

from .first_name_filters import FIRST_LETTERS
from .first_name_origins import get_origin_description
from .models import (
    FirstName,
    NameDecision,
    NameSearch,
    NameSearchParticipant,
    Profile,
)


class CurrentProfileSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            "id",
            "username",
            "email",
            "display_name",
            "roles",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "username",
            "email",
            "roles",
            "created_at",
            "updated_at",
        )

    def get_roles(self, profile):
        request = self.context.get("request")

        if request is None:
            return []

        return sorted(getattr(request.user, "roles", []))

    def validate(self, attributes):
        writable_fields = {"display_name"}
        received_fields = set(self.initial_data.keys())
        protected_fields = received_fields - writable_fields

        if protected_fields:
            raise serializers.ValidationError(
                {
                    field: (
                        "Ce champ ne peut pas être modifié depuis cette route."
                    )
                    for field in sorted(protected_fields)
                }
            )

        return super().validate(attributes)


class ProfileLookupQuerySerializer(serializers.Serializer):
    email = serializers.EmailField()


class ProfileLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            "id",
            "username",
            "email",
            "display_name",
        )
        read_only_fields = fields


class ProfileSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            "id",
            "username",
            "display_name",
        )
        read_only_fields = fields


class InvitationSearchSummarySerializer(serializers.ModelSerializer):
    creator = ProfileSummarySerializer(read_only=True)

    class Meta:
        model = NameSearch
        fields = (
            "id",
            "title",
            "status",
            "creator",
        )
        read_only_fields = fields


class SearchInvitationSerializer(serializers.ModelSerializer):
    search = InvitationSearchSummarySerializer(read_only=True)
    profile = ProfileSummarySerializer(read_only=True)
    role_label = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )
    invitation_status_label = serializers.CharField(
        source="get_invitation_status_display",
        read_only=True,
    )

    class Meta:
        model = NameSearchParticipant
        fields = (
            "id",
            "search",
            "profile",
            "role",
            "role_label",
            "invitation_status",
            "invitation_status_label",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class SearchInvitationCreateSerializer(serializers.Serializer):
    profile_id = serializers.PrimaryKeyRelatedField(
        source="profile",
        queryset=Profile.objects.all(),
        write_only=True,
    )


class SearchInvitationResponseSerializer(serializers.Serializer):
    invitation_status = serializers.ChoiceField(
        choices=(
            NameSearchParticipant.InvitationStatus.ACCEPTED,
            NameSearchParticipant.InvitationStatus.DECLINED,
        ),
    )


class FirstNameSerializer(serializers.ModelSerializer):
    gender_label = serializers.CharField(
        source="get_gender_display",
        read_only=True,
    )
    origin_label = serializers.CharField(
        source="get_origin_display",
        read_only=True,
    )
    origin_description = serializers.SerializerMethodField()

    def get_origin_description(self, first_name):
        return get_origin_description(first_name.origin)

    class Meta:
        model = FirstName
        fields = (
            "id",
            "name",
            "gender",
            "gender_label",
            "origin",
            "origin_label",
            "origin_description",
            "meaning",
        )
        read_only_fields = fields


class FirstNameOriginSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)


class NameSearchParticipantSerializer(serializers.ModelSerializer):
    profile = ProfileSummarySerializer(read_only=True)
    role_label = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )
    invitation_status_label = serializers.CharField(
        source="get_invitation_status_display",
        read_only=True,
    )

    class Meta:
        model = NameSearchParticipant
        fields = (
            "id",
            "profile",
            "role",
            "role_label",
            "invitation_status",
            "invitation_status_label",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class NameSearchSerializer(serializers.ModelSerializer):
    genders = serializers.ListField(
        child=serializers.ChoiceField(
            choices=FirstName.Gender.choices,
        ),
        allow_empty=False,
        required=False,
    )
    origins = serializers.ListField(
        child=serializers.ChoiceField(
            choices=FirstName._meta.get_field("origin").choices,
        ),
        allow_empty=True,
        required=False,
    )
    min_length = serializers.IntegerField(
        min_value=1,
        max_value=100,
        allow_null=True,
        required=False,
    )
    max_length = serializers.IntegerField(
        min_value=1,
        max_value=100,
        allow_null=True,
        required=False,
    )
    first_letters = serializers.ListField(
        child=serializers.CharField(
            min_length=1,
            max_length=1,
        ),
        allow_empty=True,
        required=False,
    )
    creator = ProfileSummarySerializer(read_only=True)
    participants = NameSearchParticipantSerializer(
        many=True,
        read_only=True,
    )
    status_label = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = NameSearch
        fields = (
            "id",
            "title",
            "genders",
            "origins",
            "min_length",
            "max_length",
            "first_letters",
            "status",
            "status_label",
            "creator",
            "participants",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "status_label",
            "creator",
            "participants",
            "created_at",
            "updated_at",
        )

    def validate_genders(self, genders):
        return list(dict.fromkeys(genders))

    def validate_origins(self, origins):
        return list(dict.fromkeys(origins))

    def validate_first_letters(self, first_letters):
        normalized_letters = []

        for first_letter in first_letters:
            normalized_letter = first_letter.upper()

            if normalized_letter not in FIRST_LETTERS:
                raise serializers.ValidationError(
                    "Chaque première lettre doit être comprise entre A et Z."
                )

            if normalized_letter not in normalized_letters:
                normalized_letters.append(normalized_letter)

        return normalized_letters

    def validate(self, attributes):
        attributes = super().validate(attributes)

        current_min_length = (
            self.instance.min_length if self.instance is not None else None
        )
        current_max_length = (
            self.instance.max_length if self.instance is not None else None
        )
        min_length = attributes.get("min_length", current_min_length)
        max_length = attributes.get("max_length", current_max_length)

        if (
            min_length is not None
            and max_length is not None
            and min_length > max_length
        ):
            raise serializers.ValidationError(
                {
                    "max_length": (
                        "La longueur maximale doit être supérieure ou "
                        "égale à la longueur minimale."
                    )
                }
            )

        return attributes


class NameDecisionSerializer(serializers.ModelSerializer):
    participant = NameSearchParticipantSerializer(read_only=True)
    first_name = FirstNameSerializer(read_only=True)
    first_name_id = serializers.PrimaryKeyRelatedField(
        source="first_name",
        queryset=FirstName.objects.filter(is_active=True),
        write_only=True,
    )
    choice_label = serializers.CharField(
        source="get_choice_display",
        read_only=True,
    )

    class Meta:
        model = NameDecision
        fields = (
            "id",
            "participant",
            "first_name",
            "first_name_id",
            "choice",
            "choice_label",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "participant",
            "first_name",
            "choice_label",
            "created_at",
            "updated_at",
        )
