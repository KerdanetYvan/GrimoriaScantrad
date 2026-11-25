<div align="center">

# Grimoria

**The back-office where a scanlation team turns raw scans into finished chapters.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.18-A30000?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.6-37814A?logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-planned-000000?logo=nextdotjs&logoColor=white)

</div>

## Why

A few years ago, I promised my scanlation team a proper tool to work
together. Grimoria is me keeping that promise: a personal challenge, and an
attempt to give the team a fresh boost.

## How a chapter gets made

Every page goes through four steps. Clean and translation run in parallel,
typesetting waits for both, and a failed check sends the page back with a
comment.

```mermaid
flowchart LR
    raw([Raw scan]) --> clean[Clean]
    raw --> trad[Translate]
    clean --> edit[Typeset]
    trad --> edit
    edit --> check{Check}
    check -- approved --> out([Publish or export])
    check -. rework .-> edit
```

Members pick the steps that match their roles, chapter by chapter. Leads
create chapters, invite people, and decide when to publish. Key events land in
the team's Discord.

## Status

The API is being built step by step, following the
[roadmap](docs/plans/backend-roadmap.md).

- [x] Project scaffold, tests and CI
- [x] Environment, PostgreSQL and Celery
- [ ] Supabase authentication
- [ ] Teams, members and invites
- [ ] Chapters and the production pipeline
- [ ] Discord notifications
- [ ] Publishing and export
- [ ] Web app (Next.js)

## Run the API locally

<details>
<summary>Requirements: Python 3.12 and Docker</summary>

From `apps/api`:

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # .venv/bin/pip on Linux/macOS
cp .env.example .env                            # then set SECRET_KEY (see the comment in the file)
docker compose up -d                            # PostgreSQL and Redis
.venv/Scripts/python manage.py migrate
.venv/Scripts/pytest
```

Start the Celery worker (on Windows, `--pool=solo` is required):

```bash
.venv/Scripts/celery -A config worker --pool=solo -l info
```

</details>

## Repository

```
apps/api/      Django REST API
docs/specs/    product specification (French)
docs/plans/    roadmap (French)
```

Every change goes through a pull request to `master`, and the CI must pass
before merging. Commits follow
[Conventional Commits](https://www.conventionalcommits.org/).

## License

All rights reserved. The code is public for reference; reuse requires
permission.
