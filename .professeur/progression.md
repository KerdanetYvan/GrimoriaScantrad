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
- Statut : Confirmé
- Mis à jour : 2026-11-05
- Indice : a créé `feat/backend-scaffold` avec la commande fournie ; expliqué switch -c, point de départ, fichiers non commités ; après merge, a trouvé seul `-d` via `git branch -h` et expliqué juste -d vs -D, suppression locale OK ; suppression distante `git push -d origin <branche>` après 3 essais (ordre des arguments, origin/x pris pour un seul mot) ; notion de ref expliquée ; 2e cycle : a composé seul `git switch -c ci/add-api-tests`, puis `git branch -d ... && git push -d origin ...` après merge

### Lire la synopsis d'une aide (`-h`, crochets, chevrons) (général)
- Domaine : général
- Statut : Vu
- Mis à jour : 2026-11-05
- Indice : bon réflexe de lire `-h` seul (branch, push) ; a tapé les crochets littéralement et mis le nom du projet au lieu de `origin` ; convention [] / <> et découpage en arguments expliqués

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
- Statut : Infirmé
- Mis à jour : 2026-11-04
- Indice : format maîtrisé (5 messages du découpage), mais choix du type fragile : `feat` sur de la mise en place, puis `fix` puis `build` pour un renommage ; a choisi `refactor` après le tableau des types ; 2026-11-05 : ne se souvenait plus de docs vs chore, fiche mémo créée ; nom de branche CI trouvé en 5 essais (`:` interdit, feat→ci, trop vague, parenthèses) → `ci/add-api-tests`

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

### Upstream / branche de suivi (Git)
- Domaine : général
- Statut : Confirmé
- Mis à jour : 2026-11-05
- Indice : a rencontré « no upstream branch », a poussé avec `-u` (commande suggérée par Git), puis `git push` seul au commit suivant ; 2026-11-05 : a composé seul `git push -u origin ci/add-api-tests` avec la bonne raison

### Utilité d'une PR en solo (Git)
- Domaine : général
- Statut : Confirmé
- Mis à jour : 2026-11-04
- Indice : a expliqué seul : point de contrôle CI avant merge + archive à relire plus tard

### Stash (Git)
- Domaine : général
- Statut : Vu
- Mis à jour : 2026-11-05
- Indice : bloqué par un switch (modifs locales) ; a proposé seul `git stash` (avec un `.` en trop) ; `pop` donné après 2 indices ; a choisi `apply` sans saisir la différence, puis après l'analogie de l'étagère a prédit juste l'effet sur `git stash list` (apply garde, pop vide) ; a vérifié puis nettoyé avec `drop && list` (sous-commandes nommées par moi)

### Workflow GitHub Actions : on, paths, jobs, steps, uses/run, defaults (GitHub Actions)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-05
- Indice : a listé seul les étapes (oubli checkout + deps) ; a écrit api-ci.yml pas à pas avec clés données en indice ; erreurs : tirets à la racine, `paths` en chaîne, `working_directory` (underscore, niveau run manquant, valeur `cd ...`), nom d'étape checkout faux, `pytest core/tests` ; croyait qu'une PR utilisait l'ancien workflow ; a bien compris steps séquentiels vs jobs parallèles

### YAML (général)
- Domaine : général
- Statut : Vu
- Mis à jour : 2026-11-05
- Indice : déjà croisé (docker-compose) sans rien retenir ; mapping vs liste confondus au début puis corrigés seul ; piège des nombres non quotés (3.12) expliqué

### Fins de ligne et .gitattributes (Git)
- Domaine : général
- Statut : Vu
- Mis à jour : 2026-11-05
- Indice : ne savait pas ce qu'étaient LF/CRLF ; a choisi seul LF avec la bonne raison (serveurs Linux, `\r` dans les scripts) ; a écrit `* text=auto eol=lf` après 2 erreurs (motif manquant, `eof`) ; renormalize lancé (aucun fichier changé)

### Motifs de fichiers (glob : *, **) (général)
- Domaine : général
- Statut : Vu
- Mis à jour : 2026-11-05
- Indice : utilisé `apps/api/**` sans le savoir ; `*`, `**`, motif sans `/` expliqués

### Bases de Git : commit, push, pull (Git)
- Domaine : général
- Statut : Déclaré
- Mis à jour : 2026-11-05
- Indice : déclaré à la calibration ; après le merge de la PR, a trouvé seul `git switch master && git pull` avec la bonne raison (master local en retard sur origin)
