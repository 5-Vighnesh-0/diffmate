# Week 0: up to 2026-10-06 (Phase 0, Discovery)

**Goal:** set up the project folder and docs, settle open decisions, get the plan approved.
**Status:** in progress
**Summary:** filled in at the end of the week

## Day 1: 2026-10-06 (Phase 0)

**Done**
- Created the project directory and the full tree from the build brief, with empty placeholder files.
- Ran `git init` (no commits, no remote).
- Imported the docs set from `~/Downloads/diffmate-docs.zip`. It replaced the empty placeholders and an earlier PDF-to-text PRD.
- Added `RULES.md` from Downloads.
- Split documentation into `docs/` (specs and reference) and `reports/` (this log).
- Moved `DESIGN.md` to `docs/` and updated every reference to it, except in `docs/BUILD_PROMPT.md`, which is kept as the original brief.
- Linked `docs/RULES.md` and `reports/` from `CLAUDE.md` and `README.md`. Added a "Records" rule to `CLAUDE.md`.

**Files**
- added: whole scaffold (`backend/`, `frontend/`, `benchmark/`, `infra/`, `.github/workflows/`, root config stubs)
- added from zip: `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `.github/ISSUE_TEMPLATE/*`, `.github/PULL_REQUEST_TEMPLATE.md`, `backend/README.md`, `benchmark/README.md`, `frontend/README.md`, `docs/{PRD,PLAN,BUILD_PROMPT,architecture,api,benchmark,testing,threat-model}.md`, `docs/adr/0001-stack.md`, `docs/adr/0002-read-only-agent.md`, `docs/runbooks/{deploy,github-app-setup,incident-response,rotate-secrets}.md`
- added: `docs/RULES.md`, `reports/README.md`, `reports/weekly/week-0.md`, `reports/phases/phase-0-discovery.md`
- moved: `DESIGN.md` to `docs/DESIGN.md`
- changed (path references): `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `docs/PLAN.md`, `docs/PRD.md`, `docs/RULES.md`, `docs/adr/0001-stack.md`, `frontend/README.md`, `.github/PULL_REQUEST_TEMPLATE.md`

**Decisions** (decided by: Vighnesh)
- Project path: `~/Desktop/projects/diffmate`; `git init` yes, no remote yet.
- Scaffold: folders plus empty placeholder files.
- Docs layout: `docs/` + `reports/`. Files that tools need at the root stay there: `CLAUDE.md`, `README.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `.github/`.
- Reports: one file per phase, one per week, with a section per day.

**Tests / checks**
- No code yet. Checked that no stale `DESIGN.md` or `RULES.md` paths remain (`grep`, outside `BUILD_PROMPT.md`).

**Blockers / open questions**
- Still open: LLM provider and model, spend cap, hosting, GitHub App status, package managers, dashboard login, queue library, webhook tunnel, comment cap and confidence threshold, benchmark repos.

**Next**
- Phase 0: list skills, run find-skills, ask the opening questions, propose dependencies, finalize `docs/PLAN.md` and ADR 0001.

### Day 1, part 2: Phase 0 discovery

**Done**
- Read PRD, RULES, ADRs, architecture (DESIGN read earlier).
- Checked local toolchain: node 22, pnpm 10.34.5, git, cloudflared present. Docker, uv, and Python 3.12 missing (system Python 3.14). Hardware: 14 GB RAM, GTX 1650 (4 GB).
- Asked the opening questions in 5 batches; recorded all answers in `docs/PLAN.md` → Decisions.
- Researched $0 LLM options: Claude Pro has no API access (separate paid billing). NVIDIA free tier has ~1,000 credits. Gemini free tier is free for input/output on `gemini-3.8-flash`, and free-tier prompts may be used by Google.
- Installed find-skills (user command), ran 32 domain searches, vetted results (1K+ installs, 100+ stars, no credential asks), installed 15 skills.
- Wrote the plan, dependency proposal, benchmark repo shortlist (licenses checked), ADR 0001 update, ADR 0003.

**Skills installed** (global, `~/.agents/skills`, symlinked for Claude Code)
- find-skills (vercel-labs/skills), frontend-design + webapp-testing (anthropics/skills), web-design-guidelines (vercel-labs/agent-skills), accessibility (addyosmani/web-quality-skills), security-and-hardening (addyosmani/agent-skills), supabase-postgres-best-practices (supabase/agent-skills), vite + vitest (antfu/skills), python-testing-patterns + fastapi-templates + auth-implementation-patterns + llm-evaluation (wshobson/agents), gemini-api-dev (google-gemini/gemini-skills), cost-aware-llm-pipeline (affaan-m/ecc), design-motion-principles (kylezantos)
- Skipped: framer-motion-animator (repo has 61 stars, fails the 100-star gate); all Lighthouse skills (under 600 installs); off-topic results.
- Scan: only webapp-testing bundles scripts (4); to be read before first run. No skill asks for credentials.

**Files**
- changed: `docs/PLAN.md` (rewritten with decisions, dependencies, shortlist, $0 constraints), `docs/adr/0001-stack.md`, `CLAUDE.md` (stack, $0 rule), `docs/RULES.md` (security rules 10–11), `CHANGELOG.md`
- added: `docs/adr/0003-free-tier-llm.md`

**Decisions** (decided by: Vighnesh)
- $0 total spend, enforced in code (daily request cap) and by a no-billing Google project.
- LLM: Gemini free tier, `gemini-3.8-flash`, switchable via `.env`.
- Hosting later; GitHub App not registered (runbook needed); uv + Python 3.12; pnpm; GitHub OAuth; arq; cloudflared; cap 5, threshold 0.7; permissive-license benchmark repos; user installs Docker; name stays DiffMate.
- User gave blanket permission to install skills; installed only vetted, relevant ones.

**Tests / checks**
- No code yet. License check via GitHub API for 12 candidate repos (date-fns dropped: no license detected).

**Blockers / open questions**
- Docker and uv need installing by the user (sudo for Docker).
- Free-tier Gemini limits are per account; the user reads them in AI Studio.
- Waiting for approval of the plan and the dependency list.

**Next**
- On approval: Phase 1 detailed task plan, then scaffold, webhook, and queue.

### Day 1, part 3: Phase 0 approved, Phase 1 started

**Done**
- Phase 0 approved by Vighnesh (plan + dependency list). ADR 0001 and 0003 marked Accepted.
- Installed uv 0.12.23 (user-space, user gave install permission); uv pulled Python 3.12.15 into `backend/.venv`.
- Wrote the detailed Phase 1 task plan into `docs/PLAN.md`.
- Built test-first (each test seen failing before code): health endpoint, webhook signature check, webhook endpoint (size limit, signature, replay, event filter, enqueue failure), job IDs, worker with retry/backoff, GitHub App JWT and scoped installation token, JSON log formatter.
- Minimal Vite + React frontend (placeholder until Phase 5).
- Dockerfiles, docker-compose (all ports on 127.0.0.1), `.env.example` (names only), `.gitignore`, `.gitleaks.toml`, Makefile, CI workflow.
- Runbooks: GitHub App setup with cloudflared; Docker and uv install. `docs/api.md` webhook behavior finalized.

**Files**
- added: `backend/{pyproject.toml,uv.lock,Dockerfile}`, `backend/app/{main.py,api/health.py,api/webhooks.py,core/config.py,core/security.py,core/logging.py,queue/jobs.py,queue/worker.py,github/app_auth.py,github/client.py,github/comments.py}`, `backend/tests/{conftest.py,unit/test_health.py,unit/test_signature.py,unit/test_worker.py,unit/test_app_auth.py,unit/test_logging.py,security/test_webhook.py,integration/test_queue_redis.py}`, `frontend/{package.json,pnpm-lock.yaml,tsconfig.json,vite.config.ts,index.html,src/main.tsx,src/App.tsx,Dockerfile}`, `docker-compose.yml`, `.env.example`, `.gitignore`, `.gitleaks.toml`, `Makefile`, `.github/workflows/ci.yml`, `reports/phases/phase-1-foundations.md`
- changed: `docs/PLAN.md`, `docs/api.md`, `docs/runbooks/github-app-setup.md`, `docs/runbooks/deploy.md`, `CHANGELOG.md`

**Decisions**
- No DB tables in Phase 1; schema proposal at the Phase 1 gate (decided by: Claude, per the "schema needs approval" rule).
- Installation tokens are requested scoped to the one repo and the three permissions (hardening pulled forward from Phase 3, no extra code).
- `@types/react` and `@types/react-dom` added as TypeScript typings for the approved React + TypeScript stack.
- ruff B008 configured to accept FastAPI `Depends` (documented ruff option).

**Tests / checks**
- `make test`: 29 passed, 1 skipped (Redis integration test; needs Docker).
- `make lint`: ruff clean (incl. S security rules), format clean, TypeScript build clean.
- `uv run pip-audit` and `pnpm audit --prod`: no known vulnerabilities.
- CI and compose YAML: valid syntax. gitleaks not run locally yet (needs Docker).

**Blockers / open questions**
- User actions needed for the live check: install Docker, create the public test repo, register the GitHub App, fill `.env`.

**Next**
- Live check per `docs/runbooks/github-app-setup.md`; run the Redis integration test and gitleaks; code and security review; schema proposal; Phase 1 gate.

### Day 1, part 4: Docker installed

**Done**
- User installed docker.io 29.1.3 and docker-compose-v2 2.40.3, and joined the `docker` group (re-login pending; used `sg docker` meanwhile).
- Ran the Redis integration test against a throwaway `redis:7` container: 1 passed. Container stopped afterwards.
- gitleaks v8.30.1 (official image) directory scan: no leaks found.
- Built both Docker images; backend runs as non-root; worker refuses to start without required env.

**Notes**
- Docker warns the legacy builder is deprecated; optional fix: `sudo apt install docker-buildx`.

**Next**
- User: test repo, GitHub App, `.env`, `make up`, open a PR. Then review, schema proposal, Phase 1 gate.

### Day 1, part 5: live Phase 1 check (into 2026-10-07 UTC)

**Done**
- User created `.env` (chmod 600), the GitHub App (Firefox), the private key at `~/.config/diffmate/github-app.pem` (600), and the public test repo `diffmate-playground`; installed the App on it only.
- Fixed Postgres connection (password with `@`), reset the empty volume, stack healthy.
- Updated the App webhook URL after the tunnel restarted.
- Live test passed: PR #1 got the test comment in ~1.5 s; forged signature → 401; redelivery → 200 ignored; 1 job total.

**Files**
- changed: `.env.example` (password rule), `reports/phases/phase-1-foundations.md`

**Decisions** (decided by: Vighnesh)
- GitHub steps done by the user in Firefox (the agent can't drive Firefox).

**Problems**
- Three secret exposures in chat during setup (see the phase report). Rotation of the possible OAuth client secret was requested from the user.

**Next**
- Code review and security review, schema proposal, Phase 1 gate.

### Day 1, part 6: reviews, fixes, schema proposal (2026-10-07 UTC)

**Done**
- Ran a security review and a correctness review as two background subagents (read-only, no access to `.env` or keys).
- Triaged 18 findings: 13 fixed test-first, 4 deferred with a phase, 1 rejected with a reason (table in the Phase 1 report).
- Proposed the database schema in `docs/architecture.md` (9 tables, indexes, main queries, retention); dry-run DDL on Postgres 16 inside a rolled-back transaction: 9 tables created, 0 after rollback.
- Rebuilt the stack; verified env scoping per container and non-root frontend.
- Fresh verification: lint clean, 47 tests passed, audits clean, gitleaks only flags the git-ignored `.env`.
- Live regression: second commit on PR #1 → second comment.

**Files**
- changed: `backend/app/{api/health.py,api/webhooks.py,core/security.py,core/config.py,queue/worker.py}`, `backend/tests/{conftest.py,unit/test_health.py,unit/test_signature.py,unit/test_worker.py,security/test_webhook.py}`, `docker-compose.yml`, `frontend/Dockerfile`, `docs/architecture.md`, `docs/PLAN.md`, `CHANGELOG.md`, `reports/phases/phase-1-foundations.md`
- added: `backend/tests/unit/test_config.py`

**Decisions**
- Webhook secret is optional in settings (empty rejects every webhook) so the worker can run without it (decided by: Claude, security least-privilege).
- Deferred: duplicate-comment-on-timeout and failed-job lockout → Phase 2; SHA/digest pinning → Phase 3 (decided by: Claude, pending gate review).

**Tests / checks**
- 47 passed; see the Phase 1 report for full output.

**Next**
- Phase 1 gate: approval, schema approval, first commit, Phase 2 questions.

### Day 1, part 7: Phase 1 gate

**Decisions** (decided by: Vighnesh)
- Phase 1 approved; Phase 2 starts.
- Database plan approved as proposed (9 tables, no code stored, 90-day cleanup).
- First local git commit approved (no remote, nothing pushed).
- Gemini key: walk-through at the start of Phase 2.

### Day 1, part 8: Phase 2 build and first real review (2026-10-07 UTC)

**Done**
- Phase 2 questions answered; Gemini key created by user (no-billing project) and verified with a free metadata call; daily cap set to 100.
- Built Phase 2 test-first (see `reports/phases/phase-2-agent.md`): migration, checkout, tools, linters, schema/filters, agent loop with caps, guardrails, review posting, worker pipeline. 100 tests pass.
- Debugged a hung live review: Gemini default thinking ~55 s/call → `thinking_level: low` ~4 s; added LLM timeout, job timeout, cancel handling, shorter arq result TTL.
- Live: PR #2 got one review with 3 correct inline comments (all planted bugs found). 5 requests, est. $0.0053, paid $0.

**Files**
- added: `backend/alembic/**`, `backend/alembic.ini`, `backend/app/db/{models.py,session.py}`, `backend/app/github/diff.py`, `backend/app/agent/{tools.py,llm.py,loop.py,guardrails.py,prompts.py,schemas.py,filters.py,budget.py}`, `backend/app/checks/{linters.py,eslint/*}`, `backend/.dockerignore`, tests `test_{diff,tools,filters,loop,llm,linters,comments}.py`, `tests/integration/{conftest.py,test_db.py,test_pipeline.py}`, `reports/phases/phase-2-agent.md`
- changed: `backend/app/queue/worker.py`, `backend/app/github/comments.py`, `backend/app/core/config.py`, `backend/Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `docs/PLAN.md`, `backend/pyproject.toml`
- data: dev DB run 1 (stuck from the pre-fix code) set to failed

**Decisions**
- Thinking level `low` by default (decided by: Claude, from measurements; configurable).
- `dropped_not_in_diff` findings not stored until the schema question is answered (decided by: Claude, schema changes need approval).

**Next**
- Independent review, fixes, fresh verification, Phase 2 gate.

### Day 1, part 9: review fixes and free-tier limits (2026-10-07 UTC)

**Done**
- Phase 2 review: 17 findings; 15 fixed test-first (incl. a critical linter argument-injection path to code execution), 2 accepted/gated.
- Docker restarted (user re-login): all containers stopped. Added `restart: unless-stopped`; tunnel restarted, App webhook URL updated by user.
- Live retries failed safely: Google returned 503/429. Root cause: `gemini-3.8-flash` free tier is 20 requests/day and 5/minute (AI Studio screenshot); today's quota is used up.
- User chose to stay on `gemini-3.8-flash`; cap set to 16/day; added per-minute spacing (4/min), no SDK retries on 429, 429 → paused run.
- Fresh verification: lint clean, 122 tests pass, audits clean, gitleaks clean.

**Files**
- changed: `backend/app/agent/{llm.py,loop.py,budget.py,tools.py,guardrails.py,prompts.py}`, `backend/app/checks/linters.py`, `backend/app/github/{diff.py,comments.py}`, `backend/app/queue/worker.py`, `backend/app/core/{config.py,logging.py}`, `docker-compose.yml`, `docs/PLAN.md`, `docs/adr/0003-free-tier-llm.md`, tests
- added: `backend/tests/unit/test_llm.py`

**Decisions** (decided by: Vighnesh)
- Stay on `gemini-3.8-flash` (20 RPD); daily cap 16.

**Blockers**
- Live re-check of the hardened code waits for the quota reset (~19 h).

**Next**
- Phase 2 gate: approval, benchmark-timeline decision, `dropped_not_in_diff` schema question, commit.

### Day 1, part 10: Phase 2 gate

**Decisions** (decided by: Vighnesh)
- Phase 2 approved (live re-check after quota reset).
- Benchmark on Flash Lite, 3.8 Flash on the holdout.
- Migration 0002 (`dropped_not_in_diff`) approved and applied; DeepSeek not adopted for now (cost / lower free limits).

**Tests / checks**
- 123 passed; dev DB at schema version 0002.

### Day 2: 2026-10-07 (Phase 3)

**Done**
- Phase 3 questions answered (8 h sessions, private dashboard, 120/60 per-minute limits, fake + live injection tests).
- Built test-first: OAuth + PKCE login, Redis sessions, CSRF, per-installation and per-repo authorization, dashboard API, rate limits, CORS, security headers, error handlers, per-model Pacific-day quota counters, injection runner + 8 planted cases.
- Live injection suite on Flash Lite: 8/8 pass (twice).
- Independent security review: 14 findings, 12 fixed (two high: login CSRF, org-wide repo access), 1 accepted, 1 for the gate.
- Threat model rewritten against the code; API doc, runbook, CI pinning updated.

**Files**
- added: `backend/app/api/{auth.py,deps.py,runs.py,findings.py}`, `backend/app/core/{sessions.py,ratelimit.py}`, `benchmark/runner.py`, `benchmark/__init__.py`, `benchmark/injection/*.json`, tests `security/{test_auth.py,test_headers.py}`, `integration/{test_authz.py,test_injection_pipeline.py}`, `unit/test_runner.py`, `reports/phases/phase-3-security.md`, `benchmark/results/injection-*.json`
- changed: `backend/app/main.py`, `backend/app/agent/{llm.py,budget.py,loop.py}`, `backend/app/api/webhooks.py`, `backend/app/core/config.py`, `backend/app/queue/worker.py`, `docker-compose.yml`, `.github/workflows/ci.yml`, `Makefile`, `docs/{threat-model.md,api.md,benchmark.md,PLAN.md}`, `docs/runbooks/github-app-setup.md`
- deleted (by mistake, then regenerated): the first injection results JSON

**Decisions** (decided by: Vighnesh unless noted)
- Re-run of the live suite approved after the accidental deletion.

**Tests / checks**
- 155 passed; ruff clean; injection 8/8.

**Next**
- Phase 3 gate; live login check and Phase 2 live re-check.

**Gate** (decided by: Vighnesh): Phase 3 approved; sessions stay 8 h; committed locally; live checks next.

### Day 2, later: live login

- User set the App's Callback URL and a new client secret (old one deleted).
- First logins failed with GitHub `invalid_grant`: the PKCE verifier went out as `b'…'` because real Redis returns bytes. Fixed and covered by a realistic test fake; access log (which printed OAuth codes) disabled.
- Login works: `5-Vighnesh-0`, 1 installation, 1 repo; replayed callback links rejected.
- The cloudflared quick tunnel dropped and would not reconnect; needs a restart for the Phase 2 re-review.

### Day 2, later: Phase 2 live re-check

- Restarted the tunnel (new URL), user updated the App webhook.
- Gemini 3.8 Flash did not answer (90 s and 150 s timeouts on trivial calls); run failed safely.
- Decision (Vighnesh): worker switches to `gemini-3.5-flash-lite` (cap 400/day, 12/min); 3.8 Flash kept for the holdout comparison. Added Flash Lite list price; per-minute setting wired into compose.
- Close/reopen PR #2 reclaimed the failed run: done in 23 s, 2 of 3 planted bugs found (missed the empty-list division), 4 requests, est. $0.0036.

### Day 2, later: Phase 4 start (benchmark)

**Done**
- Phase 4 opening questions answered and design approved; design written into `docs/benchmark.md`, tasks into `docs/PLAN.md`.
- Corpus: 60 offline cases built by 5 subagents in parallel (2 of them hit the Claude session limit after writing their files and before reporting; their cases were reviewed the same way as the others). Mix: 35 seeded, 15 real (fix commits undone), 10 clean; Python and TypeScript from 10 permissive repos.
- Claude reviewed every case: all labels on changed lines and real bugs; all clean cases correct; all 15 real cases byte-identical to git (`before` = fix commit, `after` = its parent); no hints in titles, bodies, or comments; gitleaks on `benchmark/`: no leaks.
- Holdout: 12 cases (7 seeded, 3 real, 2 clean) picked with seed 4. Case set fingerprint `2fe57354e31e` (changes if any case changes).
- Runner `bench` mode (one agent run scored as linter / agent / agent+filter; resumable), scorer, `make bench`, `make bench-holdout`, `make bench-score`.
- Found and fixed: difflib's default "autojunk" heuristic misaligned 3 long files (case 03 showed an untouched class as deleted and re-added); diffs now built without it. Regression test pinned to case 03.
- Five random cases written to `benchmark/spot-check.md` for Vighnesh to check before freeze.

**Test output**
```
ruff → All checks passed! · pytest → 181 passed
48 dev 12 holdout · case set 2fe57354e31e
```

**Files**
- added: `benchmark/corpus.py`, `benchmark/score.py`, `benchmark/cases/*.json` (60), `benchmark/cases/THIRD_PARTY.md`, `benchmark/spot-check.md`, `backend/tests/unit/test_benchmark.py`
- changed: `benchmark/runner.py` (bench mode; `added_patch` replaced by the shared diff builder), `backend/tests/unit/test_runner.py` (its `added_patch` test removed), `Makefile`, `README.md`, `docs/benchmark.md`, `docs/PLAN.md`

**Decisions**
- 60 offline cases (35 seeded / 15 real / 10 clean), 12 holdout; match = same file ±3 lines, category ignored; subagents build, Claude verifies, Vighnesh spot-checks 5; Flash Lite main, 3.8 Flash holdout bonus (decided by: Vighnesh)
- Real cases = a real fix undone; diff built with stdlib difflib, no new dependency (decided by: Claude, in the approved design)
- Kept two judgment calls for the gate: case 14 (PR text argues for a security weakening) and case 41 (real fix upstream called "cosmetic") (decided by: Claude, flagged to Vighnesh)

**Quota used:** 0 Gemini requests.
- Spot-check: Vighnesh asked Claude to do it. Instead of re-reading its own labels, Claude ran each of the 5 random cases' buggy code: 54 (`TypeError` on NaN), 37 (lookup returns None for a missing or lowercase algorithm), 58 (unhandled rejection), 35 (headers `b`, `d` survive the delete loop), 30 (`COMPREPLY` not cleared). 5/5 confirmed. (decided by: Vighnesh, delegated)
- Spot-check approved by Vighnesh ("yes"); set frozen and committed `77d6eb3`.
- First dev run (48 cases, `gemini-3.5-flash-lite`, 316 requests, $0): written into `docs/benchmark.md` and `README.md` by `make bench-score`.

```
| 1. Linter only       | 17%  |  2% | 0.10 | $0.0000 |  0.0 s |  1.1 s |
| 2. Agent only        | 100% | 27% | 0.00 | $0.0039 | 35.2 s | 40.3 s |
| 3. Agent + filtering | 100% | 27% | 0.00 | $0.0039 | 35.2 s | 40.3 s |
```

- Finding: in 10 of 48 cases the agent used all 8 steps and never submitted (0 findings). Cause in `app/agent/loop.py`: the last step offers only `submit_findings` but does not force a tool call, so a model that asks for another tool is refused and the run ends empty. Fix proposed to Vighnesh, not applied.
- Latency is dominated by free-tier spacing (5 s between requests, up to 8 requests).
- Flash Lite requests used today: 337 of the 400 cap.
- Fix approved by Vighnesh (re-run tomorrow; submit fix only, no other tuning). Test first (failed), then `app/agent/llm.py`: a step offering one tool sets `tool_choice: "any"`. 182 tests pass. Live check: one call offering only `submit_findings` with a prompt asking to read a file first → model called `submit_findings` (1 request, made outside the Redis counter); case 04 re-run once (7 requests, found the bug; not recorded as a result). Flash Lite today: ~345 of 400.
