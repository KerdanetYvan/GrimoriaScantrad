# Grimoria — Back-office équipe (pipeline de scantrad)

Date : 2026-08-10
Statut : En cours de revue

## Contexte

Grimoria est une plateforme de scantrad pensée au départ pour une équipe unique
(à l'origine "Archéologue Scantrad"), avec une évolution possible vers une
plateforme multi-équipes à étudier plus tard. Le nom de la plateforme n'est pas
lié au nom d'une équipe en particulier — c'est un clin d'œil au thème de la
découverte/l'ancien (un "grimoire" qu'on retrouve et qu'on lit), indépendant de
la spécialité de l'équipe fondatrice (reprise de projets abandonnés).

Une plateforme de scantrad complète (à la Mangakawaii) regroupe plusieurs
sous-systèmes largement indépendants : catalogue public + lecteur, back-office
équipe (upload/gestion des chapitres), comptes/communauté (commentaires,
favoris), recherche/découverte. Ce document ne couvre que le premier
sous-projet retenu : **le back-office équipe**, c'est-à-dire l'outil interne
permettant à l'équipe de produire un chapitre, de la planche brute jusqu'à
l'export final. Les autres briques (catalogue public, communauté, bot Discord
premium avec abonnement) sont hors scope et feront l'objet de leurs propres
cycles brainstorming → plan → implémentation.

## Objectifs

- Permettre à une équipe de suivre l'avancement d'un chapitre, planche par
  planche, à travers un pipeline de production (raw → clean/trad → edit →
  check).
- Permettre un travail flexible : un membre peut s'auto-assigner sur une ou
  plusieurs étapes selon ses compétences, planche par planche.
- Fournir un point d'entrée unique (lien d'invitation) pour rejoindre
  l'équipe et accéder au back-office.
- Notifier l'équipe des événements clés via un webhook Discord simple.
- Produire un export des planches finales une fois un chapitre entièrement
  validé.

## Non-objectifs (hors scope de ce sous-projet)

- Catalogue public / lecteur pour les lecteurs finaux.
- Comptes lecteurs, commentaires, favoris, recherche.
- Bot Discord avec routage de notifications par canal/événement et logique
  d'abonnement payant (sous-projet futur séparé, avec sa propre réflexion sur
  la facturation).
- Support de plusieurs équipes simultanées dans la logique métier (le modèle
  de données le permet nativement, mais aucune fonctionnalité multi-équipe —
  facturation, isolation avancée, etc. — n'est développée ici).

## Workflow de production

Chaque planche (page) d'un chapitre passe par 4 étapes suivies
indépendamment : **clean**, **trad**, **edit**, **check**. La planche raw
(scan brut) est le point de départ, uploadée par le lead à la création du
chapitre — ce n'est pas une étape de production en soi.

Dépendances entre étapes :

- **clean** et **trad** peuvent démarrer dès que le raw existe, en parallèle.
- **edit** ne peut démarrer que lorsque clean ET trad sont tous les deux
  `done` sur la planche.
- **check** ne peut démarrer que lorsque edit est `done`.
- Si **check** échoue, la planche est renvoyée vers l'étape concernée
  (souvent edit ou trad) avec un commentaire explicatif ; l'étape repasse en
  statut `rework` et les étapes suivantes sont réinitialisées.

Un membre peut avoir plusieurs "rôles pipeline" (compétences) et choisir,
planche par planche, sur quelle(s) étape(s) il s'auto-assigne — il n'y a pas
de workflow d'attribution centralisée par un lead. La validation d'une étape
est auto-déclarée par le membre qui l'exécute (pas de validation par un
tiers avant déblocage de l'étape suivante).

Le livrable de l'étape **trad** est un texte simple (script de traduction par
planche, sans positionnement précis) — distinct du livrable de **edit** (image
finale avec texte intégré), même si en pratique un même membre peut
s'auto-assigner sur les deux étapes et les enchaîner.

## Rôles et permissions

- **Lead** : peut créer une série/un chapitre, uploader les raws initiaux,
  générer des liens d'invitation, gérer les membres et leurs rôles pipeline,
  accéder à `/team/settings`.
- **Membre** : dispose d'un sous-ensemble de rôles pipeline (`clean`, `trad`,
  `edit`, `check`) déterminant sur quelles étapes il peut s'auto-assigner.
  Une équipe peut avoir plusieurs leads.

## Architecture

- **Frontend** : Next.js, hébergé sur Vercel, domaine wildcard.
  - Domaine racine : zone publique (hors scope de ce sous-projet — reste un
    placeholder minimal) + `/login` (connexion via Supabase Auth) + page
    d'accueil connectée listant les équipes du membre avec un bouton
    "Dashboard `<nom de la team>`" par équipe.
  - Sous-domaine `<team>.<domaine>` : back-office de l'équipe.
  - Un middleware Next.js route selon le header `Host` (sous-domaine présent
    → back-office ; racine → zone publique).
  - Le cookie de session Supabase est scopé sur le domaine parent
    (`.domaine`) pour rester valide en passant du domaine racine vers un
    sous-domaine, sans reconnexion.
- **Backend** : Django + Django REST Framework, hébergé sur OVH. Porte toute
  la logique métier : pipeline, permissions par rôle, invitations, export,
  déclenchement des notifications.
  - Vérifie le JWT Supabase à chaque requête (JWKS/secret Supabase) pour
    identifier l'utilisateur, puis applique ses propres règles de permission
    (appartenance à la team, rôle lead, rôles pipeline).
