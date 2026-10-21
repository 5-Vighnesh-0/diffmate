# Week 2 (from 2026-10-14)

## Day 4: 2026-10-17 (Phase 4)

**Done**
- Holdout run once on `gemini-3.5-flash-lite` (12 cases, 65 requests, $0): precision 100%, recall 30% (3 of 10), 0 false positives; both clean PRs got no comments.
- Checked the linter baseline's holdout hits against the data: 1 real (ruff B034, case 29), 1 coincidental (ESLint `no-explicit-any` within ±3 lines of case 08's bug). Corrected my first note in `docs/benchmark.md`, which had called both real. Matching rule left unchanged (changing it after seeing the holdout would be tuning on it).
- Bonus run on `gemini-3.8-flash` (its free limits: 20/day, 4/min): case 03 found (Flash Lite missed it), then Google's 429 stopped it cleanly at case 05. Resumes on later days.
- The throwaway test Postgres had gone after a Docker restart (19 integration tests skipped); restarted it, all 184 pass.
- Phase 4 report written; plan and changelog updated.

**Test output**
```
pytest → 184 passed · ruff → All checks passed!
```

**Files**
- added: `benchmark/results/holdout-gemini-3.5-flash-lite-2fe57354e31e.jsonl`, `benchmark/results/holdout-gemini-3.8-flash-2fe57354e31e.jsonl`, `reports/phases/phase-4-benchmark.md`, `reports/weekly/week-2.md`
- changed: `docs/benchmark.md`, `docs/PLAN.md`, `CHANGELOG.md`

**Decisions**
- Write the Phase 4 report now; add the 3.8 Flash bonus when it finishes (decided by: Vighnesh)

**Quota:** Flash Lite 65 of 400; 3.8 Flash at its free limit for today.

## Day 5: 2026-10-21 (Phase 4 gate, Phase 5 start)

**Decisions**
- Phase 4 approved; 30-55% recall accepted for v1; Phase 5 started (decided by: Vighnesh)

**Files**
- changed: `reports/phases/phase-4-benchmark.md` (status approved), `reports/weekly/week-2.md`
- Phase 5 opening answers: dashboard + core landing; no router library; self-hosted fonts; Vitest + Testing Library (decided by: Vighnesh). Pushback accepted: benchmark numbers bundled as JSON, no new API endpoint.
- Built the dashboard, review detail, and landing page; frontend tests in `make test` and CI. Stopped the Docker frontend container (it served the old placeholder on port 5173) to run the dev server; dev preview config in `../.claude/launch.json` (outside the repo, session root).
- Test output: backend 185 passed, frontend 4 passed, build clean. Details in `reports/phases/phase-5-frontend.md`.

