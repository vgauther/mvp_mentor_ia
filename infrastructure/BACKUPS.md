# Sauvegarde et restauration des bases PostgreSQL

Le projet possède deux bases PostgreSQL distinctes :

- `postgres` : base utilisée par Django ;
- `keycloak-postgres` : base interne utilisée par Keycloak.

## Emplacement des sauvegardes

Par défaut, les archives sont stockées dans :

```text
/var/backups/le-bon-prenom
```

Les fichiers sont nommés ainsi :

```text
django_YYYY-MM-DD_HHMMSS.dump
keycloak_YYYY-MM-DD_HHMMSS.dump
```

Les sauvegardes utilisent le format personnalisé de PostgreSQL produit par
`pg_dump --format=custom`.

Les fichiers sont protégés avec des permissions restrictives grâce à
`umask 077`.

## Sauvegarde manuelle

Depuis la racine du projet :

```bash
./infrastructure/scripts/backup-databases.sh
```

Le script :

1. vérifie la présence de Docker, du fichier Compose et du fichier `.env` ;
2. sauvegarde la base Django ;
3. sauvegarde la base Keycloak ;
4. refuse de conserver une archive vide ;
5. supprime les sauvegardes ayant dépassé la durée de conservation.

La durée de conservation par défaut est de 30 jours.

Elle peut être modifiée ponctuellement :

```bash
RETENTION_DAYS=60 ./infrastructure/scripts/backup-databases.sh
```

Un autre dossier peut également être utilisé :

```bash
BACKUP_DIR=/autre/emplacement ./infrastructure/scripts/backup-databases.sh
```

## Vérification d'une archive

Vérification d'une sauvegarde Django :

```bash
docker compose \
  --env-file infrastructure/.env \
  -f infrastructure/compose.yml \
  exec -T postgres \
  pg_restore --list \
  < /var/backups/le-bon-prenom/django_DATE_HEURE.dump \
  > /dev/null
```

Vérification d'une sauvegarde Keycloak :

```bash
docker compose \
  --env-file infrastructure/.env \
  -f infrastructure/compose.yml \
  exec -T keycloak-postgres \
  pg_restore --list \
  < /var/backups/le-bon-prenom/keycloak_DATE_HEURE.dump \
  > /dev/null
```

Ces commandes inspectent seulement les archives et ne modifient aucune base.

## Automatisation avec systemd

Créer le dossier de sauvegarde :

```bash
sudo install -d \
  -o victor \
  -g victor \
  -m 700 \
  /var/backups/le-bon-prenom
```

Installer les unités `systemd` :

```bash
sudo install -m 644 \
  infrastructure/systemd/le-bon-prenom-backup.service \
  /etc/systemd/system/le-bon-prenom-backup.service

sudo install -m 644 \
  infrastructure/systemd/le-bon-prenom-backup.timer \
  /etc/systemd/system/le-bon-prenom-backup.timer
```

Activer le timer :

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now le-bon-prenom-backup.timer
```

La sauvegarde est programmée chaque jour à 03:00, heure de Paris.

L'option `Persistent=true` permet à `systemd` de rattraper une sauvegarde
manquée lorsque le VPS était éteint.

Vérifier la programmation :

```bash
systemctl list-timers --all \
  le-bon-prenom-backup.timer \
  --no-pager

systemctl status \
  le-bon-prenom-backup.timer \
  --no-pager
```

## Tester le service systemd

Une exécution manuelle peut être déclenchée avec :

```bash
sudo systemctl start le-bon-prenom-backup.service
```

Consulter ensuite son état et ses journaux :

```bash
systemctl status \
  le-bon-prenom-backup.service \
  --no-pager

journalctl \
  -u le-bon-prenom-backup.service \
  -n 30 \
  --no-pager
```

Le service est de type `oneshot`. Après une exécution réussie, l'état
`inactive (dead)` est donc normal. Le résultat important est :

```text
status=0/SUCCESS
```

## Restaurer une base

> Attention : une restauration supprime et remplace la base actuelle.

Restaurer Django :

```bash
./infrastructure/scripts/restore-database.sh \
  django \
  /var/backups/le-bon-prenom/django_DATE_HEURE.dump
```

Restaurer Keycloak :

```bash
./infrastructure/scripts/restore-database.sh \
  keycloak \
  /var/backups/le-bon-prenom/keycloak_DATE_HEURE.dump
```

Avant la restauration, le script :

1. vérifie l'archive ;
2. demande une confirmation écrite ;
3. arrête temporairement le service applicatif concerné ;
4. crée une sauvegarde de sécurité de l'état actuel ;
5. recrée la base ;
6. restaure l'archive ;
7. redémarre le service applicatif.

Les confirmations demandées sont :

```text
RESTAURER django
RESTAURER keycloak
```

Si une erreur survient après le début de la phase destructive, le service
applicatif reste arrêté par sécurité et le chemin de la sauvegarde de secours
est affiché.

## Limite actuelle

Les sauvegardes sont stockées sur le même VPS que l'application. Elles
protègent contre une mauvaise manipulation ou une corruption logique, mais
pas contre la perte complète du disque ou du VPS.

Une copie chiffrée vers un stockage externe devra être ajoutée ultérieurement
pour disposer d'une véritable sauvegarde hors site.
