# Mentor IA - MVP

Squelette technique du MVP décrit dans le cahier des charges **MVP Mentor IA**.
Le projet repose sur :

- API Python avec Django et Django REST Framework ;
- authentification OpenID Connect avec Keycloak ;
- application Vue 3 + TypeScript construite par Vite ;
- deux bases PostgreSQL séparées pour Django et Keycloak ;
- orchestration complète avec Docker Compose.

Le socle métier permet maintenant aux administrateurs de préparer une
formation, saisir ses objectifs pédagogiques, déposer ses sources brutes,
créer des quiz structurés, enrichir chaque ressource puis générer un brouillon
de parcours à examiner. Le Trigger Master et HeyGen restent hors de cette
étape.

Dans Docker Desktop, les services sont regroupés sous le projet Compose
`mvp-ia` et tous les conteneurs utilisent le préfixe `mvp-ia-`.

## Arborescence

```text
backend/          API Django et validation des jetons Keycloak
frontend/         application Vue authentifiée
infrastructure/   Docker Compose, realm Keycloak et scripts d'exploitation
```

## Démarrage avec Docker

Prérequis : Docker avec le plugin Compose.

```bash
cp infrastructure/.env.example infrastructure/.env
docker compose \
  --env-file infrastructure/.env \
  -f infrastructure/compose.yml \
  up --build
```

Services disponibles :

| Service | URL locale |
| --- | --- |
| Frontend Vue | http://localhost:5174 |
| API Django | http://localhost:8001/api/health/ |
| Keycloak | http://localhost:8081 |
| Administration Keycloak | http://localhost:8081/admin/ |

Les ports hôtes du MVP sont `5433`, `8081`, `8001` et `5174` afin d'éviter les
collisions courantes avec d'autres services locaux.

Les identifiants de l'administrateur Keycloak sont définis dans
`infrastructure/.env`. Le realm `mentor-ia` est importé automatiquement au
premier démarrage.

## Inscription et rôles

Le realm ne contient aucun compte de démonstration ni mot de passe versionné.
L'inscription est activée depuis l'écran Keycloak et utilise le thème blanc et
bleu de Mentor IA.

Le premier compte qui termine sa première connexion dans l'application devient
automatiquement `admin`. Tous les comptes suivants deviennent `learner`. Django
est la source de vérité de ce rôle applicatif afin que les changements soient
immédiats :

- un administrateur accède au tableau de bord et à l'onglet **Utilisateurs** ;
- il peut promouvoir un apprenant ou rétrograder un autre administrateur ;
- le dernier administrateur ne peut pas être rétrogradé ;
- un apprenant accède uniquement à son espace d'apprentissage.

Les utilisateurs inscrits apparaissent dans l'administration après leur
première connexion à l'application. L'API expose notamment :

- `GET /api/health/` : contrôle public de disponibilité ;
- `GET /api/me/` : identité de l'utilisateur connecté ;
- `GET /api/admin/` : contrôle d'accès réservé au rôle `admin`.
- `GET /api/admin/users/` : liste des profils, réservée aux administrateurs ;
- `PATCH /api/admin/users/<id>/role/` : modification d'un rôle.

## Préparation des formations

L'onglet **Formations** est réservé aux administrateurs. Il permet de :

- créer une formation en brouillon avec un nom de travail et un contexte ;
- ajouter des objectifs pédagogiques ordonnés ;
- déposer des vidéos et PDF, saisir des textes bruts et créer des quiz structurés
  avec des questions à choix unique, à choix multiples ou à réponse courte ;
- lancer un enrichissement séparé des sources originales : transcription des
  vidéos, extraction des PDF, rôle du média, résumé, concepts clés, glossaire et
  mots-clés ;
- générer par IA un brouillon d’arborescence
  `module → chapitre → section` à partir des objectifs et des ressources
  enrichies ;
- valider et publier cette proposition après contrôle automatique de la
  couverture des ressources et des objectifs ;
- télécharger et supprimer les fichiers depuis l'espace privé.

