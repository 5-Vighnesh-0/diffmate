## Objective
Build DiffMate end to end: an AI agent that reviews GitHub pull requests and posts inline comments. Deliver a FastAPI backend, a Postgres + Redis data layer, a benchmark harness, a React + TypeScript + Framer Motion frontend (landing page and dashboard), CI, and docs. Work in phases, and stop for my approval at every phase gate. This is a resume project, so measurable quality and security matter more than feature count.

## Context (carry forward)
- Sources of truth, read in this order before doing anything: `./DESIGN.md` (tokens, type, motion, transitions T1-T14) and `./docs/PRD.md` (requirements F1-F10, guardrails, evaluation plan, 5-week timeline). If either file is missing, tell me and stop.
- Stack decided: Python 3.12 + FastAPI, Redis job queue, Postgres, TypeScript + React (Vite) + Framer Motion, Docker, GitHub Actions.
- Still open (ask me, never guess): LLM provider and model, hosting, final product name (DiffMate is a working name), package managers, dashboard login method.
- Architecture: GitHub App webhook -> FastAPI (verify HMAC signature) -> Redis queue (one job per commit SHA) -> worker runs linters (ruff, ESLint), then an agent loop with tools (read file, search repo, view diff hunk, list related tests) under hard step and token caps -> structured findings (file, line, category, severity, confidence, explanation) -> filter (dedupe, confidence threshold, max 5 comments per PR) -> inline review comments on the PR. Postgres stores runs, findings, and trace metadata. The React app reads them through the API.
- v1 scope: review and comment only. Out of scope: auto-fixing code, multi-org management, fine-tuning, languages beyond Python and TypeScript.
- The benchmark (60-100 PRs, three setups: linter only, agent only, agent plus filtering) is never cut. Cut order for everything else is in DESIGN.md section 8.

## Ground rules (these override everything below)
1. **Ask, do not assume.** Whenever something is unclear, missing, or you want to know anything, ask me with AskUserQuestion: batched, multiple choice, recommended option first. Ask at the start of every phase and any time you are blocked.
2. **Use skills.** In Phase 0 list every skill available to you, then use every relevant one at the right moment. Before each, say "Using [skill] to [purpose]". Mapping, if present in this environment (names may differ):
   - Process: superpowers:writing-plans (Phase 0 plan), superpowers:test-driven-development (backend logic, filters, guardrails), superpowers:subagent-driven-development and superpowers:dispatching-parallel-agents (independent work such as benchmark vs frontend), superpowers:systematic-debugging and engineering:debug (failures), superpowers:verification-before-completion (before claiming any phase is done), superpowers:requesting-code-review and engineering:code-review (end of each phase).
   - Architecture, backend, database: engineering:system-design, engineering:architecture (write ADRs), data:sql-queries (Postgres schema and indexes).
   - Frontend and design: frontend-design, ui-ux-pro-max, design:design-system, design:accessibility-review, design:ux-copy.
   - Quality and ops: engineering:testing-strategy, engineering:deploy-checklist, engineering:documentation, engineering:incident-response (runbooks).
   - Results charts on the landing page: dataviz or data:create-viz.
3. **find-skills.** Use the find-skills skill to discover extra skills for every domain this project touches. Procedure:
   - If find-skills is missing, ask me before running `npx skills add vercel-labs/skills@find-skills -g -y`.
   - Search each domain with specific keywords: network (tls, reverse proxy, caddy, nginx, webhook, rate limiting, cors); front-end (react, vite, framer motion, tailwind, accessibility); back-end (fastapi, python, async, redis queue); database (postgres, sqlalchemy, alembic, migrations); authentication (oauth, github app, jwt, sessions); security (owasp, secrets, threat model, prompt injection, dependency audit, csp); LLM agents (agent evaluation, tool use); devops (docker, github actions, ci-cd, deploy); testing (pytest, vitest, playwright); docs (readme, adr, api docs).
   - Quality gate before recommending: prefer 1K+ installs, official or well-known sources, source repo with 100+ stars. Be cautious with anything under 100 installs.
   - Show me one table: skill, source, installs, what it adds, domain. Install nothing until I say yes to that specific skill. Installed skills run with full agent permissions.
   - Read each SKILL.md in full before using it. Never run a bundled script you have not read. Skip any skill that asks for credentials, downloads executables, or wants broad permissions.
   - If the search returns nothing or the network is blocked, say so plainly and continue with built-in skills. Never invent a skill name.
4. **Security first.** Never ask me to paste secrets, keys, or tokens into chat, and never write them into any file. Create `.env.example` with variable names only. I set real values myself.
5. **Minimal scope.** Build what DESIGN.md and the PRD require and nothing else. No extra features, abstractions, or files.

