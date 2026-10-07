# Phase 1: Foundations

**Dates:** 2026-10-06 to 2026-10-07
**Status:** approved (2026-10-07) by Vighnesh; schema approved for the first migration

## Goal

Webhook in, job queued once per commit, worker posts a test comment on a real PR. Stack runs with `docker compose up`.

## What was built

- `GET /health` (Postgres + Redis checks, 503 when degraded)
- `POST /webhooks/github`: 1 MiB limit, HMAC SHA-256 constant-time check, replay protection (delivery ID `SET NX`, 7 days), PR event filter, 503 + delivery release when the queue is down
- arq queue: job ID `review:{repo}:{pr}:{sha}`, results kept 7 days, so one run per commit
- Worker: repo-scoped installation token → one PR comment; retries with backoff (5 s × 2^try) on 429/5xx/network, no retry on 4xx; max 3 tries
- GitHub App JWT (RS256, 9 min expiry, 60 s clock-drift allowance)
- JSON logs without secrets or bodies
- Docker compose (postgres, redis, backend, worker, frontend; all ports on 127.0.0.1), CI, Makefile, `.env.example`
- Runbooks for the App setup and Docker install

## Acceptance checks (with output)

- [x] Webhook tests pass (bad signature 401, replay ignored):

```
$ make test
29 passed, 1 skipped in 5.20s
SKIPPED [1] tests/integration/test_queue_redis.py:25: Redis not running; start it with: docker compose up -d redis
```

- [x] `make lint`: ruff "All checks passed!", 35 files formatted, TypeScript build OK
- [x] `pip-audit` and `pnpm audit --prod`: "No known vulnerabilities found"
- [x] `docker compose up` starts all 5 services; `/health` → `{"status":"ok"}` locally and through the tunnel
- [x] Redis integration test passes against real Redis 7 (`1 passed`): same commit queued once, next commit queued
- [x] gitleaks v8.30.1 directory scan: "no leaks found"
- [x] Backend and frontend Docker images build; backend runs as non-root uid 1000; worker fails fast without required env
- [x] Live test on `diffmate-playground` PR #1 (2026-10-07):

```
01:42:09 POST /webhooks/github 202  queued review 5-Vighnesh-0/diffmate-playground#1@13e22c0
01:42:10 POST /app/installations/…/access_tokens 201 Created
01:42:11 POST /repos/5-Vighnesh-0/diffmate-playground/issues/1/comments 201 Created   (job took 1.05 s)
         forged signature via tunnel → 401 Unauthorized, no job
01:44:27 redelivery of the same delivery ID → 200, "duplicate delivery … ignored", still 1 comment
```
- [x] Code review and security review done (two independent subagents); fixes applied test-first
- [x] Fresh verification after fixes (2026-10-07 01:50 UTC):

```
make lint      → All checks passed! / 36 files already formatted / ✓ built   (exit 0)
pytest         → 47 passed in 0.85s   (incl. real-Redis integration test)
pip-audit      → No known vulnerabilities found
pnpm audit     → No known vulnerabilities found
gitleaks dir   → 2 hits, both in .env (git-ignored, expected); none in tracked files
```

- [x] Live regression after fixes: second commit `712ae42` on PR #1 → 202 → comment 201 Created

## Review findings and what was done

| Source | Finding | Action |
| --- | --- | --- |
| Security | Non-ASCII signature header → 500 | Fixed (byte compare) + test |
| Security | Delivery ID not signed → replay with a new ID | Fixed: replay key is the signature + test |
| Security | Repo name / SHA unvalidated in API paths | Fixed: strict patterns, 400 + tests |
| Security | Every container got every secret | Fixed: per-service env, verified by listing env names |
| Security | Frontend container ran as root | Fixed: `USER node`, verified |
| Security | Lost response could double-comment | Deferred to Phase 2 (comment posting is rewritten) |
| Security | Actions/images pinned by tag | Deferred to Phase 3 (supply-chain hardening) |
| Security | ruff in runtime image | Rejected: the worker runs ruff on PR files in Phase 2 |
| Code | `/health` could hang | Fixed: 2 s timeout per check + test |
| Code | Wasted 3rd retry hid the real error | Fixed: no Retry on the last try + test |
| Code | GitHub 403 rate limits not retried | Fixed + tests |
| Code | Duplicate commit answered "queued" | Fixed: 200 "duplicate" + test |
| Code | Shutdown masked startup errors | Fixed + test |
| Code | Missing tests (400 paths, TTL, startup) | Added |
| Code | Tests read the real `.env` | Fixed: tests force fake env and no env file + test |
| Code | Failed job blocks its commit for 7 days | Deferred to Phase 2: run-per-commit moves to the `runs` table |

## Decisions and ADRs

- No tables yet; the schema proposal goes to the gate for approval.
- Installation tokens scoped to one repo and the minimum permissions.

## Problems and fixes

- Postgres unreachable from the backend: the DB password contained `@`, which ends the password inside a connection URL, so the host parsed wrong (`gaierror`). Fix: user set a URL-safe password; empty volume reset with `docker compose down -v` (user ran/approved). `.env.example` now says letters and digits only.
- The cloudflared quick-tunnel URL changed after a restart; the App's webhook URL was updated.
- Secrets exposure during setup (all caught and handled): a debug command printed a 40-hex value from a mis-filled `.env` line (likely the OAuth client secret; user asked to rotate it); a debug print showed 4 characters of the old DB password (password replaced); one generated DB password appeared unmasked in chat (discarded, never used). Lesson applied: checks now report only set/empty/shape, never values.

- ruff B008 flagged FastAPI's `Depends` defaults: configured `extend-immutable-calls` (ruff's documented fix).
- The editor's Pyright couldn't see the venv: added `[tool.pyright]` venv settings to `pyproject.toml`.

## Metrics

- 47 tests, 0 failures. Webhook to comment: ~1 s. Spend: $0.

## Open questions for next phase

- Schema approval: proposal in `docs/architecture.md` → Data model (DDL dry-run on Postgres 16 created 9 tables, rolled back).
- Phase 2: pick the exact free model after a small trial on the free tier.
