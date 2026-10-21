# Phase 6: Ship

**Dates:** 2026-10-21
**Status:** awaiting approval

## Decisions (Vighnesh, 2026-10-21)

No card anywhere; a small group of users; README with diagram and resume bullets (no demo video script); hosting on Render + Neon + UptimeRobot (route A over a laptop + ngrok address); public GitHub repository; MIT license; erase an unrelated personal note from history before the first push; yes/no votes kept (no rating scale), with a visible "useful" score.

## What was built

- **Hosting** (`render.yaml`, ADR 0004): one Render free container runs migrations, the API, the review worker, and serves the built frontend from the same origin; Render free Key Value (empty IP allow-list); Neon free Postgres; UptimeRobot on `/`. Live at https://diffmate-kgzb.onrender.com.
- **Code for hosting:** the GitHub App key from a secret setting; the API serves the frontend with a strict page CSP (no inline, no eval, no data: fonts); one Docker image with an allow-list `.dockerignore` so `.env` cannot enter it; `start.sh`; pages answer HEAD for uptime monitors.
- **Useful score:** `GET /api/feedback/summary`; the reviews list shows "x% of your rated notes were useful" next to the benchmark score, and each vote reports the running total.
- **Repository:** pushed to https://github.com/5-Vighnesh-0/diffmate after a full-history secret scan; README rewritten (live link, results, diagram, honest limits); MIT license.
- **Docs:** deploy runbook with Vighnesh's steps, ADR 0004, threat model rows 4 and boundary 5 updated, API doc.

## Acceptance checks (with output)

```
GitHub CI           → backend (pytest, ruff, pip-audit) · frontend (build, tests, pnpm audit) · secrets (gitleaks) all green
backend tests       → 196 passed, 1 skipped locally (Redis queue test; local Redis stopped; runs in CI)
frontend tests      → 6 passed
hosted review       → playground PR #2, commit 928e067: review posted 41 s after the commit, laptop off
hosted dashboard    → Vighnesh signed in, voted, saw the useful score
spoofing test       → forged CF-Connecting-IP rejected by Cloudflare (error 1000); 60 requests/min then 429
Lighthouse (phone)  → landing 96 perf / 100 a11y · sign-in 97 / 100 (after the fix below; local production build)
Lighthouse (live)   → sign-in 98 / 100 / 96 best practices; landing desktop 100 / 100
```

Final acceptance criteria (`docs/PLAN.md`):
- [x] `docker compose up` starts every service and `/health` returns ok (and the hosted copy)
- [x] A PR gets at most 5 inline comments; median well under 2 minutes (41 s hosted)
- [x] Bad signature 401; replayed delivery ignored
- [x] Agent cannot exceed step and token caps (tests)
- [x] Planted prompt-injection PRs do not change behaviour (8/8)
- [x] One command runs the benchmark (60 PRs) for all three setups
- [x] Dashboard shows runs, traces, findings with working accept and reject
- [x] Landing page per its brief; reduced motion works; Lighthouse performance 90 or higher

## Resume bullets (from real numbers)

- Built and deployed a GitHub App that reviews pull requests with an LLM agent (Gemini function calling, 4 read-only tools, step, token and daily caps) and posts at most 5 inline comments; runs 24/7 on free tiers (Render, Neon) at $0.
- Built a 60-PR benchmark from 10 open-source projects with a resumable runner: on 12 held-out PRs, 100% precision, 0 false alarms per PR and 30% recall (linters alone: 10%); a benchmark-driven fix doubled tuning-set recall from 27% to 55%.
- Secured it end to end: HMAC-verified webhooks with replay protection, repo-scoped GitHub tokens, OAuth + PKCE login with CSRF tokens, per-user authorization, rate limits and a strict CSP; resisted 8 of 8 planted prompt-injection attacks.
- React/TypeScript frontend with a scroll-driven landing page and a plain-language dashboard (Lighthouse 94+ performance, 100 accessibility); 197 tests in GitHub Actions CI with pip-audit, pnpm audit and gitleaks.

The customized resume (one page, original layout, DiffMate first) is `~/Downloads/VighneshNairResume-DiffMate.pdf`, outside the repo; the original is unchanged.

## Problems and fixes

- **No first paint on phones (found by the live Lighthouse run).** Every page faded in from opacity 0, and content that starts invisible does not count as painted; Lighthouse's phone run reported NO_FCP on the landing, locally and live. Ruled out hosting (desktop 100/100, local build failed the same way) and the font build setting (failed without it too); disabling the fade gave 96. Fixed by sliding without fading. The Phase 5 gate run had passed only because the fade happened to start in time.
- **pip-audit on the first CI run:** certifi PYSEC-2026-4320, fixed by updating to 2026.10.19.
- **Empty `bench.yml` placeholder** showed as a failed workflow; deleted (approved), with the unused `backend/.dockerignore`.
- **UptimeRobot "down" while the site was up:** it checks with HEAD; pages answered only GET (405). Pages now answer HEAD.
- **Vite inlined small fonts as data: URIs**, which the page CSP blocks; fonts now ship as files rather than loosening the CSP.
- **Empty `CLIENT_IP_HEADER` would have been ignored** by the settings (empty values are skipped); left at the default and settled by the live spoofing test.
- **My mistakes:** a `pkill -f` matched its own command line and ended my shell (the server it targeted was already stopped); `/health` as a keep-alive target would have used up Neon's free hours (caught in planning, before deploy); I first claimed in the dashboard text that a paused review resumes on its own (checked the worker and corrected it before shipping).

## Not done

- The GitHub App is still private (`https://github.com/apps/diffmate-vighnesh` shows "private GitHub App"); making it public is Vighnesh's step, then an install link goes on the site.
- Not verified: a real phone; Lighthouse on the live landing at phone size after the fix (needs the fix deployed).
- The 3.8 Flash holdout bonus stayed at 1 of 12 cases.

## Open for the gate

- Push the fix (Render redeploys), then re-run Lighthouse on the live landing at phone size.
- Make the App public now, or keep it private until the install link is in place?
