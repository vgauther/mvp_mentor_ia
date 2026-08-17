#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INFRASTRUCTURE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

COMPOSE_FILE="${INFRASTRUCTURE_DIR}/compose.yml"
ENV_FILE="${INFRASTRUCTURE_DIR}/.env"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/mentor-ia}"
TIMESTAMP="$(date +'%Y-%m-%d_%H%M%S')"

usage() {
    echo "Utilisation : $0 <django|keycloak> <fichier.dump>" >&2
}

if [[ "$#" -ne 2 ]]; then
    usage
    exit 1
fi

TARGET="$1"
DUMP_FILE="$2"

case "${TARGET}" in
    django)
        DATABASE_SERVICE="postgres"
        APPLICATION_SERVICE="backend"
        BACKUP_PREFIX="django_"
        ;;
    keycloak)
        DATABASE_SERVICE="keycloak-postgres"
        APPLICATION_SERVICE="keycloak"
        BACKUP_PREFIX="keycloak_"
        ;;
    *)
        echo "Erreur : la cible doit être 'django' ou 'keycloak'." >&2
        usage
        exit 1
        ;;
esac

command -v docker >/dev/null 2>&1 || {
    echo "Erreur : Docker est introuvable." >&2
    exit 1
}

command -v grep >/dev/null 2>&1 || {
    echo "Erreur : grep est introuvable." >&2
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

[[ -f "${DUMP_FILE}" ]] || {
    echo "Erreur : sauvegarde introuvable : ${DUMP_FILE}" >&2
    exit 1
}

[[ -s "${DUMP_FILE}" ]] || {
    echo "Erreur : le fichier de sauvegarde est vide." >&2
    exit 1
}

DUMP_DIRECTORY="$(cd -- "$(dirname -- "${DUMP_FILE}")" && pwd)"
DUMP_FILE="${DUMP_DIRECTORY}/$(basename -- "${DUMP_FILE}")"
DUMP_NAME="$(basename -- "${DUMP_FILE}")"

case "${DUMP_NAME}" in
    "${BACKUP_PREFIX}"*.dump)
        ;;
    *)
        echo "Erreur : ${DUMP_NAME} ne correspond pas à la base ${TARGET}." >&2
        exit 1
        ;;
esac

COMPOSE_COMMAND=(
    docker compose
    --env-file "${ENV_FILE}"
    -f "${COMPOSE_FILE}"
)

is_running() {
    "${COMPOSE_COMMAND[@]}" ps --status running --services |
        grep -Fxq -- "$1"
}

if ! is_running "${DATABASE_SERVICE}"; then
    echo "Erreur : le service ${DATABASE_SERVICE} n'est pas démarré." >&2
    exit 1
fi

echo "Vérification de l'archive PostgreSQL..."

if ! "${COMPOSE_COMMAND[@]}" exec -T "${DATABASE_SERVICE}" \
    pg_restore --list >/dev/null < "${DUMP_FILE}"; then
    echo "Erreur : l'archive PostgreSQL est invalide ou endommagée." >&2
    exit 1
fi

echo
echo "ATTENTION : la base ${TARGET} actuelle va être remplacée."
echo "Archive utilisée : ${DUMP_FILE}"
echo
read -r -p "Écrivez RESTAURER ${TARGET} pour confirmer : " CONFIRMATION

if [[ "${CONFIRMATION}" != "RESTAURER ${TARGET}" ]]; then
    echo "Restauration annulée."
    exit 0
fi

mkdir -p "${BACKUP_DIR}"

SAFETY_BACKUP="${BACKUP_DIR}/${TARGET}_before_restore_${TIMESTAMP}.dump"
SAFETY_TEMP="${SAFETY_BACKUP}.tmp"

APPLICATION_STOPPED=0
DESTRUCTIVE_PHASE=0
RESTORE_COMPLETED=0

cleanup() {
    rm -f -- "${SAFETY_TEMP}"

    if [[ "${APPLICATION_STOPPED}" -eq 1 ]]; then
        if [[ "${DESTRUCTIVE_PHASE}" -eq 0 ]]; then
            echo "Redémarrage du service ${APPLICATION_SERVICE}..."
            "${COMPOSE_COMMAND[@]}" up -d "${APPLICATION_SERVICE}" || true
        elif [[ "${RESTORE_COMPLETED}" -eq 0 ]]; then
            echo "Erreur : la restauration a échoué." >&2
            echo "Le service ${APPLICATION_SERVICE} reste arrêté par sécurité." >&2
            echo "Sauvegarde de secours : ${SAFETY_BACKUP}" >&2
        else
            echo "La restauration est terminée, mais le service n'a pas redémarré." >&2
        fi
    fi
}

trap cleanup EXIT

if is_running "${APPLICATION_SERVICE}"; then
    echo "Arrêt temporaire du service ${APPLICATION_SERVICE}..."
    "${COMPOSE_COMMAND[@]}" stop "${APPLICATION_SERVICE}"
    APPLICATION_STOPPED=1
fi

echo "Création d'une sauvegarde de sécurité..."

"${COMPOSE_COMMAND[@]}" exec -T "${DATABASE_SERVICE}" sh -ec '
    export PGPASSWORD="${POSTGRES_PASSWORD}"

    exec pg_dump \
        --username="${POSTGRES_USER}" \
        --dbname="${POSTGRES_DB}" \
        --format=custom \
        --compress=9 \
        --no-owner \
        --no-privileges
' > "${SAFETY_TEMP}"

if [[ ! -s "${SAFETY_TEMP}" ]]; then
    echo "Erreur : la sauvegarde de sécurité est vide." >&2
    exit 1
fi

mv -- "${SAFETY_TEMP}" "${SAFETY_BACKUP}"
echo "Sauvegarde de sécurité créée : ${SAFETY_BACKUP}"

DESTRUCTIVE_PHASE=1

echo "Recréation et restauration de la base ${TARGET}..."

"${COMPOSE_COMMAND[@]}" exec -T "${DATABASE_SERVICE}" sh -ec '
    export PGPASSWORD="${POSTGRES_PASSWORD}"

    if [ "${POSTGRES_DB}" = "postgres" ]; then
        echo "Erreur : POSTGRES_DB ne peut pas être postgres pour cette restauration." >&2
        exit 1
    fi

    dropdb \
        --username="${POSTGRES_USER}" \
        --maintenance-db=postgres \
        --if-exists \
        --force \
        "${POSTGRES_DB}"

    createdb \
        --username="${POSTGRES_USER}" \
        --maintenance-db=postgres \
        --owner="${POSTGRES_USER}" \
        "${POSTGRES_DB}"

    exec pg_restore \
        --username="${POSTGRES_USER}" \
        --dbname="${POSTGRES_DB}" \
        --no-owner \
        --no-privileges \
        --exit-on-error
' < "${DUMP_FILE}"

RESTORE_COMPLETED=1

if [[ "${APPLICATION_STOPPED}" -eq 1 ]]; then
    echo "Redémarrage du service ${APPLICATION_SERVICE}..."
    "${COMPOSE_COMMAND[@]}" up -d "${APPLICATION_SERVICE}"
    APPLICATION_STOPPED=0
fi

echo "Restauration de la base ${TARGET} terminée avec succès."
echo "Sauvegarde restaurée : ${DUMP_FILE}"
echo "État précédent conservé dans : ${SAFETY_BACKUP}"
