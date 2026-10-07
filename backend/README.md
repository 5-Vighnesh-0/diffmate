# Backend

Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Redis queue. See `../docs/architecture.md`.

## Layout

```
app/
  api/      HTTP routes (webhook, auth, dashboard)
  core/     config, security, logging
  db/       models, sessions, migrations glue
  github/   App auth (JWT, installation tokens), API client
  queue/    job enqueue, worker, retries
  agent/    loop, tools, prompts, schema
  checks/   ruff and ESLint runners
alembic/    migrations
tests/
```

## Run

```bash
make dev    # from repo root
make test
```

## Rules

- Tests first for logic, filters, and the agent loop.
- Agent tools are read-only.
- Parameterized queries only.
- Schema changes need a migration and approval.

Env var names are in `../.env.example`.