**Files**
- added: `frontend/src/lib/router.tsx`, `frontend/src/components/ui/Shell.tsx`, `frontend/src/lib/benchmark.json`, `frontend/tests/unit/setup.ts`, `frontend/tests/unit/app.test.tsx`, `reports/phases/phase-5-frontend.md`
- changed: `frontend/src/{App.tsx,main.tsx,lib/api.ts,motion/tokens.ts,styles/tokens.css,routes/*.tsx}`, `frontend/{package.json,pnpm-lock.yaml,tsconfig.json,vite.config.ts,README.md}`, `benchmark/score.py`, `backend/tests/unit/test_benchmark.py`, `Makefile`, `.github/workflows/ci.yml`, `docs/{api.md,PLAN.md}`, `CHANGELOG.md`
- Deleted 15 empty placeholder files (approved by Vighnesh). Lighthouse (approved; one-off `npx lighthouse@12`, Playwright's Chromium): landing performance 95 / accessibility 100 after fixing the marker's ARIA role; dashboard 97 / 100.
- Vighnesh asked for scroll-craft on the frontend and dashboard. Pushback accepted: no paid image generation ($0), dashboard unchanged, method only. Interview answered; brief in `scrollcraft/builds/diffmate-landing/BRIEF.md`.
- Recorded four real reviews with `benchmark/demo.py` (15 free Flash Lite requests, all caught their bug). Rebuilt the landing as a live surface; fixed during browser checks: comment showing early, code line cut off, numbers colliding, phone menu wrapping. Lighthouse 96 / 100. Removed a leftover `vite preview` process I had left running on port 4173.
- Lint caught two over-long lines I had committed in `benchmark/score.py` earlier today (I had not run lint before that commit); fixed.
- Live dashboard check by Vighnesh (signed in with GitHub, voted): works. Feedback: confusing after sign-in, wants more animation. Added explanations, vote confirmation, GitHub link, "What next?", staggered rows/cards/steps, CSS page fade. Replaced an AnimatePresence "wait" page transition that left the old page on screen when animation frames were paused. Frontend tests 5 passed.
- Vighnesh: the sign-in screen did not say what happens or why to sign in. Built a proper sign-in screen: headline, one-line purpose, the button above the fold, "What happens next" in three steps, an accurate privacy note (token never stored, never posts as you, 8-hour session), and a real recorded review as the example. Install link pending: needs the App's public `github.com/apps/<name>` address from Vighnesh. Frontend tests 5 passed (signed-out test now checks the steps, privacy note, and example).
- Vighnesh: reviews should make sense to beginners and people without a computer-science background. Rewrote both dashboard pages in plain language: "How a review happens" (4 steps), a summary (reviews, notes, waiting), one plain-sentence card per review, "Words you will see" (pull request, review, note); on a review: "Mistake, serious. In calc.py, line 9. DiffMate is 92% sure.", plain reasons a note was not sent, the AI's steps in words. Caught one claim before shipping: a paused review does not resume by itself (worker.py), so the text says it finishes the next time the change is updated. Checked the signed-in layout in the built-in browser with sample data fed to the page (no real server). Frontend tests 6 passed.
- Vighnesh on the landing: "where is the data", and asked about graphs. Cause: the full-screen hook left the first screen mostly empty, so the content below looked missing. Fixed (code box on the first screen, line 1 pre-written, plain scroll instruction in the status line). Clarified there are no graphs anywhere; the numbers are the Numbers section (landing) and the counts at the top of the reviews list (dashboard). The line under the menu is the brutalist divider; offered to soften it.
- Phase 5 gate prepared: backend 185 passed, frontend 6 passed, ruff clean, pnpm audit clean, Lighthouse landing 94/100 and sign-in 96/100. Asked Vighnesh for approval and the Phase 6 opening questions.
- Phase 5 approved (Vighnesh). Phase 6 answers: no card for hosting; a small group of users; README with diagram and resume bullets (no demo video script).
- Phase 6 started. Hosting researched (2026-10-21): Render + Neon + uptime pinger chosen (Vighnesh). Plan in `docs/PLAN.md`. Task 1 done: the GitHub App key can come from a `GITHUB_APP_PRIVATE_KEY` secret or the key file; test added. Stopped here: usage limit reached.
- Phase 6 task 2: the API serves the built frontend (`FRONTEND_DIST`) for `/`, `/dashboard`, `/dashboard/runs/{id}` and `/assets`, with a page CSP (scripts, styles, fonts, images, API calls from self only; no inline, no eval); API responses keep `default-src 'none'`. Checked with the real build served from the API: landing, scroll review, plant-a-bug and sign-in work with zero CSP errors. The first run showed Vite inlining small fonts as data: URIs (blocked by the CSP); fixed with `assetsInlineLimit: 0` rather than loosening the CSP. Backend 195 passed, frontend 6 passed.
- Phase 6 task 3: one image (`backend/Dockerfile`, context = repo root) now also builds the frontend; root `.dockerignore` is an allow-list so `.env` can never enter the image (checked: 0 `.env` files in the built image; 48 frontend files; runs as uid diffmate). `backend/start.sh` runs migrations, the API and the worker, and exits if either stops. Local compose rebuilt on the new layout: `/health` ok, worker connected. `backend/.dockerignore` is now unused (deletion to be approved).
- Phase 6 task 4: `render.yaml` (free web service in Docker running `start.sh`, free Key Value with an empty IP allow-list and `noeviction`); secrets are `sync: false`; health check on `/` so Neon's free compute-hours are not spent on checks. `CLIENT_IP_HEADER` left at its default until the task-6 spoofing test (an empty value would be ignored by the settings anyway).
- Phase 6 task 7: full-history gitleaks before any push: 23 commits, no leaks; no `.env` or `.pem` tracked. Task 5: `docs/runbooks/deploy.md` has Vighnesh's steps (GitHub repo, Neon with the direct connection and `?ssl=require`, Render blueprint and secrets, GitHub App URLs, UptimeRobot on `/` not `/health`, making the App public, stopping the laptop copy).
- Pushed to https://github.com/5-Vighnesh-0/diffmate (public, branch `main`; Vighnesh ran the push after `gh auth login`). Before pushing, with Vighnesh's approval: an unrelated personal note was erased from the whole local history (`git filter-branch`, one line in this log; backup branch `backup-before-rewrite` kept locally, not pushed) and the branch renamed `master` to `main`. Verified GitHub's `main` equals local `main` and the note is absent. First CI: the empty placeholder `.github/workflows/bench.yml` failed as an invalid workflow; deleted it and the unused `backend/.dockerignore` (approved).
- First GitHub CI run: secrets, frontend, and backend tests/lint passed; `pip-audit` failed on certifi 2026.7.22 (PYSEC-2026-4320, fixed in 2026.10.19, released two days earlier). Upgraded the lockfile to certifi 2026.10.19 (security update of an existing indirect dependency, no new package): pip-audit clean, backend 195 passed.
- Pushed `9bd781d` and `1f9bedd` (approved). GitHub CI fully green: backend (pytest, ruff, pip-audit), frontend (build, tests, pnpm audit), secrets (gitleaks, full history). Closes the Phase 3 open item "CI audits green on GitHub".
- Render live at https://diffmate-kgzb.onrender.com (Vighnesh set up Neon and Render; secrets entered by him in Render). Checked: `/health` ok (Neon + Redis reachable, migrations ran), `/` and `/dashboard` serve the frontend with the page CSP, `/api/me` 401 signed out, unknown run path 404, HSTS present, login redirect_uri points at the Render address.
- Task 6, client IP on Render, tested live: 62 requests with a forged `CF-Connecting-IP` all got Cloudflare 403 "error code: 1000" (never reach the app); 62 normal requests got 60 × 401 then 2 × 429. So `CF-Connecting-IP` is set by Cloudflare and cannot be forged; the default `CLIENT_IP_HEADER` stays. Threat model row 4 and boundary 5 updated.
- Vighnesh set the GitHub App URLs to Render and an UptimeRobot monitor; stopped the laptop stack. UptimeRobot reported "down" while the site was up: it checks with HEAD, and the page routes only allowed GET (405). Page routes now answer HEAD; test added. Backend 195 passed, 1 skipped (Redis queue test; local Redis stopped, runs in CI).
- First hosted review: Vighnesh committed `percent(part, total)` (divides by `total` with no zero check) to playground PR #2 (commit 928e067, 16:45:18). Render posted review 5606001349 at 16:45:59 (41 s), laptop stack stopped. 2 comments, both correct: line 9 IndexError (`range(len(users) + 1)`), line 16 shell injection. Missed: the new `percent` divide-by-zero and the existing empty-list `average` crash, consistent with the measured recall (30-55%) and the earlier finding that Flash Lite misses divide-by-zero bugs. No false alarms.
