# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: not decided yet.

## [Unreleased]

### Security

- Webhook replay protection keys on the signature (the delivery header is unsigned); non-ASCII signature headers rejected cleanly; repo name and SHA validated before use in API paths.
- Each container receives only the secrets it uses; frontend container runs as non-root.
- Tests can no longer read the real `.env`.

### Fixed

- `/health` checks time out after 2 s; worker retries GitHub 403 rate limits and stops wasting the last retry; duplicate commits answer 200 "duplicate".

### Added

- Phase 1 backend: `/health`, `POST /webhooks/github` (HMAC check, replay protection, 1 MiB limit), arq queue with one job per commit, worker posting a test comment with retries, GitHub App JWT and repo-scoped installation tokens, JSON logs. 29 unit/security tests.
- Docker compose stack, backend and frontend Dockerfiles, CI (ruff, pytest, pip-audit, pnpm build and audit, gitleaks), Makefile, `.env.example`, minimal frontend.
- Runbooks: GitHub App setup with cloudflared; Docker and uv install.
- Project documentation set: README, PRD, plan, architecture, API, threat model, benchmark method, testing, ADRs, runbooks, security and contributing guides.
- `docs/RULES.md` (one-page rulebook) and `docs/BUILD_PROMPT.md` (original brief); `DESIGN.md` moved into `docs/`.
- `reports/` folder: phase reports and weekly logs with a section per day.
- Phase 0 decisions in `docs/PLAN.md`; ADR 0003 (free-tier LLM, $0 rule); ADR 0001 updated with decided stack.