L’enrichissement est activé uniquement lorsque `OPENAI_API_KEY` est configurée
sur le backend. Il utilise un modèle de transcription pour les vidéos et une
sortie structurée pour les métadonnées. Les objectifs pédagogiques ne sont
jamais générés : ils restent saisis manuellement. Lorsque tous les contenus sont
enrichis, le générateur produit un brouillon `module → chapitre → section`,
utilise chaque ressource exactement une fois et signale les objectifs que les
sources ne permettent pas de couvrir. Les fichiers sont
stockés dans le volume Docker persistant
`mvp-ia_backend_media`. Ils ne sont pas servis publiquement : leur téléchargement
passe par un endpoint authentifié et réservé aux administrateurs.

Principaux endpoints :

- `GET|POST /api/admin/trainings/` ;
- `GET|PATCH|DELETE /api/admin/trainings/<id>/` ;
- `GET|POST /api/admin/trainings/<id>/objectives/` ;
- `GET|POST /api/admin/trainings/<id>/units/` ;
- `GET|POST /api/admin/trainings/<id>/raw-materials/` ;
- `POST /api/admin/trainings/<id>/enrichments/generate/` ;
- `POST /api/admin/trainings/<id>/structure/generate/` ;
- `POST /api/admin/trainings/<id>/structure/publish/` ;
- `GET /api/admin/trainings/<id>/raw-materials/<source-id>/download/`.

## API publique des formations

Une API REST versionnée expose en lecture seule les formations dont la
structure a été publiée. Elle ne demande aucun jeton d'authentification :

- `GET /api/public/v1/trainings/` : liste des formations publiées ;
- `GET /api/public/v1/trainings/<id>/` : détail d'une formation, objectifs,
  structure imbriquée et contenus bruts ;
- `GET /api/public/v1/trainings/<id>/raw-materials/<source-id>/file/` : fichier
  original public d'une source PDF ou vidéo.

Les formations en brouillon ou en cours de structuration répondent `404` sur
les routes de détail et ne figurent pas dans la liste. Les routes publiques
n'acceptent que `GET` ; toute écriture reste dans l'API d'administration.

Exemple :

```bash
curl https://formation.example.com/api/public/v1/trainings/
curl https://formation.example.com/api/public/v1/trainings/1/
```

La réponse de détail suit cette forme :

```json
{
  "id": 1,
  "title": "Formation publique",
  "description": "Description du parcours",
  "published_at": "2026-08-17T10:00:00Z",
  "updated_at": "2026-08-17T10:00:00Z",
  "objectives": [
    {
      "id": 1,
      "title": "Maîtriser le sujet",
      "description": "",
      "position": 1
    }
  ],
  "structure": [
    {
      "id": 1,
      "kind": "module",
      "title": "Fondamentaux",
      "notes": "",
      "position": 1,
      "objective_ids": [],
      "raw_material_ids": [],
      "children": []
    }
  ],
  "raw_materials": [
    {
      "id": 1,
      "kind": "text",
      "name": "Première ligne du contenu",
      "content": "Contenu texte brut",
      "quiz_data": {},
      "has_file": false,
      "file_url": null,
      "original_filename": "",
      "mime_type": "",
      "size": 18
    }
  ]
}
```

Pour un texte, la donnée originale se trouve dans `content`. Pour un quiz, elle
se trouve dans `quiz_data`. Pour un PDF ou une vidéo, `file_url` pointe vers le
fichier original et les métadonnées sont fournies dans la même ressource.

En production, le proxy HTTPS doit transmettre `/api/` au service backend et
le domaine public doit figurer dans `DJANGO_ALLOWED_HOSTS`. Si l'API est appelée
directement depuis du JavaScript hébergé sur un autre domaine, ajoutez aussi
l'origine de ce site à `CORS_ALLOWED_ORIGINS`.

## Développement local hors Docker

Backend :

```bash
cp backend/.env.example backend/.env
python -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python backend/manage.py migrate
backend/.venv/bin/python backend/manage.py runserver 8001
```

Frontend :

```bash
cp frontend/.env.example frontend/.env
npm --prefix frontend ci
npm --prefix frontend run dev
```

PostgreSQL et Keycloak doivent être disponibles avec les valeurs des fichiers
`.env` pour ce mode hybride.

## Vérifications

```bash
docker compose \
  --env-file infrastructure/.env \
  -f infrastructure/compose.yml \
  config --quiet

npm --prefix frontend run type-check
npm --prefix frontend run test:unit -- --run
```

## Dépôt cible

Le remote Git attendu pour ce projet est :

```text
git@github.com:vgauther/mvp_mentor_ia.git
```