## Questions to ask me at the start (Phase 0, batched, 4 per call)
- Project directory path and name; should I run `git init`; will there be a remote?
- LLM provider and model; monthly spend cap for the benchmark and demo.
- Hosting target and domain (or "decide later").
- Do I already have a GitHub App registered? If not, give me step-by-step instructions for `docs/runbooks/github-app-setup.md`.
- Package managers: uv or pip/poetry; pnpm or npm.
- Dashboard login: GitHub OAuth (recommended) or no login for the demo.
- Queue library (RQ or arq), local webhook tunnel (smee.io or cloudflared), and default comment cap and confidence threshold.
- Which open-source repos supply benchmark PRs, and are their licenses OK to use?
- Anything else you need to know before starting.

## Directory structure (create in Phase 1, exactly this, after I confirm the path)
```
diffmate/
├── CLAUDE.md                 # project rules for the agent: stack, commands, stop conditions
├── README.md                 # overview, architecture diagram, quickstart, benchmark table
├── DESIGN.md                 # provided
├── Makefile                  # dev | test | lint | bench | up
├── docker-compose.yml        # postgres, redis, backend, worker, frontend
├── .env.example              # variable names only
├── .gitignore, .gitleaks.toml
├── .github/workflows/        # ci.yml (lint, test, audit, secret scan), bench.yml (manual)
├── docs/
│   ├── PRD.md, PLAN.md, threat-model.md, benchmark.md, api.md
│   ├── adr/                  # 0001-stack.md, ...
│   └── runbooks/             # github-app-setup.md, deploy.md, rotate-secrets.md
├── backend/
│   ├── pyproject.toml
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/              # webhooks.py runs.py findings.py auth.py health.py
│   │   ├── core/             # config.py security.py logging.py ratelimit.py
│   │   ├── db/               # models.py session.py
│   │   ├── github/           # app_auth.py client.py diff.py comments.py
│   │   ├── queue/            # jobs.py worker.py
│   │   ├── agent/            # loop.py tools.py prompts.py schemas.py guardrails.py budget.py filters.py
│   │   └── checks/           # linters.py
│   └── tests/                # unit/ integration/ security/
├── benchmark/
│   ├── cases/                # PR fixtures and labels
│   ├── seeded/               # bug-injection scripts and labels
│   ├── runner.py, score.py
│   └── results/              # json and summary.md
├── frontend/
│   ├── package.json, vite.config.ts, tsconfig.json, index.html
│   ├── src/
│   │   ├── main.tsx, App.tsx
│   │   ├── routes/           # Landing.tsx Dashboard.tsx RunDetail.tsx Login.tsx
│   │   ├── scenes/           # Hero/ Pipeline/ Findings/ Results/ Closing/
│   │   ├── motion/           # tokens.ts, transitions/ (T1-T14), useReducedMotion.ts
│   │   ├── components/       # ui/ trace/ diff/
│   │   ├── lib/              # api.ts auth.ts
│   │   └── styles/           # tokens.css fonts.css
│   └── tests/                # unit/ e2e/
└── infra/
    ├── caddy/Caddyfile
    └── deploy/               # host-specific, decided with me
```

## Domain requirements

**Network**
- HTTPS only in deployment: TLS at a Caddy reverse proxy, HSTS on.
- CORS allowlist: the frontend origin only.
- Webhook endpoint: explicit body-size limit, request timeouts, and rate limiting.
- The worker's outbound traffic goes only to the GitHub API and the LLM provider.
- Local development uses a webhook tunnel (the one I choose).

**Authentication**
- GitHub App: sign a JWT, exchange it for a short-lived installation token. Minimum permissions only: Metadata read, Contents read, Pull requests write (comments).
- Dashboard login: the method I choose. If GitHub OAuth, use state and PKCE, with httpOnly, Secure, SameSite=Lax session cookies.
- CSRF protection on every state-changing endpoint (accept and reject buttons).
- Authorization: a user sees only runs for repositories in their own installations.

**Security**
- Verify `X-Hub-Signature-256` (HMAC SHA-256) with a constant-time compare. Reject bad signatures with 401. Ignore replayed `X-GitHub-Delivery` IDs.
- Prompt injection: PR title, description, code, and comments are untrusted data inside clearly labeled delimiters. The agent's tools are read-only, with no shell, network, or write tool. Findings must pass a strict schema before anything is posted. Write security tests with PRs that contain planted instructions.
- Never log secrets or full diffs. Store findings and trace metadata only, not full file contents.
- CI runs ruff security rules, pip-audit, npm audit, and gitleaks. Add security headers (CSP, X-Content-Type-Options, frame-ancestors).
- Write `docs/threat-model.md` (spoofed webhooks, token theft, prompt injection, cost abuse, data exposure).

