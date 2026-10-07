# ADR 0001: Stack

**Status:** Accepted (2026-10-06)
**Date:** 2026-10-06
**Deciders:** Vighnesh

## Context

A 5-week solo build that must look like real end-to-end engineering: backend, queue, database, auth, frontend, deployment. Hard constraint: $0 total spend. The dev machine has Python 3.14 (not 3.12), Node 22, pnpm, and cloudflared; no Docker or uv yet.

## Decision

- Backend: Python 3.12 managed by **uv**, FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic
- Queue: Redis + **arq**; job ID = `{repo}:{pr}:{sha}` so a commit is queued once
- Database: Postgres 16
- Frontend: TypeScript, React, Vite, Framer Motion (`motion` package), **pnpm**
- Dashboard login: **GitHub OAuth** (state + PKCE), server-side session in Redis
- Local webhooks: **cloudflared** quick tunnel
- Packaging: Docker and docker compose; Caddy as reverse proxy
- CI: GitHub Actions
- LLM: see [ADR 0003](0003-free-tier-llm.md)

## Options considered

| Choice | Picked | Alternative | Why |
| --- | --- | --- | --- |
| Python tooling | uv | pip + venv | Installs 3.12 without touching system Python; fast; lockfile |
| Queue library | arq | RQ | Async like FastAPI and the GitHub/LLM calls; job IDs give dedupe for free |
| Queue backend | Redis | Postgres-only queue | More recognizable pattern; also holds sessions, replay IDs, rate limits |
| Login | GitHub OAuth | No login | Needed to show each user only their installations' runs |
| Tunnel | cloudflared | smee.io | Already installed, no account, no extra dependency |
| JS package manager | pnpm | npm | Already installed; strict, fast installs |
| Backend language | Python | Node | Better fit for ruff and LLM tooling |

## Consequences

- Easier: one async model end to end; Redis does four jobs (queue, sessions, replay IDs, rate limits), so there are fewer services.
- Harder: Docker must be installed by the user (needs sudo); the cloudflared URL changes each run, so the App's webhook URL must be updated during development.
- Revisit: hosting (Phase 6, free options only); final name.

## Action items

1. [ ] User installs Docker Engine + compose plugin and uv
2. [ ] Phase 1 scaffolds `pyproject.toml`, `package.json`, `docker-compose.yml` with the approved dependencies
