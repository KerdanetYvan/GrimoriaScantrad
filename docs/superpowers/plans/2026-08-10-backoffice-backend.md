# Grimoria Back-office — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Django/DRF API that powers the Grimoria team back-office: auth via self-hosted Supabase, team/membership/invite management, the per-planche production pipeline (clean/trad/edit/check) with dependency and rework logic, chapter export, and Discord webhook notifications.

**Architecture:** A single Django project (`backend/grimoria`) with four small apps — `core` (Supabase JWT auth + shared permissions), `teams` (Team, TeamMembership, Invite), `pipeline` (Series, Chapter, Planche, PlancheStep, Export, dependency service), `notifications` (Discord webhook dispatch). Django trusts Supabase Auth for identity (verifies the JWT signature) and owns all authorization (team membership, lead status, pipeline roles) and business logic itself. Images are uploaded directly from the frontend to Supabase Storage; Django only stores/consumes URLs, except for the generated export zip which Django/Celery builds and uploads itself. Async work (export generation, Discord delivery) runs via Celery on Redis.

**Tech Stack:** Python 3.12, Django 5.2 (LTS), Django REST Framework 3.15, PostgreSQL (self-hosted Supabase in production, plain `postgres:16` container for dev/test since `ArrayField` requires Postgres), PyJWT 2.9, Celery 5.4 + Redis 5, django-environ, pytest + pytest-django, `requests`.

## Global Constraints

- Auth is Supabase Auth (GoTrue) self-hosted; Django verifies JWTs with the shared HS256 secret (`SUPABASE_JWT_SECRET`) — it does not issue its own sessions.
- Django and Supabase share one Postgres instance: Supabase owns the `auth` schema, Django's tables live in `public` via normal migrations. Django never writes to `auth.*`; it stores the Supabase user UUID (`sub` claim) as a plain `UUIDField` wherever a user reference is needed.
- Pipeline dependency rules (from the spec): `clean` and `trad` become available as soon as a planche exists; `edit` becomes available only once both `clean` and `trad` are `done`; `check` becomes available only once `edit` is `done`. A failed check sends the target step to `rework` and resets everything downstream of it to `locked`.
- A team member is only allowed to self-assign/complete a `PlancheStep` whose `step_type` is in their `TeamMembership.pipeline_roles`. Only leads (`TeamMembership.is_lead`) can create series/chapters, manage members/invites, and edit team settings.
- Discord notifications are single-webhook-per-team, best-effort (never block the pipeline), and sent through one internal entry point (`notifications.services.notify`) so a future premium multi-channel bot can replace the implementation without touching pipeline code — see the spec's Non-objectifs.
- Chapter export is automatic: once every `check` `PlancheStep` in a chapter is `done`, a zip of the `edit` deliverables is generated and the chapter moves to `exported`.

---

## Task 1: Project scaffold, pytest harness, health check

**Files:**

- Create: `backend/requirements.txt`
- Create: `backend/manage.py` (generated)
- Create: `backend/grimoria/__init__.py`, `backend/grimoria/settings.py`, `backend/grimoria/urls.py`, `backend/grimoria/wsgi.py`, `backend/grimoria/asgi.py` (generated then edited)
- Create: `backend/pytest.ini`
- Create: `backend/core/__init__.py`, `backend/core/apps.py`, `backend/core/views.py`, `backend/core/urls.py`
- Test: `backend/core/tests/__init__.py`, `backend/core/tests/test_health.py`

**Interfaces:**

- Produces: `GET /api/health/` → `{"status": "ok"}`, used by later tasks as a template for adding new URL includes in `grimoria/urls.py`.

- [ ] **Step 1: Create the Python environment and pin dependencies**

```bash
cd backend 2>/dev/null || (mkdir backend && cd backend)
python -m venv .venv
```

Create `backend/requirements.txt`:

```text
Django==5.2.1
djangorestframework==3.15.2
psycopg[binary]==3.2.3
django-environ==0.11.2
PyJWT==2.9.0
celery==5.4.0
redis==5.0.8
requests==2.32.3
pytest==8.3.3
pytest-django==4.9.0
```

```bash
.venv/Scripts/pip install -r requirements.txt   # Windows
# .venv/bin/pip install -r requirements.txt      # macOS/Linux
```

- [ ] **Step 2: Generate the Django project**

```bash
.venv/Scripts/django-admin startproject grimoria .
```

This creates `manage.py` and `grimoria/{__init__.py,settings.py,urls.py,wsgi.py,asgi.py}`.

- [ ] **Step 3: Add the `core` app**

```bash
.venv/Scripts/python manage.py startapp core
```

Edit `backend/grimoria/settings.py`, add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "core",
]
```

- [ ] **Step 4: Create `backend/pytest.ini`**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = grimoria.settings
python_files = tests.py test_*.py
```

- [ ] **Step 5: Write the failing test for the health endpoint**

Create `backend/core/tests/__init__.py` (empty) and `backend/core/tests/test_health.py`:

```python
import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_check_returns_ok():
    client = APIClient()
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 6: Run the test and confirm it fails**

```bash
.venv/Scripts/pytest core/tests/test_health.py -v
```

Expected: FAIL — 404, `/api/health/` doesn't exist yet.

- [ ] **Step 7: Implement the health endpoint**

Create `backend/core/views.py`:

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})
```

Create `backend/core/urls.py`:

```python
from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
]
```

Edit `backend/grimoria/urls.py`:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
]
```

- [ ] **Step 8: Run the test and confirm it passes**

```bash
.venv/Scripts/pytest core/tests/test_health.py -v
```

Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "chore: scaffold Django project with health check endpoint"
```

---

## Task 2: Environment config, Postgres connection, Celery skeleton

**Files:**

- Create: `backend/.env.example`
- Modify: `backend/grimoria/settings.py`
- Create: `backend/grimoria/celery.py`
- Modify: `backend/grimoria/__init__.py`
- Test: `backend/core/tests/test_settings.py`

**Interfaces:**

- Produces: `env` object (django-environ) available via `from django.conf import settings` for `settings.SUPABASE_JWT_SECRET`, `settings.SUPABASE_URL`, `settings.SUPABASE_SERVICE_ROLE_KEY` (used by Task 3 and Task 13).
- Produces: `grimoria.celery.app` (Celery app instance), imported by later `tasks.py` modules via `from celery import shared_task`.

- [ ] **Step 1: Start a local Postgres for dev/test**

The full self-hosted Supabase stack (see Task 2 note below) is the production target, but local development/tests only need a plain Postgres matching its version — `ArrayField` (used by `TeamMembership.pipeline_roles` in Task 4) requires real Postgres, not SQLite.

```bash
docker run -d --name grimoria-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
```

- [ ] **Step 2: Create `backend/.env.example`**

```text
DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres
DJANGO_SECRET_KEY=changeme
DJANGO_DEBUG=True
SUPABASE_URL=http://localhost:8000
SUPABASE_JWT_SECRET=changeme-must-match-gotrue-jwt-secret
SUPABASE_SERVICE_ROLE_KEY=changeme
CELERY_BROKER_URL=redis://localhost:6379/0
DISCORD_WEBHOOK_TIMEOUT=10
```

Copy it for local use: `cp backend/.env.example backend/.env` and fill in real values once self-hosted Supabase is running (see the note at the end of this task).

- [ ] **Step 3: Write the failing test for settings wiring**

Create `backend/core/tests/test_settings.py`:

```python
from django.conf import settings


def test_supabase_settings_are_loaded():
    assert settings.SUPABASE_JWT_SECRET
    assert settings.SUPABASE_URL.startswith("http")
```

- [ ] **Step 4: Run the test and confirm it fails**

```bash
.venv/Scripts/pytest core/tests/test_settings.py -v
```

Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'SUPABASE_JWT_SECRET'`

- [ ] **Step 5: Wire environment variables into settings**

Edit `backend/grimoria/settings.py` — replace the `SECRET_KEY`, `DEBUG`, and `DATABASES` sections with:

```python
import environ

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

SUPABASE_URL = env("SUPABASE_URL")
SUPABASE_JWT_SECRET = env("SUPABASE_JWT_SECRET")
SUPABASE_SERVICE_ROLE_KEY = env("SUPABASE_SERVICE_ROLE_KEY")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.SupabaseJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_SERIALIZER = "json"
```

Note: `core.authentication.SupabaseJWTAuthentication` doesn't exist yet — that's Task 3. For now the health check in Task 1 is registered via `@api_view`, which defaults to `DEFAULT_PERMISSION_CLASSES`; add `permission_classes = [AllowAny]` to it so it still passes:

Edit `backend/core/views.py`:

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})
```

- [ ] **Step 6: Create the local `.env` for running tests**

```bash
cp backend/.env.example backend/.env
```