- **Supabase self-hosted (sur OVH)** :
  - *Auth (GoTrue)* — gère comptes et sessions, émet les JWT. Source de
    vérité pour l'identité des utilisateurs.
  - *Postgres* — instance unique : schéma `auth` géré par Supabase pour les
    utilisateurs, tables métier Django (Team, Chapter, Planche, ...) dans le
    même Postgres, référençant l'UUID utilisateur Supabase en clé étrangère.
  - *Storage* — images raw/clean/edit par planche, et zips d'export.
  - *Realtime* — installé mais non branché pour ce MVP ; disponible pour un
    besoin futur (ex. dashboard en direct).
- **Notifications Discord** : envoi via une tâche asynchrone (Celery), en
  best-effort, derrière un point d'entrée unique côté Django
  (`notify(team, event_type, payload)`). L'équipe configure une seule URL de
  webhook (`Team.discord_webhook_url`) recevant tous les événements. Ce
  découplage permet de remplacer l'implémentation (ex. bot Discord premium
  avec routage par canal) sans toucher au code du pipeline — voir
  Non-objectifs.

## Modèle de données

**Team** — `id`, `name`, `slug` (sous-domaine), `discord_webhook_url`,
`created_at`

**TeamMembership** — lie un utilisateur Supabase (`user_id`) à une `Team` :
- `is_lead` (booléen)
- `pipeline_roles` (sous-ensemble de `{clean, trad, edit, check}`)

**Invite** — `token`, `team_id`, `created_by`, `expires_at`, `used_at`
(nullable). À l'usage : crée le compte Supabase si besoin, crée/complète la
`TeamMembership` correspondante.

**Series** — `id`, `team_id`, `name`, `slug`

**Chapter** — `id`, `series_id`, `number`, `title`,
`status` (`in_progress` / `ready` / `exported`), `created_by`, `created_at`

**Planche** — `id`, `chapter_id`, `page_number`, `raw_image` (réf. Storage)

**PlancheStep** — une ligne par étape (`clean`, `trad`, `edit`, `check`) et
par planche :
- `status` (`locked` / `available` / `in_progress` / `done` / `rework`)
- `assigned_to` (nullable, auto-assignation)
- `deliverable` (image pour clean/edit, texte pour trad, vide pour check)
- `rework_comment` (rempli si un check échoue et renvoie vers cette étape)

La logique de dépendance entre étapes (voir Workflow) est portée par Django
et recalculée à chaque changement de statut — elle n'est pas encodée dans le
schéma lui-même.

**Export** — `id`, `chapter_id`, `generated_at`, `file_url` (zip dans
Storage). Généré automatiquement quand toutes les `PlancheStep(check)` d'un
chapitre passent à `done`.

## Pages principales (frontend)

- `/login` (domaine racine) — connexion via Supabase Auth
- `/` (domaine racine, connecté) — liste des équipes du membre, bouton
  "Dashboard `<nom de la team>`" par équipe
- `/invite/[token]` — acceptation d'invitation
- `/dashboard` (`<team>.domaine`) — planches disponibles par étape,
  filtrable selon les `pipeline_roles` du membre connecté
- `/series` et `/series/[slug]/chapters/new` — gestion des séries, création
  de chapitre + upload des raws (lead uniquement)
- `/chapters/[id]` — liste des planches d'un chapitre avec statut par étape
- `/chapters/[id]/planches/[num]` — livrable de l'étape active, action
  "terminer l'étape", commentaire de rework si check échoue
- `/team/members` — invitations et rôles pipeline (lead uniquement)
- `/team/settings` — accès lead uniquement : nom/slug de l'équipe, URL
  webhook Discord

## Gestion des erreurs

- Upload d'image échoue (format/taille invalide, erreur réseau Storage) →
  message clair, le statut de l'étape ne change pas tant que l'upload n'est
  pas confirmé.
- Action sur une étape non autorisée (rôle pipeline manquant, étape encore
  `locked` car dépendances non remplies) → rejet côté API (403 / statut
  invalide), le bouton correspondant n'est pas affiché côté UI.
- Accès à une page réservée au lead (`/team/settings`, création de chapitre)
  par un non-lead → 403.
- Token d'invitation expiré ou déjà utilisé → message explicite, le lead
  peut en regénérer un.
- Génération de l'export échoue (ex. image manquante) → le chapitre reste en
  `ready` (pas `exported`), erreur loggée et consultable par le lead, retry
  possible.
- Webhook Discord indisponible (URL invalide, channel supprimé) → échec
  loggé côté Django, best-effort via Celery avec retry limité, ne bloque
  jamais le pipeline.

## Tests

- **Backend (Django)** : tests unitaires sur la logique de dépendance du
  pipeline (déblocage d'étapes, transitions de statut, rework), tests
  d'intégration API (permissions par rôle/lead, flow d'invitation,
  génération d'export).
- **Frontend** : tests de composants sur l'affichage conditionnel selon rôle
  (étapes disponibles/verrouillées, accès `/team/settings`), test
  end-to-end du parcours critique (upload raw → clean → trad → edit → check
  → export) via Playwright.
- Pas de tests de charge prévus pour ce MVP (équipe unique, faible
  volumétrie).

## Points en suspens / suivi

- Nom de domaine définitif non encore choisi (ce document utilise
  `<team>.domaine` comme placeholder).
- Le dossier de travail local s'appelle encore `ArcheologueScantrad` — un
  renommage en `Grimoria` est prévu mais n'a pas pu être effectué depuis la
  session en cours (verrou du répertoire de travail) ; à faire manuellement.
