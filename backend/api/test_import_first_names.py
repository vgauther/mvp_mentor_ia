from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from api.models import FirstName


class ImportFirstNamesCommandTests(TestCase):
    def create_csv(self, content: str) -> Path:
        temporary_directory = TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)

        csv_path = Path(temporary_directory.name) / "prenoms.csv"
        csv_path.write_text(content, encoding="utf-8")

        return csv_path

    def test_imports_first_names_and_converts_genders(self):
        csv_path = self.create_csv(
            "prenom,sexe,origine,signification\n"
            "Alice,féminin,germanique,Noble\n"
            "Paul,masculin,latine,Petit\n"
            "Camille,neutre,francaise,Assistant de cérémonie\n"
        )
        output = StringIO()

        call_command(
            "import_first_names",
            str(csv_path),
            stdout=output,
        )

        self.assertEqual(FirstName.objects.count(), 3)

        self.assertEqual(
            FirstName.objects.get(name="Alice").gender,
            FirstName.Gender.FEMALE,
        )
        self.assertEqual(
            FirstName.objects.get(name="Paul").gender,
            FirstName.Gender.MALE,
        )
        self.assertEqual(
            FirstName.objects.get(name="Camille").gender,
            FirstName.Gender.MIXED,
        )
        self.assertEqual(
            FirstName.objects.get(name="Alice").origin,
            "germanique",
        )
        self.assertEqual(
            FirstName.objects.get(name="Alice").meaning,
            "Noble",
        )

        self.assertIn(
            "3 prénom(s) créé(s)",
            output.getvalue(),
        )

    def test_import_can_be_run_twice_without_creating_duplicates(self):
        csv_path = self.create_csv(
            "prenom,sexe,origine,signification\n"
            "Alice,féminin,germanique,Noble\n"
            "Paul,masculin,latine,Petit\n"
        )

        call_command(
            "import_first_names",
            str(csv_path),
            stdout=StringIO(),
        )

        second_output = StringIO()

        call_command(
            "import_first_names",
            str(csv_path),
            stdout=second_output,
        )

        self.assertEqual(FirstName.objects.count(), 2)
        self.assertIn(
            "0 prénom(s) créé(s)",
            second_output.getvalue(),
        )
        self.assertIn(
            "0 prénom(s) mis à jour",
            second_output.getvalue(),
        )
        self.assertIn(
            "2 prénom(s) inchangé(s)",
            second_output.getvalue(),
        )

    def test_existing_name_is_updated_case_insensitively(self):
        existing_first_name = FirstName.objects.create(
            name="Alice",
            gender=FirstName.Gender.MIXED,
            origin="indeterminee",
            meaning="Ancienne information",
        )

        csv_path = self.create_csv(
            "prenom,sexe,origine,signification\n"
            "alice,féminin,germanique,Noble\n"
        )
        output = StringIO()

        call_command(
            "import_first_names",
            str(csv_path),
            stdout=output,
        )

        self.assertEqual(FirstName.objects.count(), 1)

        imported_first_name = FirstName.objects.get()

        self.assertEqual(
            imported_first_name.id,
            existing_first_name.id,
        )
        self.assertEqual(imported_first_name.name, "alice")
        self.assertEqual(
            imported_first_name.gender,
            FirstName.Gender.FEMALE,
        )
        self.assertEqual(
            imported_first_name.origin,
            "germanique",
        )
        self.assertEqual(
            imported_first_name.meaning,
            "Noble",
        )
        self.assertIn(
            "0 prénom(s) créé(s)",
            output.getvalue(),
        )
        self.assertIn(
            "1 prénom(s) mis à jour",
            output.getvalue(),
        )

    def test_rejects_unknown_gender_without_importing_anything(self):
        csv_path = self.create_csv(
            "prenom,sexe,origine,signification\n"
            "Alice,féminin,germanique,Noble\n"
            "Alexandre,inconnu,grecque,Protecteur\n"
        )

        with self.assertRaisesMessage(
            CommandError,
            "sexe inconnu",
        ):
            call_command(
                "import_first_names",
                str(csv_path),
            )

        self.assertEqual(FirstName.objects.count(), 0)

    def test_rejects_csv_with_missing_column(self):
        csv_path = self.create_csv(
            "prenom\n"
            "Alice\n"
        )

        with self.assertRaisesMessage(
            CommandError,
            (
                "Colonne(s) obligatoire(s) absente(s) : "
                "origine, sexe, signification"
            ),
        ):
            call_command(
                "import_first_names",
                str(csv_path),
            )

        self.assertEqual(FirstName.objects.count(), 0)

    def test_rejects_unknown_origin_without_importing_anything(self):
        csv_path = self.create_csv(
            "prenom,sexe,origine,signification\n"
            "Alice,féminin,origine_inconnue,Noble\n"
        )

        with self.assertRaisesMessage(
            CommandError,
            "origine inconnue",
        ):
            call_command(
                "import_first_names",
                str(csv_path),
            )

        self.assertEqual(FirstName.objects.count(), 0)

    def test_rejects_empty_meaning_without_importing_anything(self):
        csv_path = self.create_csv(
            "prenom,sexe,origine,signification\n"
            "Alice,féminin,germanique,\n"
        )

        with self.assertRaisesMessage(
            CommandError,
            "signification vide",
        ):
            call_command(
                "import_first_names",
                str(csv_path),
            )

        self.assertEqual(FirstName.objects.count(), 0)