import csv
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from api.first_name_origins import FIRST_NAME_ORIGIN_IDS
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

ORIGIN_MAPPING = {
    normalize_text(origin_id): origin_id
    for origin_id in FIRST_NAME_ORIGIN_IDS
}


class Command(BaseCommand):
    help = (
        "Importe ou met à jour des prénoms depuis un fichier CSV contenant "
        "prenom, sexe, origine et signification."
    )

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

        existing_first_names = {
            first_name.name.casefold(): first_name
            for first_name in FirstName.objects.all()
        }

        first_names_to_create: list[FirstName] = []
        first_names_to_update: list[FirstName] = []

        for normalized_name, candidate in candidates.items():
            name, gender, origin, meaning = candidate
            existing_first_name = existing_first_names.get(normalized_name)

            if existing_first_name is None:
                first_names_to_create.append(
                    FirstName(
                        name=name,
                        gender=gender,
                        origin=origin,
                        meaning=meaning,
                    )
                )
                continue

            has_changed = any(
                (
                    existing_first_name.name != name,
                    existing_first_name.gender != gender,
                    existing_first_name.origin != origin,
                    existing_first_name.meaning != meaning,
                )
            )

            if not has_changed:
                continue

            existing_first_name.name = name
            existing_first_name.gender = gender
            existing_first_name.origin = origin
            existing_first_name.meaning = meaning
            existing_first_name.updated_at = timezone.now()

            first_names_to_update.append(existing_first_name)

        with transaction.atomic():
            FirstName.objects.bulk_create(
                first_names_to_create,
                batch_size=1000,
            )

            FirstName.objects.bulk_update(
                first_names_to_update,
                fields=(
                    "name",
                    "gender",
                    "origin",
                    "meaning",
                    "updated_at",
                ),
                batch_size=1000,
            )

        created_count = len(first_names_to_create)
        updated_count = len(first_names_to_update)
        unchanged_count = len(candidates) - created_count - updated_count
        duplicated_row_count = valid_row_count - len(candidates)

        self.stdout.write(
            self.style.SUCCESS(
                "Import terminé : "
                f"{valid_row_count} ligne(s) valide(s), "
                f"{created_count} prénom(s) créé(s), "
                f"{updated_count} prénom(s) mis à jour, "
                f"{unchanged_count} prénom(s) inchangé(s), "
                f"{duplicated_row_count} doublon(s) dans le CSV, "
                "0 erreur."
            )
        )

    def read_csv(
        self,
        csv_path: Path,
    ) -> tuple[dict[str, tuple[str, str, str, str]], int]:
        candidates: dict[str, tuple[str, str, str, str]] = {}
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
                "origine",
                "signification",
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
            origin_column = columns["origine"]
            meaning_column = columns["signification"]

            for line_number, row in enumerate(reader, start=2):
                raw_name = (row.get(first_name_column) or "").strip()
                raw_gender = (row.get(gender_column) or "").strip()
                raw_origin = (row.get(origin_column) or "").strip()
                raw_meaning = (row.get(meaning_column) or "").strip()

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

                if not raw_origin:
                    errors.append(
                        f"Ligne {line_number} : origine vide."
                    )
                    continue

                normalized_origin = normalize_text(raw_origin)
                origin = ORIGIN_MAPPING.get(normalized_origin)

                if origin is None:
                    errors.append(
                        f"Ligne {line_number} : origine inconnue "
                        f"« {raw_origin} »."
                    )
                    continue

                if not raw_meaning:
                    errors.append(
                        f"Ligne {line_number} : signification vide."
                    )
                    continue

                name = " ".join(raw_name.split())
                meaning = " ".join(raw_meaning.split())
                normalized_name = name.casefold()

                valid_row_count += 1

                candidates.setdefault(
                    normalized_name,
                    (
                        name,
                        gender,
                        origin,
                        meaning,
                    ),
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