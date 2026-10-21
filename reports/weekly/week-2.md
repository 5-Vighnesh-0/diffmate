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
