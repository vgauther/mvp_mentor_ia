import csv
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import FirstName


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    ).strip()


GENDER_MAPPING = {
    "feminin": FirstName.Gender.FEMALE,
    "female": FirstName.Gender.FEMALE,
    "masculin": FirstName.Gender.MALE,
    "male": FirstName.Gender.MALE,
    "neutre": FirstName.Gender.MIXED,
    "mixte": FirstName.Gender.MIXED,
    "mixed": FirstName.Gender.MIXED,
}


class Command(BaseCommand):
    help = "Importe des prénoms depuis un fichier CSV contenant prenom et sexe."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Chemin du fichier CSV à importer.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"]).expanduser()

        if not csv_path.is_file():
            raise CommandError(
                f"Le fichier CSV est introuvable : {csv_path}"
            )

        try:
            candidates, valid_row_count = self.read_csv(csv_path)
        except UnicodeDecodeError as error:
            raise CommandError(
                "Le fichier CSV ne peut pas être lu en UTF-8."
            ) from error
        except OSError as error:
            raise CommandError(
                f"Impossible de lire le fichier CSV : {error}"
            ) from error

        existing_names = {
            name.casefold()
            for name in FirstName.objects.values_list("name", flat=True)
        }

        first_names_to_create = [
            FirstName(
                name=name,
                gender=gender,
            )
            for normalized_name, (name, gender) in candidates.items()
            if normalized_name not in existing_names
        ]

        with transaction.atomic():
            count_before = FirstName.objects.count()

            FirstName.objects.bulk_create(
                first_names_to_create,
                batch_size=1000,
                ignore_conflicts=True,
            )

            count_after = FirstName.objects.count()

        created_count = count_after - count_before
        ignored_count = valid_row_count - created_count

        self.stdout.write(
            self.style.SUCCESS(
                "Import terminé : "
                f"{valid_row_count} ligne(s) valide(s), "
                f"{created_count} prénom(s) créé(s), "
                f"{ignored_count} ligne(s) ignorée(s), "
                "0 erreur."
            )
        )

    def read_csv(
        self,
        csv_path: Path,
    ) -> tuple[dict[str, tuple[str, str]], int]:
        candidates: dict[str, tuple[str, str]] = {}
        errors: list[str] = []
        valid_row_count = 0

        with csv_path.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            if reader.fieldnames is None:
                raise CommandError(
                    "Le fichier CSV ne contient aucun en-tête."
                )

            columns = {
                column.strip().casefold(): column
                for column in reader.fieldnames
                if column is not None
            }

            missing_columns = {
                "prenom",
                "sexe",
            } - columns.keys()

            if missing_columns:
                missing_columns_text = ", ".join(
                    sorted(missing_columns)
                )
                raise CommandError(
                    "Colonne(s) obligatoire(s) absente(s) : "
                    f"{missing_columns_text}."
                )

            first_name_column = columns["prenom"]
            gender_column = columns["sexe"]

            for line_number, row in enumerate(reader, start=2):
                raw_name = (row.get(first_name_column) or "").strip()
                raw_gender = (row.get(gender_column) or "").strip()

                if not raw_name:
                    errors.append(
                        f"Ligne {line_number} : prénom vide."
                    )
                    continue

                normalized_gender = normalize_text(raw_gender)
                gender = GENDER_MAPPING.get(normalized_gender)

                if gender is None:
                    errors.append(
                        f"Ligne {line_number} : sexe inconnu "
                        f"« {raw_gender} »."
                    )
                    continue

                name = " ".join(raw_name.split())
                normalized_name = name.casefold()

                valid_row_count += 1

                if normalized_name not in candidates:
                    candidates[normalized_name] = (
                        name,
                        gender,
                    )

        if errors:
            displayed_errors = "\n".join(errors[:10])

            if len(errors) > 10:
                displayed_errors += (
                    f"\n... et {len(errors) - 10} autre(s) erreur(s)."
                )

            raise CommandError(
                f"{len(errors)} erreur(s) détectée(s). "
                "Import annulé :\n"
                f"{displayed_errors}"
            )

        return candidates, valid_row_count