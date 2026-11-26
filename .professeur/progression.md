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
- Mis à jour : 2026-11-25
- Indice : a créé `feat/backend-scaffold` avec la commande fournie ; expliqué switch -c, point de départ, fichiers non commités ; après merge, a trouvé seul `-d` via `git branch -h` et expliqué juste -d vs -D, suppression locale OK ; suppression distante `git push -d origin <branche>` après 3 essais (ordre des arguments, origin/x pris pour un seul mot) ; notion de ref expliquée ; 2e cycle : a composé seul `git switch -c ci/add-api-tests`, puis `git branch -d ... && git push -d origin ...` après merge ; 2026-11-25 (après 3 semaines de pause) : avait oublié `-u` et les deux commandes de suppression → redescendu à Vu ; même jour, PR suivante : a enchaîné seul `switch master && pull && branch -d && push -d origin` (fiche cycle de vie dispo)

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
- Indice : format maîtrisé (5 messages du découpage), mais choix du type fragile : `feat` sur de la mise en place, puis `fix` puis `build` pour un renommage ; a choisi `refactor` après le tableau des types ; 2026-11-05 : ne se souvenait plus de docs vs chore, fiche mémo créée ; nom de branche CI trouvé en 5 essais (`:` interdit, feat→ci, trop vague, parenthèses) → `ci/add-api-tests` ; 2026-11-25 : premier commit avec corps (`-m` titre + `-m` corps, guillemets simples), corps rédigé seul puis corrigé (anglais francisé, oubli d'un changement) ; tend encore à décrire le mécanisme plutôt que le comportement

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
- Statut : Confirmé
- Mis à jour : 2026-11-25
- Indice : 2026-11-25 : a anticipé seul le besoin de stash avant de revenir sur master, enchaîné `switch && pull && stash pop` (refait l'erreur du chemin sans `push`) ; avant : bloqué par un switch (modifs locales) ; a proposé seul `git stash` (avec un `.` en trop) ; `pop` donné après 2 indices ; a choisi `apply` sans saisir la différence, puis après l'analogie de l'étagère a prédit juste l'effet sur `git stash list` (apply garde, pop vide) ; a vérifié puis nettoyé avec `drop && list` (sous-commandes nommées par moi)

### Workflow GitHub Actions : on, paths, jobs, steps, uses/run, defaults (GitHub Actions)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-05
- Indice : a listé seul les étapes (oubli checkout + deps) ; a écrit api-ci.yml pas à pas avec clés données en indice ; erreurs : tirets à la racine, `paths` en chaîne, `working_directory` (underscore, niveau run manquant, valeur `cd ...`), nom d'étape checkout faux, `pytest core/tests` ; croyait qu'une PR utilisait l'ancien workflow ; a bien compris steps séquentiels vs jobs parallèles

### Jobs dépendants : needs, outputs, if, permissions (GitHub Actions)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-05
- Indice : a deviné seul que les jobs doivent partager une info via needs + if ; a écrit outputs (`${{ steps.filter.outputs.api }}`) et le `if` correct après explication des 3 maillons ; `permissions` donné en forme générale, a choisi `read` ; CI verte (detect 6s, test 15s) ; 2026-11-25 : cas « skip » vérifié sur la PR docs (test Required sauté, PR mergeable)

### Protection de branche : rulesets (GitHub)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-05
- Indice : a trouvé seul les 2 règles clés (pas de push direct, pas de merge rouge) ; a configuré le ruleset (oubli de la cible) ; a trouvé seul que le filtre `paths` + check requis bloquerait les PR hors API ; a choisi la solution propre (job de détection)

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

### Secrets et variables d'environnement (django-environ) (Django)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-25
- Indice : a su pourquoi la SECRET_KEY ne doit pas être dans le code ; a écrit seul la lecture via django-environ (env, read_env, DEBUG en bool) depuis la doc ; .env.example compris ; a anticipé seul que la CI casserait sans les variables

### Substitution de commande `$(...)` (shell)
- Domaine : général
- Statut : Vu
- Mis à jour : 2026-11-25
- Indice : a voulu écrire la clé sans l'afficher (bon réflexe) ; a inversé les couches echo/python, commande complète donnée

### Docker Compose : services, ports, volumes (Docker)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-25
- Indice : ne se souvenait plus de la structure (générée par IA avant) ; a rempli le squelette (erreurs : DATABASE_URL dans le conteneur, port 5176, chemin du volume) ; a compris le conflit avec le Postgres Windows sur 5432 ; a ajouté Redis seul

### Celery et Redis (broker, worker) (Celery)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-25
- Indice : ne comprenait pas Redis ; analogie du restaurant ; croyait Redis bloqué en cas de panne Discord ; celery.py recopié de la doc puis expliqué ligne par ligne ; worker lancé avec succès

### Service containers et health check (GitHub Actions)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-25
- Indice : a ajouté un service Postgres à la CI (pensait à une step) ; health check repris de la doc GitHub ; a compris qu'un service Redis était inutile pour l'instant

### JWT : signature, JWKS, vérification (général)
- Domaine : général
- Statut : Vu
- Mis à jour : 2026-11-25
- Indice : pensait qu'un JWT était chiffré (« décrypter ») ; signé vs chiffré, secret partagé vs paire de clés, JWKS et `kid` expliqués ; Supabase local en ES256

### Classe d'authentification DRF (DRF)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-25
- Indice : a écrit core/authentication.py étape par étape (lecture en-tête, split Bearer, PyJWKClient, jwt.decode, SupabaseUser) ; perdu plusieurs fois (try/except inversé — code donné à tort, recadré ; noms classe/variable inversés ; return oublié) ; 401 vs 403 et `authenticate_header` découverts via le test rouge ; faux positif Pylance ; en fin de session : « j'ai rien compris de ce qu'on vient de faire » → vue d'ensemble à reprendre ; 2026-11-26 : après réexplication courte (401 = refus + type de ticket), a prédit juste 403 sans la méthode

### Mock avec monkeypatch (pytest)
- Domaine : spécifique
- Statut : Vu
- Mis à jour : 2026-11-26
- Indice : a compris pourquoi ne pas appeler Supabase en test (CI) ; analogie du videur ; a écrit FakeKey + fausse fonction + setattr après plusieurs erreurs (tuple au lieu de dict, import datetime, setattr avec appel au lieu de la fonction, fonction hors du test, test sans assert qui passait, concat PHP `.`) ; test vert avec vraies assertions

### Bases de Git : commit, push, pull (Git)
- Domaine : général
- Statut : Déclaré
- Mis à jour : 2026-11-05
- Indice : déclaré à la calibration ; après le merge de la PR, a trouvé seul `git switch master && git pull` avec la bonne raison (master local en retard sur origin)