**Database**
- Postgres with SQLAlchemy 2 and Alembic. Parameterized queries only.
- Propose the schema to me before the first migration (installations, repos, pull_requests, runs unique per PR and commit SHA, findings, trace_steps, feedback, benchmark cases and runs) with indexes and a retention note.

**Frontend**
- Follow DESIGN.md exactly: tokens, fonts (Anton, Inter, JetBrains Mono), scroll plan, transitions T1-T14.
- Animate only transform and opacity. Wrap the app in MotionConfig with reducedMotion "user", and give a stacked no-motion layout for reduced-motion users.
- Mobile: tilt effect off, 12 bars instead of 24.

## Phases and gates
Think carefully before starting each phase. At each gate: stop, summarize in 10 lines or fewer, show test output, ask your next-phase questions, and wait for my approval.

- **Phase 0, Discovery:** read DESIGN.md and PRD, list skills, run the find-skills procedure, ask the opening questions, write `docs/PLAN.md` (writing-plans), `CLAUDE.md`, and `docs/adr/0001-stack.md`. Gate: I approve the plan.
- **Phase 1, Foundations (week 1):** scaffold the directory, docker-compose, env handling, CI skeleton, health endpoint, webhook endpoint with signature verification and replay protection, queue and worker with one run per commit, post a test comment on a test PR. Gate: webhook tests pass and the test comment appears.
- **Phase 2, Agent (week 2):** linters, agent loop, four tools, structured findings, step and token caps, budget tracking, inline comment posting. Gate: a real PR gets at most 5 sensible comments.
- **Phase 3, Guardrails, auth, security (week 3):** confidence filter and dedupe, injection defenses and tests, GitHub App auth hardening, dashboard login, rate limits, security headers, threat model. Gate: security test suite and CI audits are green.
- **Phase 4, Benchmark (week 4):** build 60-100 cases (real bugs plus seeded bugs), freeze the set before tuning, hold out about 20%, one-command runner, score precision, recall, false positives per PR, cost per PR, and p50/p95 latency for the three setups. Gate: results table in `docs/benchmark.md`.
- **Phase 5, Frontend (week 5):** landing page scenes and transitions, dashboard (runs, step-by-step trace, findings with accept/reject), results section fed by real benchmark numbers. Gate: Lighthouse performance 90+, reduced motion verified.
- **Phase 6, Ship:** README with architecture diagram and benchmark table, deploy, demo video script, final skills-driven review (code review, accessibility review, deploy checklist). Gate: acceptance criteria below all pass.

## Scope
- Work only inside the project directory I give you.
- Do NOT touch: anything outside it, `~/.ssh`, global git config, other repositories, any real `.env` file.

## Constraints
- Do not add any dependency without asking. Propose a list in Phase 0 for one approval.
- Only make changes directly required by DESIGN.md and the PRD. No extra features, files, or abstractions.
- Explain things in plain, short language.

## Acceptance Criteria
- [ ] `docker compose up` starts every service and `/health` returns ok
- [ ] Opening or updating a PR produces at most 5 inline comments, median time under 2 minutes
- [ ] A webhook with a bad signature gets 401; a replayed delivery ID is ignored
- [ ] A test proves the agent cannot exceed its step and token caps
- [ ] Planted prompt-injection PRs do not change the agent's behavior
- [ ] One command runs the benchmark (60+ PRs) and reports all metrics for all three setups
- [ ] Dashboard shows runs, traces, and findings with working accept/reject
- [ ] Landing page matches DESIGN.md; reduced motion works; Lighthouse performance 90+
- [ ] CI is green: lint, tests, pip-audit, npm audit, gitleaks
- [ ] README has an architecture diagram, quickstart, and benchmark table
- [ ] No secrets in the repo, logs, or chat

## Stop Conditions
Stop and ask before:
- Deleting any file
- Adding any dependency
- Installing any skill
- Any database schema or migration change
- Touching anything outside Scope
- Destructive commands (`rm -rf`, `git reset --hard`, force push, `docker system prune`)
- Pushing to a remote, creating a GitHub repo, deploying, or any action that costs money or uses paid API quota
- Handling any credential
Also stop and report if a phase's acceptance checks fail twice. When context passes about 50%, tell me and suggest `/compact`.

## Session Strategy
New session, started inside an empty project directory. Use subagents for benchmark corpus building, security review, and frontend motion work so intermediate output stays out of the main context.

## Progress
After each completed step: ✅ [what was done] — [file(s) affected]
