# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: not decided yet.

## [Unreleased]

### Security

- Private repositories are now refused: the webhook ignores them, and the worker re-checks with GitHub before any AI call. Before, "public repositories only" was a note, not a rule.
- `/health` no longer queries Postgres and is rate-limited (30/min), so nobody can keep the free Neon database awake through it.

### Fixed

- A paused, failed, or crashed review that was resumed always ended as "failed": its old AI steps were still saved and the new ones collided with them. Resuming now clears the old attempt's steps and notes (and votes on them) first.

## [1.0.0] - 2026-10-21

First release: all six phases approved.

### Security

- Phase 3: GitHub OAuth login (state bound to the browser, PKCE S256), Redis sessions, CSRF tokens, per-installation and per-repo authorization, rate limits, CORS allowlist, security headers, uniform errors, per-model Pacific-day quota counters, CI Actions pinned to SHAs. Live injection suite 8/8 on Flash Lite.
- Phase 2 hardening: linter argument injection closed (`--`), tarball size/entry caps, bounded tools, untrusted-content marking for file names and tool output, bot-only review markers, httpx URLs not logged.
- Webhook replay protection keys on the signature (the delivery header is unsigned); non-ASCII signature headers rejected cleanly; repo name and SHA validated before use in API paths.
- Each container receives only the secrets it uses; frontend container runs as non-root.
- Tests can no longer read the real `.env`.

### Fixed

- Pages no longer fade in from invisible: on phones Lighthouse saw no first paint at all. They now slide in without changing opacity.
- Frontend pages answer HEAD, so uptime monitors see the site as up.
- certifi updated to 2026.10.19 (PYSEC-2026-4320).
- The agent's last step now requires a `submit_findings` call (Gemini `tool_choice: "any"`); before, 10 of 48 benchmark runs ended with no answer.
- `/health` checks time out after 2 s; worker retries GitHub 403 rate limits and stops wasting the last retry; duplicate commits answer 200 "duplicate".

### Added

- Phase 6: hosted at $0 with no card on Render (one container: API, worker, frontend) with Render Key Value, Neon Postgres and an UptimeRobot keep-alive (`render.yaml`, ADR 0004, deploy runbook). Public repository with an MIT license and a rewritten README. Useful score from the user's own votes (`GET /api/feedback/summary`).
- Dashboard explains itself: what a review is, statuses, what Useful / Not useful does, "Saved" confirmation, link to the pull request, what to do next; rows, comments and steps animate in; pages fade in.
- Landing rebuilt with scroll-craft's method: a brutalist live surface where scroll types a real pull request and DiffMate's real recorded review lands on the bug, real benchmark numbers, and a "plant a bug" input showing four real recorded reviews (`benchmark/demo.py`).
- Phase 5: dashboard (reviews list, review detail with findings, Useful / Not useful votes, agent trace) and landing page (tilting hero diff card, pinned five-step pipeline story, results from the real benchmark). Reduced motion and phones get a stacked, still layout. History API routing, self-hosted fonts, Vitest tests in `make test` and CI.
- Phase 4: offline benchmark of 60 PR cases (35 seeded, 15 real, 10 clean; 12 held out) with a resumable runner and scorer (`make bench`, `make bench-holdout`, `make bench-score`). Flash Lite: precision 100%, recall 55% (dev) / 30% (holdout), 0 false positives per PR, estimated $0.003-0.004 per PR.
- Phase 2: AI review agent (Gemini free tier) with four read-only tools, ruff/ESLint hints, step/token/daily/per-minute caps, findings filter, one inline review per commit, run history in Postgres (migrations 0001-0002).
- Phase 1 backend: `/health`, `POST /webhooks/github` (HMAC check, replay protection, 1 MiB limit), arq queue with one job per commit, worker posting a test comment with retries, GitHub App JWT and repo-scoped installation tokens, JSON logs. 29 unit/security tests.
- Docker compose stack, backend and frontend Dockerfiles, CI (ruff, pytest, pip-audit, pnpm build and audit, gitleaks), Makefile, `.env.example`, minimal frontend.
- Runbooks: GitHub App setup with cloudflared; Docker and uv install.
- Project documentation set: README, PRD, plan, architecture, API, threat model, benchmark method, testing, ADRs, runbooks, security and contributing guides.
- `docs/RULES.md` (one-page rulebook) and `docs/BUILD_PROMPT.md` (original brief); `DESIGN.md` moved into `docs/`.
- `reports/` folder: phase reports and weekly logs with a section per day.
- Phase 0 decisions in `docs/PLAN.md`; ADR 0003 (free-tier LLM, $0 rule); ADR 0001 updated with decided stack.