(Values from `.env.example` are sufficient to run tests locally against the Postgres container from Step 1; `SUPABASE_JWT_SECRET=changeme-must-match-gotrue-jwt-secret` is fine as a placeholder until Task 3's tests, which set their own known secret via `override_settings`.)

- [ ] **Step 7: Run the test and confirm it passes**

```bash
.venv/Scripts/pytest core/tests/test_settings.py core/tests/test_health.py -v
```

Expected: PASS (both tests)

- [ ] **Step 8: Add the Celery app skeleton**

Create `backend/grimoria/celery.py`:

```python
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grimoria.settings")

app = Celery("grimoria")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

Edit `backend/grimoria/__init__.py`:

```python
from .celery import app as celery_app

__all__ = ("celery_app",)
```

- [ ] **Step 9: Run the full test suite and confirm nothing broke**

```bash
.venv/Scripts/pytest -v
```

Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add backend/
git commit -m "chore: wire environment config, Postgres, and Celery skeleton"
```

> **Deployment note (not exercised by tests):** the production Postgres/Auth/Storage backing this project is self-hosted Supabase on OVH, not the plain container from Step 1. Stand it up by cloning `https://github.com/supabase/supabase`, copying `docker/.env.example` to `docker/.env`, setting `POSTGRES_PASSWORD`, `JWT_SECRET` (this becomes `SUPABASE_JWT_SECRET` above), and `SITE_URL`, then `docker compose -f docker/docker-compose.yml up -d`. Point `DATABASE_URL` in `backend/.env` at that Postgres instance and `SUPABASE_URL` at that stack's Kong gateway.

---

## Task 3: Supabase JWT authentication

**Files:**

- Create: `backend/core/authentication.py`
- Modify: `backend/core/views.py`
- Modify: `backend/core/urls.py`
- Test: `backend/core/tests/test_authentication.py`

**Interfaces:**

- Produces: `core.authentication.SupabaseJWTAuthentication` (DRF authentication class, already referenced in `settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`).
- Produces: `core.authentication.SupabaseUser` with attributes `.id` (str UUID) and `.email` (str), used by every later permission class and view as `request.user.id`.

- [ ] **Step 1: Write the failing tests**

Create `backend/core/tests/test_authentication.py`:

```python
import jwt
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

TEST_SECRET = "test-secret"


def make_token(sub="11111111-1111-1111-1111-111111111111", email="a@example.com"):
    return jwt.encode(
        {"sub": sub, "email": email, "aud": "authenticated"},
        TEST_SECRET,
        algorithm="HS256",
    )


@override_settings(SUPABASE_JWT_SECRET=TEST_SECRET)
def test_whoami_rejects_missing_token():
    client = APIClient()
    response = client.get("/api/whoami/")
    assert response.status_code == 401


@override_settings(SUPABASE_JWT_SECRET=TEST_SECRET)
def test_whoami_rejects_invalid_token():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    response = client.get("/api/whoami/")
    assert response.status_code == 401


@override_settings(SUPABASE_JWT_SECRET=TEST_SECRET)
def test_whoami_returns_user_from_valid_token():
    client = APIClient()
    token = make_token(sub="22222222-2222-2222-2222-222222222222", email="b@example.com")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.get("/api/whoami/")
    assert response.status_code == 200
    assert response.json() == {
        "id": "22222222-2222-2222-2222-222222222222",
        "email": "b@example.com",
    }
```

- [ ] **Step 2: Run the tests and confirm they fail**

```bash
.venv/Scripts/pytest core/tests/test_authentication.py -v
```

Expected: FAIL — `/api/whoami/` returns 404 (doesn't exist yet).

- [ ] **Step 3: Implement the authentication class**

Create `backend/core/authentication.py`:

```python
import jwt
from django.conf import settings
from rest_framework import authentication, exceptions


class SupabaseUser:
    def __init__(self, id, email):
        self.id = id
        self.email = email
        self.is_authenticated = True


class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[len("Bearer "):].strip()
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid Supabase token: {exc}")

        user_id = payload.get("sub")
        if not user_id:
            raise exceptions.AuthenticationFailed("Token missing sub claim")

        return (SupabaseUser(id=user_id, email=payload.get("email", "")), token)
```

- [ ] **Step 4: Add the `whoami` endpoint**

Edit `backend/core/views.py`, add:

```python
from rest_framework.permissions import IsAuthenticated


@api_view(["GET"])
def whoami(request):
    return Response({"id": request.user.id, "email": request.user.email})
```

(`whoami` uses the default `IsAuthenticated` permission from `REST_FRAMEWORK` settings — no decorator override needed.)

Edit `backend/core/urls.py`:

```python
from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("whoami/", views.whoami, name="whoami"),
]
```

- [ ] **Step 5: Run the tests and confirm they pass**

```bash
.venv/Scripts/pytest core/tests/test_authentication.py -v
```

Expected: PASS (all 3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/core/
git commit -m "feat: verify Supabase JWTs for API authentication"
```

---

## Task 4: Team and TeamMembership models

**Files:**

- Create: `backend/teams/__init__.py`, `backend/teams/apps.py`, `backend/teams/models.py`, `backend/teams/admin.py`
- Create: `backend/teams/migrations/__init__.py`
- Modify: `backend/grimoria/settings.py`
- Test: `backend/teams/tests/__init__.py`, `backend/teams/tests/test_models.py`

**Interfaces:**

- Produces: `teams.models.Team` (`id`, `name`, `slug`, `logo`, `discord_webhook_url`, `created_at`).
- Produces: `teams.models.TeamMembership` (`id`, `team` FK, `user_id` UUID, `is_lead` bool, `pipeline_roles` list[str], `created_at`), `unique_together = ("team", "user_id")`.
- Produces: `teams.models.PIPELINE_ROLE_CHOICES` — used by Task 5's `HasPipelineRole` and Task 8's serializer.

- [ ] **Step 1: Create the app**

```bash
.venv/Scripts/python manage.py startapp teams
```

Edit `backend/grimoria/settings.py`, add `"teams"` to `INSTALLED_APPS`.

- [ ] **Step 2: Write the failing test**

Create `backend/teams/tests/__init__.py` (empty) and `backend/teams/tests/test_models.py`:

```python
import pytest
from django.db import IntegrityError

from teams.models import Team, TeamMembership


@pytest.mark.django_db
def test_team_membership_is_unique_per_user_per_team():
    team = Team.objects.create(name="Archéologue Scantrad", slug="archeologue")
    TeamMembership.objects.create(
        team=team, user_id="11111111-1111-1111-1111-111111111111", is_lead=True
    )
    with pytest.raises(IntegrityError):
        TeamMembership.objects.create(
            team=team, user_id="11111111-1111-1111-1111-111111111111"
        )


@pytest.mark.django_db
def test_team_membership_stores_pipeline_roles():
    team = Team.objects.create(name="Archéologue Scantrad", slug="archeologue")
    membership = TeamMembership.objects.create(
        team=team,
        user_id="22222222-2222-2222-2222-222222222222",
        pipeline_roles=["clean", "edit"],
    )
    membership.refresh_from_db()
    assert membership.pipeline_roles == ["clean", "edit"]
```

- [ ] **Step 3: Run the test and confirm it fails**

```bash
.venv/Scripts/pytest teams/tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'teams.models'` has no `Team`/`TeamMembership` yet (empty file from `startapp`).

- [ ] **Step 4: Implement the models**

Create `backend/teams/models.py`:

```python
import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models

PIPELINE_ROLE_CHOICES = [
    ("clean", "Clean"),
    ("trad", "Trad"),
    ("edit", "Edit"),
    ("check", "Check"),
]


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=63, unique=True)
    logo = models.URLField(blank=True, default="")
    discord_webhook_url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user_id = models.UUIDField()
    is_lead = models.BooleanField(default=False)
    pipeline_roles = ArrayField(
        models.CharField(max_length=10, choices=PIPELINE_ROLE_CHOICES),
        default=list,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("team", "user_id")

    def __str__(self):
        return f"{self.user_id} @ {self.team.slug}"
```

Create `backend/teams/admin.py`:

```python
from django.contrib import admin

from .models import Team, TeamMembership

admin.site.register(Team)
admin.site.register(TeamMembership)
```

- [ ] **Step 5: Generate and apply the migration**

```bash
.venv/Scripts/python manage.py makemigrations teams
.venv/Scripts/python manage.py migrate
```

- [ ] **Step 6: Run the test and confirm it passes**

```bash
.venv/Scripts/pytest teams/tests/test_models.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/teams/ backend/grimoria/settings.py
git commit -m "feat: add Team and TeamMembership models"
```

---

## Task 5: Permission classes

**Files:**

- Create: `backend/core/permissions.py`
- Test: `backend/core/tests/test_permissions.py`

**Interfaces:**

- Consumes: `teams.models.TeamMembership` (Task 4).
- Produces: `core.permissions.IsTeamMember`, `core.permissions.IsTeamLead` (both check `view.kwargs["team_id"]` against `request.user.id`), and `core.permissions.HasPipelineRole` (object-level, expects `obj.step_type` and `obj.planche.chapter.series.team_id` — matches the `PlancheStep` model from Task 9).

- [ ] **Step 1: Write the failing tests**

Create `backend/core/tests/test_permissions.py`:

```python
import pytest
from rest_framework.test import APIRequestFactory

from core.authentication import SupabaseUser
from core.permissions import IsTeamLead, IsTeamMember
from teams.models import Team, TeamMembership

factory = APIRequestFactory()


class FakeView:
    def __init__(self, team_id):
        self.kwargs = {"team_id": team_id}


@pytest.mark.django_db
def test_is_team_member_true_for_member():
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(team=team, user_id="11111111-1111-1111-1111-111111111111")
    request = factory.get("/")
    request.user = SupabaseUser(id="11111111-1111-1111-1111-111111111111", email="a@example.com")
    assert IsTeamMember().has_permission(request, FakeView(team.id)) is True


@pytest.mark.django_db
def test_is_team_member_false_for_stranger():
    team = Team.objects.create(name="Team", slug="team")
    request = factory.get("/")
    request.user = SupabaseUser(id="99999999-9999-9999-9999-999999999999", email="x@example.com")
    assert IsTeamMember().has_permission(request, FakeView(team.id)) is False


@pytest.mark.django_db
def test_is_team_lead_false_for_non_lead_member():
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(
        team=team, user_id="11111111-1111-1111-1111-111111111111", is_lead=False
    )
    request = factory.get("/")
    request.user = SupabaseUser(id="11111111-1111-1111-1111-111111111111", email="a@example.com")
    assert IsTeamLead().has_permission(request, FakeView(team.id)) is False


@pytest.mark.django_db
def test_is_team_lead_true_for_lead():
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(
        team=team, user_id="11111111-1111-1111-1111-111111111111", is_lead=True
    )
    request = factory.get("/")
    request.user = SupabaseUser(id="11111111-1111-1111-1111-111111111111", email="a@example.com")
    assert IsTeamLead().has_permission(request, FakeView(team.id)) is True
```

- [ ] **Step 2: Run the tests and confirm they fail**

```bash
.venv/Scripts/pytest core/tests/test_permissions.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'core.permissions'`

- [ ] **Step 3: Implement the permission classes**

Create `backend/core/permissions.py`:

```python
from rest_framework.permissions import BasePermission

from teams.models import TeamMembership


class IsTeamMember(BasePermission):
    def has_permission(self, request, view):
        team_id = view.kwargs.get("team_id")
        if not team_id or not request.user or not request.user.is_authenticated:
            return False
        return TeamMembership.objects.filter(team_id=team_id, user_id=request.user.id).exists()


class IsTeamLead(BasePermission):
    def has_permission(self, request, view):
        team_id = view.kwargs.get("team_id")
        if not team_id or not request.user or not request.user.is_authenticated:
            return False
        return TeamMembership.objects.filter(
            team_id=team_id, user_id=request.user.id, is_lead=True
        ).exists()


class HasPipelineRole(BasePermission):
    """Object-level check: the requesting user must have obj.step_type
    in their pipeline_roles for the team that owns obj (a PlancheStep)."""

    def has_object_permission(self, request, view, obj):
        team_id = obj.planche.chapter.series.team_id
        membership = TeamMembership.objects.filter(
            team_id=team_id, user_id=request.user.id
        ).first()
        return bool(membership and obj.step_type in membership.pipeline_roles)
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
.venv/Scripts/pytest core/tests/test_permissions.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/core/permissions.py backend/core/tests/test_permissions.py
git commit -m "feat: add team membership, lead, and pipeline-role permissions"
```

---

## Task 6: Teams API — list my teams, view/update team settings

**Files:**

- Create: `backend/teams/serializers.py`
- Create: `backend/teams/views.py`
- Create: `backend/teams/urls.py`
- Modify: `backend/grimoria/urls.py`
- Test: `backend/teams/tests/test_views.py`

**Interfaces:**

- Consumes: `core.permissions.IsTeamMember`, `core.permissions.IsTeamLead` (Task 5).
- Produces: `GET /api/teams/mine/` (list teams the caller belongs to), `GET /api/teams/<team_id>/` (team detail, member-only), `PATCH /api/teams/<team_id>/` (lead-only: `name`, `logo`, `discord_webhook_url`).

- [ ] **Step 1: Write the failing tests**

Create `backend/teams/tests/test_views.py`:

```python
import jwt
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from teams.models import Team, TeamMembership

SECRET = "test-secret"
USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"


def auth_client(user_id):
    client = APIClient()
    token = jwt.encode({"sub": user_id, "email": "x@example.com", "aud": "authenticated"}, SECRET, algorithm="HS256")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_list_my_teams_only_returns_teams_i_belong_to():
    team_a = Team.objects.create(name="Team A", slug="team-a")
    team_b = Team.objects.create(name="Team B", slug="team-b")
    TeamMembership.objects.create(team=team_a, user_id=USER_A)
    TeamMembership.objects.create(team=team_b, user_id=USER_B)

    response = auth_client(USER_A).get("/api/teams/mine/")

    assert response.status_code == 200
    slugs = [t["slug"] for t in response.json()]
    assert slugs == ["team-a"]


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_non_lead_cannot_update_team_settings():
    team = Team.objects.create(name="Team A", slug="team-a")
    TeamMembership.objects.create(team=team, user_id=USER_A, is_lead=False)

    response = auth_client(USER_A).patch(f"/api/teams/{team.id}/", {"name": "New Name"})

    assert response.status_code == 403


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_lead_can_update_team_settings():
    team = Team.objects.create(name="Team A", slug="team-a")
    TeamMembership.objects.create(team=team, user_id=USER_A, is_lead=True)

    response = auth_client(USER_A).patch(
        f"/api/teams/{team.id}/",
        {"name": "New Name", "logo": "https://storage.example/logo.png"},
        format="json",
    )

    assert response.status_code == 200
    team.refresh_from_db()
    assert team.name == "New Name"
    assert team.logo == "https://storage.example/logo.png"
```

- [ ] **Step 2: Run the tests and confirm they fail**

```bash
.venv/Scripts/pytest teams/tests/test_views.py -v
```

Expected: FAIL — `/api/teams/mine/` returns 404.

- [ ] **Step 3: Implement serializers and views**

Create `backend/teams/serializers.py`:

```python
from rest_framework import serializers

from .models import Team


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "slug", "logo", "discord_webhook_url", "created_at"]
        read_only_fields = ["id", "created_at"]
```

Create `backend/teams/views.py`:

```python
from rest_framework.decorators import api_view
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response

from core.permissions import IsTeamLead, IsTeamMember
from .models import Team, TeamMembership
from .serializers import TeamSerializer


@api_view(["GET"])
def my_teams(request):
    team_ids = TeamMembership.objects.filter(user_id=request.user.id).values_list(
        "team_id", flat=True
    )
    teams = Team.objects.filter(id__in=team_ids)
    return Response(TeamSerializer(teams, many=True).data)


class TeamDetailView(RetrieveUpdateAPIView):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    lookup_url_kwarg = "team_id"

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [IsTeamLead()]
        return [IsTeamMember()]
```

Create `backend/teams/urls.py`:

```python
from django.urls import path

from . import views

urlpatterns = [
    path("mine/", views.my_teams, name="my-teams"),
    path("<uuid:team_id>/", views.TeamDetailView.as_view(), name="team-detail"),
]
```

Edit `backend/grimoria/urls.py`:

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/teams/", include("teams.urls")),
]
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
.venv/Scripts/pytest teams/tests/test_views.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/teams/ backend/grimoria/urls.py
git commit -m "feat: list my teams and view/update team settings"
```

---

## Task 7: Invites — create and accept

**Files:**

- Modify: `backend/teams/models.py`
- Modify: `backend/teams/serializers.py`
- Modify: `backend/teams/views.py`
- Modify: `backend/teams/urls.py`
- Test: `backend/teams/tests/test_invites.py`

**Interfaces:**

- Produces: `teams.models.Invite` (`id`, `token`, `team` FK, `created_by` UUID, `expires_at`, `used_at`, `created_at`).
- Produces: `POST /api/teams/<team_id>/invites/` (lead-only, body `{"expires_in_days": 7}`, returns `{"token": "..."}`).
- Produces: `POST /api/invites/<token>/accept/` (authenticated, any user; creates or updates the caller's `TeamMembership` for the invite's team, marks the invite used).

- [ ] **Step 1: Write the failing tests**

Create `backend/teams/tests/test_invites.py`:

```python
import jwt
import pytest
from django.test import override_settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from teams.models import Invite, Team, TeamMembership

SECRET = "test-secret"
LEAD = "11111111-1111-1111-1111-111111111111"
NEWCOMER = "33333333-3333-3333-3333-333333333333"


def auth_client(user_id):
    client = APIClient()
    token = jwt.encode({"sub": user_id, "email": "x@example.com", "aud": "authenticated"}, SECRET, algorithm="HS256")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_lead_can_create_invite():
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(team=team, user_id=LEAD, is_lead=True)

    response = auth_client(LEAD).post(f"/api/teams/{team.id}/invites/", {"expires_in_days": 7})

    assert response.status_code == 201
    assert Invite.objects.filter(team=team, created_by=LEAD).exists()
    assert response.json()["token"]


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_accepting_invite_creates_membership():
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(team=team, user_id=LEAD, is_lead=True)
    invite = Invite.objects.create(
        team=team, created_by=LEAD, expires_at=timezone.now() + timedelta(days=7)
    )

    response = auth_client(NEWCOMER).post(f"/api/invites/{invite.token}/accept/")

    assert response.status_code == 200
    assert TeamMembership.objects.filter(team=team, user_id=NEWCOMER).exists()
    invite.refresh_from_db()
    assert invite.used_at is not None


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_accepting_expired_invite_fails():
    team = Team.objects.create(name="Team", slug="team")
    invite = Invite.objects.create(
        team=team, created_by=LEAD, expires_at=timezone.now() - timedelta(days=1)
    )

    response = auth_client(NEWCOMER).post(f"/api/invites/{invite.token}/accept/")

    assert response.status_code == 400
    assert not TeamMembership.objects.filter(team=team, user_id=NEWCOMER).exists()


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_accepting_already_used_invite_fails():
    team = Team.objects.create(name="Team", slug="team")
    invite = Invite.objects.create(
        team=team,
        created_by=LEAD,
        expires_at=timezone.now() + timedelta(days=7),
        used_at=timezone.now(),
    )

    response = auth_client(NEWCOMER).post(f"/api/invites/{invite.token}/accept/")

    assert response.status_code == 400
```

- [ ] **Step 2: Run the tests and confirm they fail**

```bash
.venv/Scripts/pytest teams/tests/test_invites.py -v
```

Expected: FAIL — `ImportError: cannot import name 'Invite' from 'teams.models'`

- [ ] **Step 3: Add the `Invite` model**

Edit `backend/teams/models.py`, add near the top:

```python
import secrets
```

Add at the end of the file:

```python
def generate_invite_token():
    return secrets.token_urlsafe(32)


class Invite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=64, unique=True, default=generate_invite_token)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="invites")
    created_by = models.UUIDField()
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

```bash
.venv/Scripts/python manage.py makemigrations teams
.venv/Scripts/python manage.py migrate
```

- [ ] **Step 4: Add serializer, views, and URLs**

Edit `backend/teams/serializers.py`, add:

```python
from .models import Invite


class InviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invite
        fields = ["token", "expires_at", "used_at", "created_at"]
        read_only_fields = fields
```

Edit `backend/teams/views.py`, add:

```python
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Invite
from .serializers import InviteSerializer


@api_view(["POST"])
def create_invite(request, team_id):
    if not IsTeamLead().has_permission(request, type("V", (), {"kwargs": {"team_id": team_id}})()):
        return Response(status=status.HTTP_403_FORBIDDEN)
    expires_in_days = int(request.data.get("expires_in_days", 7))
    invite = Invite.objects.create(
        team_id=team_id,
        created_by=request.user.id,
        expires_at=timezone.now() + timedelta(days=expires_in_days),
    )
    return Response(InviteSerializer(invite).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def accept_invite(request, token):
    invite = get_object_or_404(Invite, token=token)
    if invite.used_at is not None:
        return Response({"detail": "Invite already used."}, status=status.HTTP_400_BAD_REQUEST)
    if invite.expires_at < timezone.now():
        return Response({"detail": "Invite expired."}, status=status.HTTP_400_BAD_REQUEST)

    TeamMembership.objects.get_or_create(
        team=invite.team, user_id=request.user.id, defaults={"is_lead": False}
    )
    invite.used_at = timezone.now()
    invite.save(update_fields=["used_at"])
    return Response({"team_id": str(invite.team_id)})
```

`create_invite` needs `IsAuthenticated` as its base DRF permission (already the default) plus the manual lead check above — no `@permission_classes` override needed since `IsAuthenticated` is the project default.

Edit `backend/teams/urls.py`:

```python
urlpatterns = [
    path("mine/", views.my_teams, name="my-teams"),
    path("<uuid:team_id>/", views.TeamDetailView.as_view(), name="team-detail"),
    path("<uuid:team_id>/invites/", views.create_invite, name="create-invite"),
]
```

Edit `backend/grimoria/urls.py`, add a top-level route for accepting invites (not team-scoped, since the caller isn't a member yet):

```python
from teams.views import accept_invite

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/teams/", include("teams.urls")),
    path("api/invites/<str:token>/accept/", accept_invite, name="accept-invite"),
]
```

- [ ] **Step 5: Run the tests and confirm they pass**

```bash
.venv/Scripts/pytest teams/tests/test_invites.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/teams/ backend/grimoria/urls.py
git commit -m "feat: add invite creation and acceptance"
```

---

## Task 8: Team members management (list + update pipeline roles)

**Files:**

- Modify: `backend/teams/serializers.py`
- Modify: `backend/teams/views.py`
- Modify: `backend/teams/urls.py`
- Test: `backend/teams/tests/test_members.py`

**Interfaces:**

- Produces: `GET /api/teams/<team_id>/members/` (member-only, lists memberships), `PATCH /api/teams/<team_id>/members/<membership_id>/` (lead-only, updates `is_lead`/`pipeline_roles`).

- [ ] **Step 1: Write the failing tests**

Create `backend/teams/tests/test_members.py`:

```python
import jwt
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from teams.models import Team, TeamMembership

SECRET = "test-secret"
LEAD = "11111111-1111-1111-1111-111111111111"
MEMBER = "22222222-2222-2222-2222-222222222222"


def auth_client(user_id):
    client = APIClient()
    token = jwt.encode({"sub": user_id, "email": "x@example.com", "aud": "authenticated"}, SECRET, algorithm="HS256")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_member_can_list_team_members():
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(team=team, user_id=LEAD, is_lead=True)
    TeamMembership.objects.create(team=team, user_id=MEMBER, pipeline_roles=["clean"])

    response = auth_client(MEMBER).get(f"/api/teams/{team.id}/members/")

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_lead_can_update_member_pipeline_roles():
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(team=team, user_id=LEAD, is_lead=True)
    membership = TeamMembership.objects.create(team=team, user_id=MEMBER, pipeline_roles=["clean"])

    response = auth_client(LEAD).patch(
        f"/api/teams/{team.id}/members/{membership.id}/",
        {"pipeline_roles": ["clean", "edit"]},
        format="json",
    )

    assert response.status_code == 200
    membership.refresh_from_db()
    assert membership.pipeline_roles == ["clean", "edit"]


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_non_lead_cannot_update_member_roles():
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(team=team, user_id=LEAD, is_lead=True)
    membership = TeamMembership.objects.create(team=team, user_id=MEMBER, pipeline_roles=["clean"])

    response = auth_client(MEMBER).patch(
        f"/api/teams/{team.id}/members/{membership.id}/",
        {"pipeline_roles": ["check"]},
        format="json",
    )

    assert response.status_code == 403
```

- [ ] **Step 2: Run the tests and confirm they fail**

```bash
.venv/Scripts/pytest teams/tests/test_members.py -v
```

Expected: FAIL — `/api/teams/<id>/members/` returns 404.

- [ ] **Step 3: Implement serializer, views, URLs**

Edit `backend/teams/serializers.py`, add:

```python
from .models import TeamMembership


class TeamMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMembership
        fields = ["id", "user_id", "is_lead", "pipeline_roles", "created_at"]
        read_only_fields = ["id", "user_id", "created_at"]
```

Edit `backend/teams/views.py`, add:

```python
from rest_framework.generics import ListAPIView, UpdateAPIView

from .serializers import TeamMembershipSerializer


class TeamMemberListView(ListAPIView):
    serializer_class = TeamMembershipSerializer
    permission_classes = [IsTeamMember]

    def get_queryset(self):
        return TeamMembership.objects.filter(team_id=self.kwargs["team_id"])


class TeamMemberUpdateView(UpdateAPIView):
    serializer_class = TeamMembershipSerializer
    permission_classes = [IsTeamLead]
    lookup_url_kwarg = "membership_id"

    def get_queryset(self):
        return TeamMembership.objects.filter(team_id=self.kwargs["team_id"])
```

Edit `backend/teams/urls.py`:

```python
urlpatterns = [
    path("mine/", views.my_teams, name="my-teams"),
    path("<uuid:team_id>/", views.TeamDetailView.as_view(), name="team-detail"),
    path("<uuid:team_id>/invites/", views.create_invite, name="create-invite"),
    path("<uuid:team_id>/members/", views.TeamMemberListView.as_view(), name="team-members"),
    path(
        "<uuid:team_id>/members/<uuid:membership_id>/",
        views.TeamMemberUpdateView.as_view(),
        name="team-member-detail",
    ),
]
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
.venv/Scripts/pytest teams/tests/test_members.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/teams/
git commit -m "feat: list and manage team members' pipeline roles"
```

---

## Task 9: Series, Chapter, Planche, PlancheStep models + chapter creation endpoint

**Files:**

- Create: `backend/pipeline/__init__.py`, `backend/pipeline/apps.py`, `backend/pipeline/models.py`, `backend/pipeline/admin.py`
- Create: `backend/pipeline/migrations/__init__.py`
- Create: `backend/pipeline/serializers.py`
- Create: `backend/pipeline/views.py`
- Create: `backend/pipeline/urls.py`
- Modify: `backend/grimoria/settings.py`
- Modify: `backend/grimoria/urls.py`
- Test: `backend/pipeline/tests/__init__.py`, `backend/pipeline/tests/test_chapter_creation.py`

**Interfaces:**

- Produces: `pipeline.models.Series`, `pipeline.models.Chapter` (`status` ∈ `in_progress|ready|exported`), `pipeline.models.Planche`, `pipeline.models.PlancheStep` (`step_type` ∈ `clean|trad|edit|check`, `status` ∈ `locked|available|in_progress|done|rework`).
- Produces: `POST /api/teams/<team_id>/series/` (lead-only, `{"name": "...", "slug": "..."}`).
- Produces: `POST /api/teams/<team_id>/series/<series_id>/chapters/` (lead-only, `{"number": 1, "title": "...", "planches": [{"page_number": 1, "raw_image": "https://..."}]}`) — creates the `Chapter`, its `Planche`s, and 4 `PlancheStep` rows per planche (all `locked` initially; Task 10 wires the unlock call in).

- [ ] **Step 1: Create the app**

```bash
.venv/Scripts/python manage.py startapp pipeline
```

Edit `backend/grimoria/settings.py`, add `"pipeline"` to `INSTALLED_APPS`.

- [ ] **Step 2: Write the failing test**

Create `backend/pipeline/tests/__init__.py` (empty) and `backend/pipeline/tests/test_chapter_creation.py`:

```python
import jwt
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from pipeline.models import Chapter, Planche, PlancheStep, Series
from teams.models import Team, TeamMembership

SECRET = "test-secret"
LEAD = "11111111-1111-1111-1111-111111111111"
MEMBER = "22222222-2222-2222-2222-222222222222"


def auth_client(user_id):
    client = APIClient()
    token = jwt.encode({"sub": user_id, "email": "x@example.com", "aud": "authenticated"}, SECRET, algorithm="HS256")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_lead_can_create_series():
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(team=team, user_id=LEAD, is_lead=True)

    response = auth_client(LEAD).post(
        f"/api/teams/{team.id}/series/", {"name": "One Piece", "slug": "one-piece"}
    )

    assert response.status_code == 201
    assert Series.objects.filter(team=team, slug="one-piece").exists()


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_non_lead_cannot_create_series():
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(team=team, user_id=MEMBER, is_lead=False)

    response = auth_client(MEMBER).post(
        f"/api/teams/{team.id}/series/", {"name": "One Piece", "slug": "one-piece"}
    )

    assert response.status_code == 403


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_creating_chapter_creates_planches_and_four_steps_each():
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(team=team, user_id=LEAD, is_lead=True)
    series = Series.objects.create(team=team, name="One Piece", slug="one-piece")

    response = auth_client(LEAD).post(
        f"/api/teams/{team.id}/series/{series.id}/chapters/",
        {
            "number": "1",
            "title": "Romance Dawn",
            "planches": [
                {"page_number": 1, "raw_image": "https://storage.example/1.png"},
                {"page_number": 2, "raw_image": "https://storage.example/2.png"},
            ],
        },
        format="json",
    )

    assert response.status_code == 201
    chapter = Chapter.objects.get(series=series, number=1)
    assert chapter.status == "in_progress"
    assert chapter.created_by == LEAD
    planches = Planche.objects.filter(chapter=chapter).order_by("page_number")
    assert list(planches.values_list("page_number", flat=True)) == [1, 2]
    for planche in planches:
        step_types = set(
            PlancheStep.objects.filter(planche=planche).values_list("step_type", flat=True)
        )
        assert step_types == {"clean", "trad", "edit", "check"}
```

- [ ] **Step 3: Run the test and confirm it fails**

```bash
.venv/Scripts/pytest pipeline/tests/test_chapter_creation.py -v
```

Expected: FAIL — `ModuleNotFoundError` / no models yet.

- [ ] **Step 4: Implement the models**

Create `backend/pipeline/models.py`:

```python
import uuid

from django.db import models

from teams.models import Team

STEP_TYPES = ["clean", "trad", "edit", "check"]
STEP_STATUS_CHOICES = [
    ("locked", "Locked"),
    ("available", "Available"),
    ("in_progress", "In progress"),
    ("done", "Done"),
    ("rework", "Rework"),
]
CHAPTER_STATUS_CHOICES = [
    ("in_progress", "In progress"),
    ("ready", "Ready"),
    ("exported", "Exported"),
]


class Series(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="series")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("team", "slug")
        verbose_name_plural = "series"

    def __str__(self):
        return self.name


class Chapter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    series = models.ForeignKey(Series, on_delete=models.CASCADE, related_name="chapters")
    number = models.DecimalField(max_digits=6, decimal_places=1)
    title = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=20, choices=CHAPTER_STATUS_CHOICES, default="in_progress")
    created_by = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("series", "number")

    def __str__(self):
        return f"{self.series.name} #{self.number}"


class Planche(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="planches")
    page_number = models.PositiveIntegerField()
    raw_image = models.URLField()

    class Meta:
        unique_together = ("chapter", "page_number")
        ordering = ["page_number"]


class PlancheStep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    planche = models.ForeignKey(Planche, on_delete=models.CASCADE, related_name="steps")
    step_type = models.CharField(max_length=10, choices=[(t, t) for t in STEP_TYPES])
    status = models.CharField(max_length=15, choices=STEP_STATUS_CHOICES, default="locked")
    assigned_to = models.UUIDField(null=True, blank=True)
    deliverable = models.TextField(blank=True, default="")
    rework_comment = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("planche", "step_type")

    def __str__(self):
        return f"{self.planche_id}:{self.step_type}"
```

Create `backend/pipeline/admin.py`:

```python
from django.contrib import admin

from .models import Chapter, Planche, PlancheStep, Series

admin.site.register(Series)
admin.site.register(Chapter)
admin.site.register(Planche)
admin.site.register(PlancheStep)
```

```bash
.venv/Scripts/python manage.py makemigrations pipeline
.venv/Scripts/python manage.py migrate
```

- [ ] **Step 5: Implement serializers and views**

Create `backend/pipeline/serializers.py`:

```python
from rest_framework import serializers

from .models import Chapter, Planche, PlancheStep, Series, STEP_TYPES


class SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = ["id", "name", "slug", "created_at"]
        read_only_fields = ["id", "created_at"]


class PlancheInputSerializer(serializers.Serializer):
    page_number = serializers.IntegerField(min_value=1)
    raw_image = serializers.URLField()


class ChapterCreateSerializer(serializers.Serializer):
    number = serializers.DecimalField(max_digits=6, decimal_places=1)
    title = serializers.CharField(required=False, allow_blank=True, default="")
    planches = PlancheInputSerializer(many=True)


class PlancheStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlancheStep
        fields = ["id", "step_type", "status", "assigned_to", "deliverable", "rework_comment", "updated_at"]
        read_only_fields = fields


class PlancheSerializer(serializers.ModelSerializer):
    steps = PlancheStepSerializer(many=True, read_only=True)

    class Meta:
        model = Planche
        fields = ["id", "page_number", "raw_image", "steps"]


class ChapterSerializer(serializers.ModelSerializer):
    planches = PlancheSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ["id", "number", "title", "status", "created_by", "created_at", "planches"]
```

Create `backend/pipeline/views.py`:

```python
from django.db import transaction
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsTeamLead, IsTeamMember
from .models import Chapter, Planche, PlancheStep, STEP_TYPES, Series
from .serializers import ChapterCreateSerializer, ChapterSerializer, SeriesSerializer


class SeriesListCreateView(ListCreateAPIView):
    serializer_class = SeriesSerializer

    def get_permissions(self):
        return [IsTeamLead()] if self.request.method == "POST" else [IsTeamMember()]

    def get_queryset(self):
        return Series.objects.filter(team_id=self.kwargs["team_id"])

    def perform_create(self, serializer):
        serializer.save(team_id=self.kwargs["team_id"])


class ChapterCreateView(APIView):
    permission_classes = [IsTeamLead]

    def post(self, request, team_id, series_id):
        payload = ChapterCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        with transaction.atomic():
            chapter = Chapter.objects.create(
                series_id=series_id,
                number=data["number"],
                title=data.get("title", ""),
                created_by=request.user.id,
            )
            for planche_data in data["planches"]:
                planche = Planche.objects.create(
                    chapter=chapter,
                    page_number=planche_data["page_number"],
                    raw_image=planche_data["raw_image"],
                )
                PlancheStep.objects.bulk_create(
                    [PlancheStep(planche=planche, step_type=step_type) for step_type in STEP_TYPES]
                )

        return Response(ChapterSerializer(chapter).data, status=status.HTTP_201_CREATED)


class ChapterDetailView(RetrieveAPIView):
    serializer_class = ChapterSerializer
    permission_classes = [IsTeamMember]
    lookup_url_kwarg = "chapter_id"

    def get_queryset(self):
        return Chapter.objects.filter(series__team_id=self.kwargs["team_id"])
```

Create `backend/pipeline/urls.py`:

```python
from django.urls import path

from . import views

urlpatterns = [
    path("<uuid:team_id>/series/", views.SeriesListCreateView.as_view(), name="series-list-create"),
    path(
        "<uuid:team_id>/series/<uuid:series_id>/chapters/",
        views.ChapterCreateView.as_view(),
        name="chapter-create",
    ),
    path(
        "<uuid:team_id>/chapters/<uuid:chapter_id>/",
        views.ChapterDetailView.as_view(),
        name="chapter-detail",
    ),
]
```

Edit `backend/grimoria/urls.py`:

```python
path("api/teams/", include("pipeline.urls")),
```

(add alongside the existing `path("api/teams/", include("teams.urls"))` line — both includes share the `api/teams/` prefix, which Django resolves fine since the sub-patterns don't collide: `teams.urls` has no `series/` or `chapters/` routes.)

- [ ] **Step 6: Run the test and confirm it passes**

```bash
.venv/Scripts/pytest pipeline/tests/test_chapter_creation.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/pipeline/ backend/grimoria/
git commit -m "feat: add Series/Chapter/Planche/PlancheStep models and chapter creation"
```

---

## Task 10: Pipeline dependency service

**Files:**

- Create: `backend/pipeline/services.py`
- Test: `backend/pipeline/tests/test_services.py`

**Interfaces:**

- Consumes: `pipeline.models.PlancheStep`, `pipeline.models.Chapter` (Task 9).
- Produces: `pipeline.services.recompute_step_statuses(planche) -> list[PlancheStep]` (returns steps newly transitioned to `available`), `pipeline.services.send_step_to_rework(planche, target_step_type, comment) -> None`, `pipeline.services.chapter_is_ready(chapter) -> bool`. All three are consumed by Task 11 and Task 12's views.

- [ ] **Step 1: Write the failing tests**

Create `backend/pipeline/tests/test_services.py`:

```python
import pytest

from pipeline.models import Chapter, Planche, PlancheStep, STEP_TYPES, Series
from pipeline.services import chapter_is_ready, recompute_step_statuses, send_step_to_rework
from teams.models import Team


@pytest.fixture
def planche(db):
    team = Team.objects.create(name="Team", slug="team")
    series = Series.objects.create(team=team, name="Series", slug="series")
    chapter = Chapter.objects.create(series=series, number=1, created_by="11111111-1111-1111-1111-111111111111")
    planche = Planche.objects.create(chapter=chapter, page_number=1, raw_image="https://storage.example/1.png")
    PlancheStep.objects.bulk_create([PlancheStep(planche=planche, step_type=t) for t in STEP_TYPES])
    return planche


def get_step(planche, step_type):
    return PlancheStep.objects.get(planche=planche, step_type=step_type)


def test_clean_and_trad_unlock_immediately(planche):
    newly_available = recompute_step_statuses(planche)
    assert {s.step_type for s in newly_available} == {"clean", "trad"}
    assert get_step(planche, "clean").status == "available"
    assert get_step(planche, "trad").status == "available"
    assert get_step(planche, "edit").status == "locked"
    assert get_step(planche, "check").status == "locked"


def test_edit_stays_locked_until_clean_and_trad_are_done(planche):
    recompute_step_statuses(planche)
    clean = get_step(planche, "clean")
    clean.status = "done"
    clean.save()

    newly_available = recompute_step_statuses(planche)

    assert newly_available == []
    assert get_step(planche, "edit").status == "locked"


def test_edit_unlocks_once_clean_and_trad_are_both_done(planche):
    recompute_step_statuses(planche)
    for step_type in ("clean", "trad"):
        step = get_step(planche, step_type)
        step.status = "done"
        step.save()

    newly_available = recompute_step_statuses(planche)

    assert {s.step_type for s in newly_available} == {"edit"}
    assert get_step(planche, "edit").status == "available"


def test_check_unlocks_once_edit_is_done(planche):
    recompute_step_statuses(planche)
    for step_type in ("clean", "trad", "edit"):
        step = get_step(planche, step_type)
        step.status = "done"
        step.save()

    newly_available = recompute_step_statuses(planche)

    assert {s.step_type for s in newly_available} == {"check"}
    assert get_step(planche, "check").status == "available"


def test_failed_check_sends_edit_to_rework_and_relocks_check(planche):
    for step_type in ("clean", "trad", "edit"):
        step = get_step(planche, step_type)
        step.status = "done"
        step.save()
    check = get_step(planche, "check")
    check.status = "available"
    check.save()

    send_step_to_rework(planche, "edit", "Texte mal placé sur la case 3")

    edit = get_step(planche, "edit")
    assert edit.status == "rework"
    assert edit.rework_comment == "Texte mal placé sur la case 3"
    assert get_step(planche, "check").status == "locked"


def test_chapter_is_ready_only_when_every_planche_check_is_done(db):
    team = Team.objects.create(name="Team", slug="team")
    series = Series.objects.create(team=team, name="Series", slug="series")
    chapter = Chapter.objects.create(series=series, number=1, created_by="11111111-1111-1111-1111-111111111111")
    p1 = Planche.objects.create(chapter=chapter, page_number=1, raw_image="https://storage.example/1.png")
    p2 = Planche.objects.create(chapter=chapter, page_number=2, raw_image="https://storage.example/2.png")
    for p in (p1, p2):
        PlancheStep.objects.bulk_create([PlancheStep(planche=p, step_type=t) for t in STEP_TYPES])

    assert chapter_is_ready(chapter) is False

    for p in (p1, p2):
        step = get_step(p, "check")
        step.status = "done"
        step.save()

    assert chapter_is_ready(chapter) is True
```

- [ ] **Step 2: Run the tests and confirm they fail**

```bash
.venv/Scripts/pytest pipeline/tests/test_services.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.services'`

- [ ] **Step 3: Implement the service**

Create `backend/pipeline/services.py`:

```python
from .models import PlancheStep

DOWNSTREAM = {
    "clean": ["edit", "check"],
    "trad": ["edit", "check"],
    "edit": ["check"],
}


def recompute_step_statuses(planche):
    steps = {s.step_type: s for s in planche.steps.all()}
    newly_available = []

    for step_type in ("clean", "trad"):
        step = steps[step_type]
        if step.status == "locked":
            step.status = "available"
            step.save(update_fields=["status"])
            newly_available.append(step)

    edit = steps["edit"]
    if edit.status == "locked" and steps["clean"].status == "done" and steps["trad"].status == "done":
        edit.status = "available"
        edit.save(update_fields=["status"])
        newly_available.append(edit)

    check = steps["check"]
    if check.status == "locked" and edit.status == "done":
        check.status = "available"
        check.save(update_fields=["status"])
        newly_available.append(check)

    return newly_available


def send_step_to_rework(planche, target_step_type, comment):
    steps = {s.step_type: s for s in planche.steps.all()}
    target = steps[target_step_type]
    target.status = "rework"
    target.rework_comment = comment
    target.assigned_to = None
    target.save(update_fields=["status", "rework_comment", "assigned_to"])

    for downstream_type in DOWNSTREAM.get(target_step_type, []):
        downstream = steps[downstream_type]
        if downstream.status != "locked":
            downstream.status = "locked"
            downstream.assigned_to = None
            downstream.save(update_fields=["status", "assigned_to"])


def chapter_is_ready(chapter):
    check_steps = PlancheStep.objects.filter(planche__chapter=chapter, step_type="check")
    return check_steps.exists() and all(s.status == "done" for s in check_steps)
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
.venv/Scripts/pytest pipeline/tests/test_services.py -v
```

Expected: PASS (6 tests)

- [ ] **Step 5: Wire `recompute_step_statuses` into chapter creation**

Edit `backend/pipeline/views.py` — in `ChapterCreateView.post`, after the `with transaction.atomic():` block that creates planches/steps, call the service for each planche so `clean`/`trad` start `available` instead of `locked`:

```python
from .services import recompute_step_statuses
```

```python
        with transaction.atomic():
            chapter = Chapter.objects.create(
                series_id=series_id,
                number=data["number"],
                title=data.get("title", ""),
                created_by=request.user.id,
            )
            created_planches = []
            for planche_data in data["planches"]:
                planche = Planche.objects.create(
                    chapter=chapter,
                    page_number=planche_data["page_number"],
                    raw_image=planche_data["raw_image"],
                )
                PlancheStep.objects.bulk_create(
                    [PlancheStep(planche=planche, step_type=step_type) for step_type in STEP_TYPES]
                )
                created_planches.append(planche)

        for planche in created_planches:
            recompute_step_statuses(planche)
```

Edit `backend/pipeline/tests/test_chapter_creation.py`'s `test_creating_chapter_creates_planches_and_four_steps_each` to also assert the unlock happened — add at the end:

```python
    for planche in planches:
        clean = PlancheStep.objects.get(planche=planche, step_type="clean")
        trad = PlancheStep.objects.get(planche=planche, step_type="trad")
        edit = PlancheStep.objects.get(planche=planche, step_type="edit")
        assert clean.status == "available"
        assert trad.status == "available"
        assert edit.status == "locked"
```

- [ ] **Step 6: Run the full pipeline test suite and confirm it passes**

```bash
.venv/Scripts/pytest pipeline/ -v
```

Expected: PASS (all tests)

- [ ] **Step 7: Commit**

```bash
git add backend/pipeline/
git commit -m "feat: add pipeline dependency and rework service logic"
```

---

## Task 11: PlancheStep assign and complete endpoints

**Files:**

- Modify: `backend/pipeline/serializers.py`
- Modify: `backend/pipeline/views.py`
- Modify: `backend/pipeline/urls.py`
- Test: `backend/pipeline/tests/test_step_actions.py`

**Interfaces:**

- Consumes: `core.permissions.HasPipelineRole` (Task 5), `pipeline.services.recompute_step_statuses` (Task 10).
- Produces: `POST /api/planche-steps/<step_id>/assign/` (self-assign; requires `step_type` in caller's `pipeline_roles`, step must be `available`), `POST /api/planche-steps/<step_id>/complete/` (body `{"deliverable": "..."}`; requires caller to be `assigned_to`, step must be `in_progress`).

- [ ] **Step 1: Write the failing tests**

Create `backend/pipeline/tests/test_step_actions.py`:

```python
import jwt
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from pipeline.models import Chapter, Planche, PlancheStep, STEP_TYPES, Series
from pipeline.services import recompute_step_statuses
from teams.models import Team, TeamMembership

SECRET = "test-secret"
CLEANER = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"


def auth_client(user_id):
    client = APIClient()
    token = jwt.encode({"sub": user_id, "email": "x@example.com", "aud": "authenticated"}, SECRET, algorithm="HS256")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def planche_with_available_clean(db):
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(team=team, user_id=CLEANER, pipeline_roles=["clean"])
    TeamMembership.objects.create(team=team, user_id=OTHER, pipeline_roles=["trad"])
    series = Series.objects.create(team=team, name="Series", slug="series")
    chapter = Chapter.objects.create(series=series, number=1, created_by=CLEANER)
    planche = Planche.objects.create(chapter=chapter, page_number=1, raw_image="https://storage.example/1.png")
    PlancheStep.objects.bulk_create([PlancheStep(planche=planche, step_type=t) for t in STEP_TYPES])
    recompute_step_statuses(planche)
    return planche


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_member_without_role_cannot_assign(planche_with_available_clean):
    clean_step = PlancheStep.objects.get(planche=planche_with_available_clean, step_type="clean")

    response = auth_client(OTHER).post(f"/api/planche-steps/{clean_step.id}/assign/")

    assert response.status_code == 403


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_member_with_role_can_assign_available_step(planche_with_available_clean):
    clean_step = PlancheStep.objects.get(planche=planche_with_available_clean, step_type="clean")

    response = auth_client(CLEANER).post(f"/api/planche-steps/{clean_step.id}/assign/")

    assert response.status_code == 200
    clean_step.refresh_from_db()
    assert clean_step.status == "in_progress"
    assert str(clean_step.assigned_to) == CLEANER


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_only_the_assignee_can_complete_a_step(planche_with_available_clean):
    clean_step = PlancheStep.objects.get(planche=planche_with_available_clean, step_type="clean")
    auth_client(CLEANER).post(f"/api/planche-steps/{clean_step.id}/assign/")

    response = auth_client(OTHER).post(
        f"/api/planche-steps/{clean_step.id}/complete/",
        {"deliverable": "https://storage.example/1-clean.png"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_completing_a_step_saves_deliverable_and_recomputes_dependents(planche_with_available_clean):
    clean_step = PlancheStep.objects.get(planche=planche_with_available_clean, step_type="clean")
    trad_step = PlancheStep.objects.get(planche=planche_with_available_clean, step_type="trad")
    auth_client(CLEANER).post(f"/api/planche-steps/{clean_step.id}/assign/")

    response = auth_client(CLEANER).post(
        f"/api/planche-steps/{clean_step.id}/complete/",
        {"deliverable": "https://storage.example/1-clean.png"},
    )

    assert response.status_code == 200
    clean_step.refresh_from_db()
    assert clean_step.status == "done"
    assert clean_step.deliverable == "https://storage.example/1-clean.png"
    edit_step = PlancheStep.objects.get(planche=planche_with_available_clean, step_type="edit")
    assert edit_step.status == "locked"  # trad not done yet, so edit stays locked
```

- [ ] **Step 2: Run the tests and confirm they fail**

```bash
.venv/Scripts/pytest pipeline/tests/test_step_actions.py -v
```

Expected: FAIL — `/api/planche-steps/<id>/assign/` returns 404.

- [ ] **Step 3: Implement the views**

Edit `backend/pipeline/views.py`, add imports and views:

```python
from django.shortcuts import get_object_or_404

from core.permissions import HasPipelineRole
from .models import PlancheStep
from .services import recompute_step_statuses


class PlancheStepAssignView(APIView):
    def post(self, request, step_id):
        step = get_object_or_404(PlancheStep, id=step_id)
        if not HasPipelineRole().has_object_permission(request, self, step):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if step.status != "available":
            return Response(
                {"detail": f"Step is {step.status}, not available."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        step.status = "in_progress"
        step.assigned_to = request.user.id
        step.save(update_fields=["status", "assigned_to"])
        return Response({"id": str(step.id), "status": step.status})


class PlancheStepCompleteView(APIView):
    def post(self, request, step_id):
        step = get_object_or_404(PlancheStep, id=step_id)
        if str(step.assigned_to) != str(request.user.id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if step.status != "in_progress":
            return Response(
                {"detail": f"Step is {step.status}, not in_progress."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        step.deliverable = request.data.get("deliverable", "")
        step.status = "done"
        step.save(update_fields=["deliverable", "status"])
        recompute_step_statuses(step.planche)
        return Response({"id": str(step.id), "status": step.status})
```

Edit `backend/pipeline/urls.py`, add:

```python
    path("planche-steps/<uuid:step_id>/assign/", views.PlancheStepAssignView.as_view(), name="step-assign"),
    path("planche-steps/<uuid:step_id>/complete/", views.PlancheStepCompleteView.as_view(), name="step-complete"),
```

These two routes aren't team-scoped in the URL, so mount them directly in `backend/grimoria/urls.py` instead of inside the `api/teams/` include — remove them from `pipeline/urls.py`'s list above and instead edit `backend/grimoria/urls.py`:

```python
from django.contrib import admin
from django.urls import include, path

from pipeline.views import PlancheStepAssignView, PlancheStepCompleteView
from teams.views import accept_invite

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/teams/", include("teams.urls")),
    path("api/teams/", include("pipeline.urls")),
    path("api/invites/<str:token>/accept/", accept_invite, name="accept-invite"),
    path("api/planche-steps/<uuid:step_id>/assign/", PlancheStepAssignView.as_view(), name="step-assign"),
    path("api/planche-steps/<uuid:step_id>/complete/", PlancheStepCompleteView.as_view(), name="step-complete"),
]
```

This is the complete file — it replaces the version from Task 7 in full (which only had `core.urls`, `teams.urls`, and the invite-accept route).

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
.venv/Scripts/pytest pipeline/tests/test_step_actions.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 5: Run the full backend test suite**

```bash
.venv/Scripts/pytest -v
```

Expected: PASS (all tests)

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/ backend/grimoria/urls.py
git commit -m "feat: add planche step assign and complete endpoints"
```

---

## Task 12: Check rework endpoint

**Files:**

- Modify: `backend/pipeline/views.py`
- Modify: `backend/grimoria/urls.py`
- Test: `backend/pipeline/tests/test_rework.py`

**Interfaces:**

- Consumes: `pipeline.services.send_step_to_rework` (Task 10).
- Produces: `POST /api/planche-steps/<check_step_id>/reject/` (body `{"target_step_type": "edit", "comment": "..."}`; only valid when the target step is a `check` step assigned to the caller and currently `in_progress`).

- [ ] **Step 1: Write the failing tests**

Create `backend/pipeline/tests/test_rework.py`:

```python
import jwt
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from pipeline.models import Chapter, Planche, PlancheStep, STEP_TYPES, Series
from teams.models import Team, TeamMembership

SECRET = "test-secret"
CHECKER = "11111111-1111-1111-1111-111111111111"


def auth_client(user_id):
    client = APIClient()
    token = jwt.encode({"sub": user_id, "email": "x@example.com", "aud": "authenticated"}, SECRET, algorithm="HS256")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def planche_with_check_in_progress(db):
    team = Team.objects.create(name="Team", slug="team")
    TeamMembership.objects.create(team=team, user_id=CHECKER, pipeline_roles=["check"])
    series = Series.objects.create(team=team, name="Series", slug="series")
    chapter = Chapter.objects.create(series=series, number=1, created_by=CHECKER)
    planche = Planche.objects.create(chapter=chapter, page_number=1, raw_image="https://storage.example/1.png")
    steps = {
        t: PlancheStep.objects.create(planche=planche, step_type=t, status="done")
        for t in ("clean", "trad", "edit")
    }
    check = PlancheStep.objects.create(
        planche=planche, step_type="check", status="in_progress", assigned_to=CHECKER
    )
    return planche, steps, check


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_checker_can_reject_and_send_edit_to_rework(planche_with_check_in_progress):
    planche, steps, check = planche_with_check_in_progress

    response = auth_client(CHECKER).post(
        f"/api/planche-steps/{check.id}/reject/",
        {"target_step_type": "edit", "comment": "Bulle mal alignée"},
        format="json",
    )

    assert response.status_code == 200
    edit = PlancheStep.objects.get(planche=planche, step_type="edit")
    assert edit.status == "rework"
    assert edit.rework_comment == "Bulle mal alignée"
    check.refresh_from_db()
    assert check.status == "locked"


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_only_assigned_checker_can_reject(planche_with_check_in_progress):
    planche, steps, check = planche_with_check_in_progress

    response = auth_client("99999999-9999-9999-9999-999999999999").post(
        f"/api/planche-steps/{check.id}/reject/",
        {"target_step_type": "edit", "comment": "Bulle mal alignée"},
        format="json",
    )

    assert response.status_code == 403
```

- [ ] **Step 2: Run the tests and confirm they fail**

```bash
.venv/Scripts/pytest pipeline/tests/test_rework.py -v
```

Expected: FAIL — `/api/planche-steps/<id>/reject/` returns 404.

- [ ] **Step 3: Implement the view**

Edit `backend/pipeline/views.py`, add:

```python
from .services import send_step_to_rework


class PlancheStepRejectView(APIView):
    def post(self, request, step_id):
        step = get_object_or_404(PlancheStep, id=step_id, step_type="check")
        if str(step.assigned_to) != str(request.user.id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if step.status != "in_progress":
            return Response(
                {"detail": f"Step is {step.status}, not in_progress."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        target_step_type = request.data.get("target_step_type")
        comment = request.data.get("comment", "")
        if target_step_type not in ("clean", "trad", "edit"):
            return Response({"detail": "Invalid target_step_type."}, status=status.HTTP_400_BAD_REQUEST)

        send_step_to_rework(step.planche, target_step_type, comment)
        return Response({"target_step_type": target_step_type, "status": "rework"})
```

Edit `backend/grimoria/urls.py`:

```python
from pipeline.views import PlancheStepAssignView, PlancheStepCompleteView, PlancheStepRejectView

urlpatterns = [
    ...
    path("api/planche-steps/<uuid:step_id>/reject/", PlancheStepRejectView.as_view(), name="step-reject"),
]
```

- [ ] **Step 4: Run the tests and confirm they pass**

```bash
.venv/Scripts/pytest pipeline/tests/test_rework.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/ backend/grimoria/urls.py
git commit -m "feat: add check rejection / rework endpoint"
```

---

## Task 13: Discord notifications

**Files:**

- Create: `backend/notifications/__init__.py`, `backend/notifications/apps.py`, `backend/notifications/services.py`, `backend/notifications/tasks.py`
- Modify: `backend/grimoria/settings.py`
- Test: `backend/notifications/tests/__init__.py`, `backend/notifications/tests/test_services.py`, `backend/notifications/tests/test_tasks.py`

**Interfaces:**

- Produces: `notifications.services.notify(team, event_type, payload: dict) -> None` — no-op if `team.discord_webhook_url` is empty, otherwise enqueues `notifications.tasks.send_discord_notification`.
- Produces: `notifications.tasks.send_discord_notification(webhook_url, event_type, payload)` (Celery task, retries up to 3 times on request failure).

- [ ] **Step 1: Create the app**

```bash
.venv/Scripts/python manage.py startapp notifications
```

Edit `backend/grimoria/settings.py`, add `"notifications"` to `INSTALLED_APPS`.

- [ ] **Step 2: Write the failing tests**

Create `backend/notifications/tests/__init__.py` (empty) and `backend/notifications/tests/test_services.py`:

```python
from unittest.mock import patch

import pytest

from notifications.services import notify
from teams.models import Team


@pytest.mark.django_db
def test_notify_does_nothing_without_a_webhook_url():
    team = Team.objects.create(name="Team", slug="team")
    with patch("notifications.services.send_discord_notification") as mocked_task:
        notify(team, "chapter_created", {"title": "Chapitre 1"})
    mocked_task.delay.assert_not_called()


@pytest.mark.django_db
def test_notify_enqueues_task_when_webhook_url_is_set():
    team = Team.objects.create(
        name="Team", slug="team", discord_webhook_url="https://discord.com/api/webhooks/x/y"
    )
    with patch("notifications.services.send_discord_notification") as mocked_task:
        notify(team, "chapter_created", {"title": "Chapitre 1"})
    mocked_task.delay.assert_called_once_with(
        "https://discord.com/api/webhooks/x/y", "chapter_created", {"title": "Chapitre 1"}
    )
```

Create `backend/notifications/tests/test_tasks.py`:

```python
from unittest.mock import patch

import pytest
import requests

from notifications.tasks import send_discord_notification


def test_message_formats_chapter_created_event():
    with patch("notifications.tasks.requests.post") as mocked_post:
        mocked_post.return_value.raise_for_status.return_value = None
        send_discord_notification(
            "https://discord.com/api/webhooks/x/y", "chapter_created", {"title": "Chapitre 1"}
        )
    _, kwargs = mocked_post.call_args
    assert "Chapitre 1" in kwargs["json"]["content"]


def test_task_retries_on_request_failure():
    with patch("notifications.tasks.requests.post", side_effect=requests.RequestException("boom")):
        with pytest.raises(Exception):
            send_discord_notification.apply(
                args=["https://discord.com/api/webhooks/x/y", "chapter_created", {"title": "Chapitre 1"}],
                throw=True,
            )
```

- [ ] **Step 3: Run the tests and confirm they fail**

```bash
.venv/Scripts/pytest notifications/ -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'notifications.services'`

- [ ] **Step 4: Implement the task and service**

Create `backend/notifications/tasks.py`:

```python
import requests
from celery import shared_task
from django.conf import settings

MESSAGES = {
    "chapter_created": "📖 Nouveau chapitre créé : {title}",
    "step_available": "✅ Planche {page_number} disponible pour l'étape {step_type}",
    "check_failed": "⚠️ Planche {page_number} renvoyée en rework ({step_type}) : {comment}",
    "chapter_ready": "🎉 Chapitre {title} prêt et exporté !",
}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_discord_notification(self, webhook_url, event_type, payload):
    content = MESSAGES.get(event_type, event_type).format(**payload)
    timeout = getattr(settings, "DISCORD_WEBHOOK_TIMEOUT", 10)
    try:
        response = requests.post(webhook_url, json={"content": content}, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise self.retry(exc=exc)
```

Create `backend/notifications/services.py`:

```python
from .tasks import send_discord_notification


def notify(team, event_type, payload):
    if not team.discord_webhook_url:
        return
    send_discord_notification.delay(team.discord_webhook_url, event_type, payload)
```

Edit `backend/grimoria/settings.py`, add near the other env-driven settings:

```python
DISCORD_WEBHOOK_TIMEOUT = env.int("DISCORD_WEBHOOK_TIMEOUT", default=10)
```

- [ ] **Step 5: Run the tests and confirm they pass**

```bash
.venv/Scripts/pytest notifications/ -v
```

Expected: PASS (4 tests)

- [ ] **Step 6: Wire `notify()` into the four trigger points**

Edit `backend/pipeline/views.py`:

- In `ChapterCreateView.post`, after the `for planche in created_planches: recompute_step_statuses(planche)` loop, add:

```python
        from notifications.services import notify
        notify(chapter.series.team, "chapter_created", {"title": chapter.title or f"Chapitre {chapter.number}"})
```

- In `PlancheStepCompleteView.post`, after `recompute_step_statuses(step.planche)`, notify for each step that just became available, and — if the completed step was itself a `check` — check for chapter readiness:

```python
        from notifications.services import notify
        from .services import chapter_is_ready
        team = step.planche.chapter.series.team
        for available_step in recompute_step_statuses(step.planche):
            notify(
                team,
                "step_available",
                {"page_number": step.planche.page_number, "step_type": available_step.step_type},
            )
        if step.step_type == "check" and chapter_is_ready(step.planche.chapter):
            chapter = step.planche.chapter
            chapter.status = "ready"
            chapter.save(update_fields=["status"])
            notify(team, "chapter_ready", {"title": chapter.title or f"Chapitre {chapter.number}"})
```

Replace the earlier single `recompute_step_statuses(step.planche)` call in that view with the block above (it now calls the service and captures its return value instead of discarding it).

- In `PlancheStepRejectView.post`, after `send_step_to_rework(...)`, add:

```python
        from notifications.services import notify
        team = step.planche.chapter.series.team
        notify(
            team,
            "check_failed",
            {"page_number": step.planche.page_number, "step_type": target_step_type, "comment": comment},
        )
```

- [ ] **Step 7: Update the affected pipeline tests to assert notifications fire**

Edit `backend/pipeline/tests/test_step_actions.py`'s `test_completing_a_step_saves_deliverable_and_recomputes_dependents` — add a mock so the test doesn't attempt a real HTTP call, and assert `notify` isn't triggered here (no webhook URL configured on the fixture's team by default) — no change needed since `Team.discord_webhook_url` defaults to `""` and `notify()` no-ops. Run the full suite to confirm nothing broke:

```bash
.venv/Scripts/pytest pipeline/ notifications/ -v
```

Expected: PASS (all tests)

- [ ] **Step 8: Commit**

```bash
git add backend/notifications/ backend/pipeline/ backend/grimoria/settings.py
git commit -m "feat: send Discord notifications for chapter/step lifecycle events"
```

---

## Task 14: Chapter export generation

**Files:**

- Modify: `backend/pipeline/models.py`
- Create: `backend/pipeline/tasks.py`
- Modify: `backend/pipeline/views.py`
- Modify: `backend/pipeline/urls.py`
- Modify: `backend/grimoria/urls.py`
- Test: `backend/pipeline/tests/test_export.py`

**Interfaces:**

- Produces: `pipeline.models.Export` (`id`, `chapter` OneToOne, `generated_at`, `file_url`).
- Produces: `pipeline.tasks.generate_chapter_export(chapter_id)` (Celery task: zips every planche's `edit` deliverable, uploads the zip to Supabase Storage via the service-role key, creates/updates the `Export` row, sets `Chapter.status = "exported"`).
- Produces: `GET /api/teams/<team_id>/chapters/<chapter_id>/export/` (member-only; 404 until the export exists, then returns `{"file_url": "..."}`).

- [ ] **Step 1: Add the `Export` model**

Edit `backend/pipeline/models.py`, add at the end:

```python
class Export(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chapter = models.OneToOneField(Chapter, on_delete=models.CASCADE, related_name="export")
    generated_at = models.DateTimeField(auto_now_add=True)
    file_url = models.URLField()
```

```bash
.venv/Scripts/python manage.py makemigrations pipeline
.venv/Scripts/python manage.py migrate
```

- [ ] **Step 2: Write the failing test for the export task**

Create `backend/pipeline/tests/test_export.py`:

```python
import zipfile
from io import BytesIO
from unittest.mock import patch

import pytest

from pipeline.models import Chapter, Export, Planche, PlancheStep, Series
from pipeline.tasks import generate_chapter_export
from teams.models import Team


@pytest.fixture
def ready_chapter(db):
    team = Team.objects.create(name="Team", slug="team")
    series = Series.objects.create(team=team, name="Series", slug="series")
    chapter = Chapter.objects.create(
        series=series, number=1, title="Chapitre 1",
        created_by="11111111-1111-1111-1111-111111111111", status="ready",
    )
    for page_number in (1, 2):
        planche = Planche.objects.create(
            chapter=chapter, page_number=page_number, raw_image=f"https://storage.example/{page_number}-raw.png"
        )
        PlancheStep.objects.create(
            planche=planche, step_type="edit", status="done",
            deliverable=f"https://storage.example/{page_number}-edit.png",
        )
    return chapter


@pytest.mark.django_db
def test_generate_chapter_export_builds_zip_and_marks_chapter_exported(ready_chapter):
    fake_image_bytes = b"fake-png-bytes"

    with patch("pipeline.tasks.requests.get") as mocked_get, \
         patch("pipeline.tasks.upload_zip_to_storage", return_value="https://storage.example/exports/1.zip") as mocked_upload:
        mocked_get.return_value.content = fake_image_bytes
        mocked_get.return_value.raise_for_status.return_value = None

        generate_chapter_export(str(ready_chapter.id))

    ready_chapter.refresh_from_db()
    assert ready_chapter.status == "exported"
    export = Export.objects.get(chapter=ready_chapter)
    assert export.file_url == "https://storage.example/exports/1.zip"

    zip_bytes = mocked_upload.call_args[0][0]
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        assert sorted(zf.namelist()) == ["001.png", "002.png"]
        assert zf.read("001.png") == fake_image_bytes
```

- [ ] **Step 3: Run the test and confirm it fails**

```bash
.venv/Scripts/pytest pipeline/tests/test_export.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.tasks'`

- [ ] **Step 4: Implement the export task**

Create `backend/pipeline/tasks.py`:

```python
import io
import zipfile

import requests
from celery import shared_task
from django.conf import settings

from .models import Chapter, Export


def upload_zip_to_storage(zip_bytes, path):
    url = f"{settings.SUPABASE_URL}/storage/v1/object/exports/{path}"
    response = requests.put(
        url,
        data=zip_bytes,
        headers={
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/zip",
        },
        timeout=60,
    )
    response.raise_for_status()
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/exports/{path}"


@shared_task
def generate_chapter_export(chapter_id):
    chapter = Chapter.objects.get(id=chapter_id)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for planche in chapter.planches.order_by("page_number"):
            edit_step = planche.steps.get(step_type="edit")
            image_response = requests.get(edit_step.deliverable, timeout=30)
            image_response.raise_for_status()
            zf.writestr(f"{planche.page_number:03d}.png", image_response.content)

    zip_bytes = buffer.getvalue()
    file_url = upload_zip_to_storage(zip_bytes, f"{chapter.id}.zip")

    Export.objects.update_or_create(chapter=chapter, defaults={"file_url": file_url})
    chapter.status = "exported"
    chapter.save(update_fields=["status"])
```

- [ ] **Step 5: Run the test and confirm it passes**

```bash
.venv/Scripts/pytest pipeline/tests/test_export.py -v
```

Expected: PASS

- [ ] **Step 6: Trigger the export task when a chapter becomes ready**

Edit `backend/pipeline/views.py`, in `PlancheStepCompleteView.post`, extend the "chapter ready" branch added in Task 13:

```python
        if step.step_type == "check" and chapter_is_ready(step.planche.chapter):
            chapter = step.planche.chapter
            chapter.status = "ready"
            chapter.save(update_fields=["status"])
            notify(team, "chapter_ready", {"title": chapter.title or f"Chapitre {chapter.number}"})
            from .tasks import generate_chapter_export
            generate_chapter_export.delay(str(chapter.id))
```

- [ ] **Step 7: Add the export status endpoint**

Edit `backend/pipeline/views.py`, add:

```python
from .models import Export


class ChapterExportView(APIView):
    permission_classes = [IsTeamMember]

    def get(self, request, team_id, chapter_id):
        export = get_object_or_404(Export, chapter_id=chapter_id, chapter__series__team_id=team_id)
        return Response({"file_url": export.file_url, "generated_at": export.generated_at})
```

Edit `backend/pipeline/urls.py`, add:

```python
    path(
        "<uuid:team_id>/chapters/<uuid:chapter_id>/export/",
        views.ChapterExportView.as_view(),
        name="chapter-export",
    ),
```

- [ ] **Step 8: Write a test for the export endpoint**

Add to `backend/pipeline/tests/test_export.py`:

```python
import jwt
from django.test import override_settings
from rest_framework.test import APIClient

from teams.models import TeamMembership

SECRET = "test-secret"
MEMBER = "22222222-2222-2222-2222-222222222222"


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_export_endpoint_404s_until_export_exists(ready_chapter):
    TeamMembership.objects.create(team=ready_chapter.series.team, user_id=MEMBER)
    client = APIClient()
    token = jwt.encode({"sub": MEMBER, "email": "x@example.com", "aud": "authenticated"}, SECRET, algorithm="HS256")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.get(f"/api/teams/{ready_chapter.series.team_id}/chapters/{ready_chapter.id}/export/")

    assert response.status_code == 404


@pytest.mark.django_db
@override_settings(SUPABASE_JWT_SECRET=SECRET)
def test_export_endpoint_returns_file_url_once_generated(ready_chapter):
    TeamMembership.objects.create(team=ready_chapter.series.team, user_id=MEMBER)
    Export.objects.create(chapter=ready_chapter, file_url="https://storage.example/exports/1.zip")
    client = APIClient()
    token = jwt.encode({"sub": MEMBER, "email": "x@example.com", "aud": "authenticated"}, SECRET, algorithm="HS256")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.get(f"/api/teams/{ready_chapter.series.team_id}/chapters/{ready_chapter.id}/export/")

    assert response.status_code == 200
    assert response.json()["file_url"] == "https://storage.example/exports/1.zip"
```

- [ ] **Step 9: Run the full backend test suite**

```bash
.venv/Scripts/pytest -v
```

Expected: PASS (all tests)

- [ ] **Step 10: Commit**

```bash
git add backend/pipeline/ backend/grimoria/urls.py
git commit -m "feat: generate and expose chapter export zip"
```

---

## Post-plan check

After Task 14, the backend exposes a complete, independently testable API: auth, teams/invites/members, series/chapters/planches with full pipeline dependency and rework logic, Discord notifications, and export generation — all covered by `pytest`. The frontend plan (separate document) will consume this API; no frontend code is part of this plan.
