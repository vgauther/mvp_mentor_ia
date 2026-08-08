#!/bin/sh

set -eu

realm_file="${1:-infrastructure/keycloak/import/le-bon-prenom-realm.json}"

if ! command -v jq >/dev/null 2>&1; then
  echo "Erreur : jq est nécessaire pour contrôler le realm Keycloak." >&2
  exit 2
fi

if [ ! -f "$realm_file" ]; then
  echo "Erreur : fichier introuvable : $realm_file" >&2
  exit 2
fi

secret_paths=$(jq -r '
  paths(scalars) as $path
  | select(
      any(
        $path[];
        type == "string"
        and test("^(privateKey|secret)$"; "i")
      )
    )
  | $path | map(tostring) | join(".")
' "$realm_file")

if [ -n "$secret_paths" ]; then
  echo "Erreur : le realm exporté contient des clés ou secrets privés :" >&2
  printf '%s\n' "$secret_paths" >&2
  exit 1
fi

jq -e '
  .internationalizationEnabled == true
  and .supportedLocales == ["fr"]
  and .defaultLocale == "fr"
  and (
    .clients[]
    | select(.clientId == "le-bon-prenom-frontend")
    | (.redirectUris | index("http://localhost:5173/*") != null)
      and (.webOrigins | index("http://localhost:5173") != null)
  )
' "$realm_file" >/dev/null || {
  echo "Erreur : la configuration française ou les URLs locales sont incomplètes." >&2
  exit 1
}

echo "Realm Keycloak validé : aucun secret versionné et configuration attendue présente."
