# Conventional Commits et noms de branches (Conventional Commits 1.0.0)

> Mise à jour : 2026-11-05

Une convention pour écrire des messages de commit lisibles et triables : le type dit **quelle sorte de changement** c'est, avant même de lire la description. On réutilise les mêmes types pour nommer les branches et les PR.

## L'essentiel

### Le format
```text
type(périmètre): description courte
```
- `type` : la catégorie du changement (voir le tableau).
- `(périmètre)` : facultatif, la partie du projet touchée (`api`, `web`, `auth`...).
- `description` : en anglais, à l'impératif (« add », pas « added »), minuscule au début, sans point final.

```text
feat(api): add user registration endpoint
fix(web): prevent double submit on login form
docs: explain local setup in readme
```

### Les types
| Type | Quand l'utiliser | Exemple |
| --- | --- | --- |
| `feat` | Nouvelle fonctionnalité **visible pour l'utilisateur** | un endpoint, une page, un bouton |
| `fix` | Correction d'un bug | une erreur 500, un calcul faux |
| `docs` | Uniquement de la documentation, **écrite pour être lue** | README, plan, spec, commentaires d'explication |
| `test` | Ajout ou correction de tests, sans toucher au code testé | un nouveau fichier de test |
| `refactor` | Réorganiser le code **sans changer son comportement** | renommer un dossier, découper une fonction |
| `style` | Pure mise en forme, aucune logique touchée | indentation, espaces, guillemets |
| `build` | Construire ou installer le projet | dépendances, version du langage, Dockerfile |
| `ci` | Configuration de l'intégration continue | workflows GitHub Actions |
| `chore` | Entretien du repo qui ne rentre dans aucune autre case | `.gitignore`, fichiers de suivi |
| `perf` | Amélioration des performances | une requête plus rapide |

### Choisir le type : les questions à se poser, dans l'ordre
1. L'utilisateur de l'appli voit-il une nouveauté ? → `feat`
2. Est-ce que ça corrige un comportement cassé ? → `fix`
3. Le comportement reste identique, seul le code est réorganisé ? → `refactor`
4. Est-ce uniquement des tests ? → `test`
5. Est-ce uniquement un texte écrit pour des humains ? → `docs`
6. Est-ce l'installation ou la construction du projet ? → `build`
7. Est-ce ce qu'un service de CI exécute automatiquement ? → `ci`
8. Rien de tout ça → `chore`

Si un commit mélange plusieurs types, c'est souvent le signe qu'il faut le découper en plusieurs commits.

### Les noms de branches
Même idée, avec un `/` comme séparateur et des tirets entre les mots :

```text
feat/user-registration
fix/login-double-submit
ci/github-actions-tests
```
Court (2 à 4 mots), en minuscules, qui dit ce que fait la branche.

### Le corps et le pied du message · *pas encore vu*
Un commit peut avoir, après une ligne vide, un corps qui explique le **pourquoi**, puis un pied de page (références, ruptures) :

```text
fix(api): reject expired tokens

Tokens were only checked for signature, not expiry date.

Closes #42
```

### Signaler une rupture de compatibilité · *pas encore vu*
Un `!` après le type (`feat(api)!: remove v1 endpoints`) ou une ligne `BREAKING CHANGE: ...` dans le pied signale un changement qui casse l'existant pour ceux qui s'en servent.

## Pièges fréquents
- **`feat` pour de la mise en place** : installer un outil ou générer une structure n'est pas une fonctionnalité visible. C'est souvent `build` ou `chore`.
- **`fix` pour un renommage** : rien n'était cassé, le comportement ne change pas, c'est un `refactor`.
- **`:` dans un nom de branche** (`feat:login`) : Git le refuse, car `:` a un sens spécial dans `git push`. Utilise `/`.
- **Description au passé ou trop vague** (« added stuff », « update ») : impératif + la chose concrète.
- **Backticks dans un message entre guillemets doubles en bash** (`git commit -m "add \`x\`"`) : le shell les exécute comme une commande. Mets le message entre guillemets simples.

## Pour aller plus loin
- Certains outils génèrent un changelog ou un numéro de version automatiquement à partir des types (`feat` → version mineure, `fix` → correctif).
- En squash merge, le titre de la PR devient le message du commit sur la branche principale : il doit suivre la même convention.
- Spécification officielle : https://www.conventionalcommits.org/fr/v1.0.0/
