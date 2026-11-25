# Cycle de vie d'une branche (Git + GitHub)

> Mise à jour : 2026-11-25

Toutes les étapes, de la création au ménage après le merge. Les `<...>` sont à remplacer par tes valeurs.

## 1. Partir d'un master à jour
```bash
git switch master
git pull
```

## 2. Créer la branche
```bash
git switch -c <type>/<nom-court>
```
- Nom : `type/mots-en-tirets`, avec le même type que les commits (`feat`, `fix`, `docs`, `ci`...). Pas de `:`, de parenthèses ni d'espaces.
- Les modifications non commitées suivent sur la nouvelle branche.

## 3. Travailler et commiter
```bash
git status
git add <fichiers>
git commit -m "<type>(<périmètre>): <description>"
```
- Avec un corps (détails) : `git commit -m "<titre>" -m '<corps>'`. Mets le corps entre guillemets simples s'il contient des backticks.
- Corriger le **dernier** commit, s'il n'est **pas encore poussé** : `git commit --amend -m "<nouveau message>"`.

## 4. Premier push
```bash
git push -u origin <branche>
```
- `-u` lie ta branche locale à celle de GitHub. Les fois suivantes, un simple `git push` suffit.

## 5. Ouvrir la PR
- Avec le lien affiché par GitHub après le push, ou depuis l'onglet « Pull requests ».
- Description : Quoi / Pourquoi / Comment vérifier / Notes.
- Attends que les vérifications soient vertes (ou sautées), puis fusionne.

## 6. Revenir sur master après le merge
```bash
git switch master
git pull
```
Si Git refuse de changer de branche à cause de modifications en cours :
```bash
git stash
git switch master
git pull
git stash pop
```
- `stash` met tes modifications de côté, et `pop` les réapplique puis les retire de la pile.
- `git stash list` affiche ce qui est encore de côté.

## 7. Supprimer la branche
```bash
git branch -d <branche>
git push -d origin <branche>
```
- `-d` refuse de supprimer une branche non fusionnée, c'est un garde-fou. `-D` force la suppression, à réserver aux branches ratées.
- Vérifier : `git branch -a` ne doit plus montrer que `master`.

## Pièges fréquents
- **Commande sans `!`** dans Claude Code : elle part comme un message et ne s'exécute pas.
- **`main` au lieu de `master`** : vérifie le nom de ta branche principale avec `git branch`.
- **`git stash <fichier>`** : refusé. Utilise `git stash` seul, ou `git stash push <fichier>`.
- **`git push -d origin/<branche>`** : c'est un seul mot pour Git. Il faut un espace : `origin <branche>`.
- **Oublier `git pull`** après le merge : ton master local reste en retard.

## Pour aller plus loin
- `git fetch --prune` · *pas encore vu* : nettoie les signets `origin/...` des branches supprimées sur GitHub.
- `gh pr create` · *pas encore vu* : créer la PR depuis le terminal.
