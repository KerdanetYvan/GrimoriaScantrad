# Grimoria — Feuille de route du backend

Date : 2026-11-25
Spec de référence : `docs/specs/2026-08-10-back-office-equipe-design.md`

Une étape = une branche = une PR. Chaque étape donne le **but** et ce qui
prouve qu'elle est **finie**, sans imposer le code : c'est à construire.

## 1. Squelette du projet ✅

- But : projet Django dans `apps/api`, pytest, endpoint de santé, CI.
- Fini : `GET /api/health/` répond `{"status": "ok"}`, la CI est verte.

## 2. Configuration et base de données

- But : sortir les secrets du code (`.env` avec django-environ), brancher
  Postgres, poser le squelette de Celery.
- Fini : plus aucun secret dans `settings.py` ; `manage.py check` et les tests
  passent sur Postgres ; un `.env.example` documente les variables.

## 3. Authentification Supabase

- But : reconnaître l'utilisateur à partir du jeton (JWT) émis par Supabase.
- Fini : une requête avec un jeton valide est authentifiée, une requête sans
  jeton ou avec un jeton invalide reçoit un 401 ; testé.

## 4. Équipes et membres

- But : modèles `Team` et `TeamMembership` (lead, rôles pipeline).
- Fini : migrations appliquées ; un membre ne peut pas être deux fois dans la
  même équipe ; testé.

## 5. Permissions

- But : règles réutilisables « est membre », « est lead », « a ce rôle
  pipeline ».
- Fini : chaque règle a ses tests, cas autorisé et cas refusé.

## 6. API des équipes

- But : lister mes équipes, voir une équipe, modifier ses réglages (lead).
- Fini : endpoints testés, y compris un 403 pour un non-lead qui modifie.

## 7. Invitations

- But : le lead crée un lien d'invitation, un utilisateur l'accepte.
- Fini : l'acceptation crée l'appartenance à l'équipe ; un lien expiré ou déjà
  utilisé est refusé ; testé.

## 8. Gestion des membres

- But : lister les membres, modifier leur rôle de lead et leurs rôles
  pipeline (lead).
- Fini : endpoints testés, droits compris.

## 9. Séries, chapitres et planches

- But : modèles `Series`, `Chapter`, `Planche`, `ChapterStep` (assignation par
  chapitre) et `PlancheStep` (avancement par planche) ; création d'un chapitre
  avec ses planches.
- Fini : créer un chapitre génère ses 4 `ChapterStep` et 4 `PlancheStep` par
  planche ; testé.

## 10. Logique du pipeline

- But : calculer quelles étapes se débloquent (clean et trad en parallèle,
  edit après les deux, check après edit), y compris l'exception trad + edit
  par la même personne.
- Fini : chaque règle de dépendance a son test, exception comprise.

## 11. Prendre et terminer une étape

- But : un membre s'assigne une étape d'un chapitre, puis termine les
  planches une à une.
- Fini : impossible sans le bon rôle ou si l'étape est déjà prise ; terminer
  une planche débloque la suite ; testé.

## 12. Rework

- But : un check qui échoue renvoie la planche vers l'étape fautive, avec un
  commentaire.
- Fini : l'étape repasse en `rework`, les étapes suivantes sont
  réinitialisées ; testé.

## 13. Notifications Discord

- But : envoyer les événements clés au webhook de l'équipe, en tâche Celery.
- Fini : pas d'envoi sans webhook ; un Discord en panne ne bloque rien ;
  testé sans appeler le vrai Discord.

## 14. Publication et export

- But : le lead publie un chapitre sur Grimoria ou génère un zip, à tout
  moment, avec les règles de la spec (planches éditées seulement, marqué
  incomplet si le chapitre n'est pas entièrement checké).
- Fini : statut de publication et export corrects dans les cas complet et
  incomplet ; testé.
