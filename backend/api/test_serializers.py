from django.test import TestCase

from .models import FirstName
from .serializers import (
    FirstNameSerializer,
    NameDecisionSerializer,
    NameSearchSerializer,
)


class BusinessSerializerTests(TestCase):
    def setUp(self):
        gender_field = FirstName._meta.get_field("gender")
        self.gender = gender_field.choices[0][0]

        self.active_first_name = FirstName.objects.create(
            name="Emma",
            gender=self.gender,
            origin="germanique",
            meaning="Universelle",
            is_active=True,
        )
        self.inactive_first_name = FirstName.objects.create(
            name="Alba",
            gender=self.gender,
            origin="latine",
            meaning="Aube",
            is_active=False,
        )

    def test_first_name_serializer_exposes_expected_fields(self):
        serializer = FirstNameSerializer(self.active_first_name)

        self.assertEqual(
            set(serializer.data),
            {
                "id",
                "name",
                "gender",
                "gender_label",
                "origin",
                "origin_label",
                "origin_description",
                "meaning",
            },
        )
        self.assertEqual(serializer.data["name"], "Emma")
        self.assertEqual(serializer.data["gender"], self.gender)
        self.assertEqual(serializer.data["origin"], "germanique")
        self.assertEqual(serializer.data["origin_label"], "Germanique")
        self.assertNotEqual(
            serializer.data["origin_description"],
            "",
        )
        self.assertEqual(serializer.data["meaning"], "Universelle")
        self.assertNotIn("is_active", serializer.data)

    def test_name_search_protects_managed_fields(self):
        serializer = NameSearchSerializer()

        self.assertFalse(serializer.fields["title"].read_only)
        self.assertTrue(serializer.fields["status"].read_only)
        self.assertTrue(serializer.fields["creator"].read_only)
        self.assertTrue(serializer.fields["participants"].read_only)
        self.assertTrue(serializer.fields["created_at"].read_only)
        self.assertTrue(serializer.fields["updated_at"].read_only)

    def test_name_decision_protects_managed_fields(self):
        serializer = NameDecisionSerializer()

        self.assertTrue(serializer.fields["participant"].read_only)
        self.assertTrue(serializer.fields["first_name"].read_only)
        self.assertTrue(serializer.fields["first_name_id"].write_only)
        self.assertFalse(serializer.fields["choice"].read_only)

    def test_name_decision_accepts_an_active_first_name(self):
        serializer = NameDecisionSerializer(
            data={
                "first_name_id": self.active_first_name.id,
                "choice": "liked",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["first_name"],
            self.active_first_name,
        )
        self.assertEqual(serializer.validated_data["choice"], "liked")

    def test_name_decision_rejects_an_inactive_first_name(self):
        serializer = NameDecisionSerializer(
            data={
                "first_name_id": self.inactive_first_name.id,
                "choice": "rejected",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("first_name_id", serializer.errors)

    def test_name_decision_rejects_an_unknown_choice(self):
        serializer = NameDecisionSerializer(
            data={
                "first_name_id": self.active_first_name.id,
                "choice": "maybe",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("choice", serializer.errors)