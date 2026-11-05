# Progression

### Bases du langage (Python)
- Domaine : spécifique
- Statut : Déclaré
- Mis à jour : 2026-11-03
- Indice : déclaré à la calibration (plusieurs projets, mais rouillé)

### Structure d'un projet (Django)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-03
- Indice : se dit en réapprentissage ; manage.py et INSTALLED_APPS expliqués ; a ajouté seul core, rest_framework, django.contrib.postgres (check OK)

### Bases relationnelles : clés étrangères, jointures, migrations (général)
- Domaine : général
- Statut : Déclaré
- Mis à jour : 2026-11-03
- Indice : déclaré à la calibration (« je maîtrise »)

### Asynchrone (JavaScript)
- Domaine : général
- Statut : Déclaré
- Mis à jour : 2026-11-03
- Indice : déclaré à la calibration (pratiqué avec Next et React)

### Environnement virtuel et dépendances (Python)
- Domaine : spécifique
- Statut : Confirmé
- Mis à jour : 2026-11-03
- Indice : a écrit seul `source .venv/Scripts/activate && python manage.py check` après avoir buté sur l'activation (sans venv, puis sans `source`) ; avait déjà justifié requirements.txt / .python-version / .venv, épinglage et LTS vus

### Processus enfant et `source` (shell)
- Domaine : général
- Statut : Confirmé
- Mis à jour : 2026-11-03
- Indice : réutilisé seul `source` + `&&` dans une même commande `!` pour `manage.py check`

### Ce qu'on versionne ou non (Git)
- Domaine : général
- Statut : Confirmé
- Mis à jour : 2026-11-03
- Indice : a classé seul requirements.txt et .python-version (versionnés) vs .venv/ (non), avec la bonne raison

### Branches (Git)
- Domaine : général
- Statut : Vu
- Mis à jour : 2026-11-03
- Indice : a créé `feat/backend-scaffold` avec la commande fournie ; expliqué switch -c, point de départ, fichiers non commités

### Organisation en monorepo (général)
- Domaine : général
- Statut : Vu
- Mis à jour : 2026-11-03
- Indice : a proposé seul un découpage apps/front, back, mobile ; expliqué nommage, outillage JS séparé du Python, CI par chemin

### Zone de staging et commits ciblés (Git)
- Domaine : général
- Statut : Confirmé
- Mis à jour : 2026-11-04
- Indice : a composé seul `git add ... && git restore --staged ... && git status` pour isoler le commit 1 (60b5082) ; avait oublié core/views.py dans le découpage

### Conventional Commits (Git)
- Domaine : général
- Statut : Confirmé
- Mis à jour : 2026-11-04
- Indice : a écrit les 5 messages du découpage scaffold/pytest/health ; tendance à mettre `feat` sur de la mise en place et une majuscule, corrigé après explication (changelog/semver)

### Écrire un test avec pytest (pytest)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-04
- Indice : a écrit core/tests/test_health.py correct (APIClient, 2 assert) mais à partir d'un pseudo-code très guidé ; pytest.ini (settings + python_files) écrit seul ; a prédit juste l'échec (1er assert, 404) et trouvé `.venv/Scripts/pytest` après 2 erreurs (`python pytest`, cd en trop)

### Vues fonctions DRF : @api_view, Response (DRF)
- Domaine : spécifique
- Statut : Confirmé
- Mis à jour : 2026-11-04
- Indice : a écrit seul core/views.py health_check (aidé par l'autocomplétion pour un import, désactivée depuis)

### Routage et include (Django)
- Domaine : spécifique
- Statut : Confirmé
- Mis à jour : 2026-11-04
- Indice : a écrit core/urls.py puis corrigé seul la racine en `include('core.urls')` après une ImportError (avait d'abord pris l'exemple class-based view) ; test vert

### Lire une traceback pytest (général)
- Domaine : général
- Statut : Vu
- Mis à jour : 2026-11-04
- Indice : expliqué (lire de bas en haut, ligne `E` + fichier:ligne) sur l'ImportError de grimoria/urls.py

### Bases de Git : commit, push, pull (Git)
- Domaine : général
- Statut : Déclaré
- Mis à jour : 2026-11-03
- Indice : déclaré à la calibration
