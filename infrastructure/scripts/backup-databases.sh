#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INFRASTRUCTURE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

COMPOSE_FILE="${INFRASTRUCTURE_DIR}/compose.yml"
ENV_FILE="${INFRASTRUCTURE_DIR}/.env"

BACKUP_DIR="${BACKUP_DIR:-/var/backups/le-bon-prenom}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP="$(date +'%Y-%m-%d_%H%M%S')"

case "${RETENTION_DAYS}" in
    ''|*[!0-9]*)
        echo "Erreur : RETENTION_DAYS doit être un nombre entier positif." >&2
        exit 1
        ;;
esac

command -v docker >/dev/null 2>&1 || {
    echo "Erreur : Docker est introuvable." >&2
    exit 1
}

[[ -f "${COMPOSE_FILE}" ]] || {
    echo "Erreur : fichier Compose introuvable : ${COMPOSE_FILE}" >&2
    exit 1
}

[[ -f "${ENV_FILE}" ]] || {
    echo "Erreur : fichier d'environnement introuvable : ${ENV_FILE}" >&2
    exit 1
}

mkdir -p "${BACKUP_DIR}"

DJANGO_BACKUP="${BACKUP_DIR}/django_${TIMESTAMP}.dump"
KEYCLOAK_BACKUP="${BACKUP_DIR}/keycloak_${TIMESTAMP}.dump"

DJANGO_TEMP="${DJANGO_BACKUP}.tmp"
KEYCLOAK_TEMP="${KEYCLOAK_BACKUP}.tmp"

cleanup() {
    rm -f -- "${DJANGO_TEMP}" "${KEYCLOAK_TEMP}"
}

trap cleanup EXIT

COMPOSE_COMMAND=(
    docker compose
    --env-file "${ENV_FILE}"
    -f "${COMPOSE_FILE}"
)

dump_database() {
    local service_name="$1"
    local temporary_file="$2"
    local final_file="$3"

    echo "Sauvegarde du service ${service_name}..."

    "${COMPOSE_COMMAND[@]}" exec -T "${service_name}" sh -ec '
        export PGPASSWORD="${POSTGRES_PASSWORD}"

        exec pg_dump \
            --username="${POSTGRES_USER}" \
            --dbname="${POSTGRES_DB}" \
            --format=custom \
            --compress=9 \
            --no-owner \
            --no-privileges
    ' > "${temporary_file}"

    if [[ ! -s "${temporary_file}" ]]; then
        echo "Erreur : la sauvegarde de ${service_name} est vide." >&2
        exit 1
    fi

    mv -- "${temporary_file}" "${final_file}"
    echo "Sauvegarde créée : ${final_file}"
}

dump_database "postgres" "${DJANGO_TEMP}" "${DJANGO_BACKUP}"
dump_database "keycloak-postgres" "${KEYCLOAK_TEMP}" "${KEYCLOAK_BACKUP}"

find "${BACKUP_DIR}" \
    -maxdepth 1 \
    -type f \
    \( -name 'django_*.dump' -o -name 'keycloak_*.dump' \) \
    -mtime "+${RETENTION_DAYS}" \
    -delete

echo "Les deux bases PostgreSQL ont été sauvegardées avec succès."
echo "Conservation configurée : ${RETENTION_DAYS} jours."
