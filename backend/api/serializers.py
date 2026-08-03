from rest_framework import serializers

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

    class Meta:
        model = FirstName
        fields = (
            "id",
            "name",
            "gender",
            "gender_label",
            "origin",
            "meaning",
        )
        read_only_fields = fields


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