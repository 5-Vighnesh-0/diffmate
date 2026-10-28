# Week 3 (from 2026-10-21)

## Day 6: 2026-10-27 (after v1: review fixes)

**Done**
- Independent code review (superpowers:requesting-code-review) rated v1 "with fixes". Vighnesh approved fixing findings #1, #3 and #5; the rest stay open.
- #1 Private repositories refused: the webhook returns 200 "ignored" unless the payload says `private: false`; the worker reads `base.repo.private` from the live PR and stops before any AI call. Two tests.
- #3 Resumed runs fixed (test first, it failed with `duplicate key ... trace_steps_run_id_step_no_key` and status "failed"): re-opening a run now deletes that run's old trace steps and findings (votes on them cascade). The crash-reclaim test now also checks the final status is "done"; new paused-then-resumed test.
- #5 `/health`: no Postgres probe (it woke Neon and used free compute hours for anyone who called it), rate limit 30/min per IP. Render and UptimeRobot already use `/`.
- Claude Code no longer adds a "Co-Authored-By: Claude" line to commits, in every project (Vighnesh). Past commits unchanged.

**Files**
- changed: `backend/app/api/{webhooks.py,health.py}`, `backend/app/github/diff.py`, `backend/app/queue/worker.py`, `backend/app/main.py`, `backend/tests/{security/test_webhook.py,security/test_headers.py,unit/test_health.py,integration/test_pipeline.py}`, `docs/{api.md,threat-model.md,PLAN.md,adr/0004-free-hosting.md,runbooks/deploy.md}`, `README.md`, `CHANGELOG.md`
- added: `reports/weekly/week-3.md`

**Decisions**
- Fix #1, #3, #5 now; #2, #4, #6, #7, #8 later (decided by: Vighnesh).
- A payload without a `private` flag counts as private (safe default) (decided by: Claude, within the approved fix).
- No Claude co-author line on commits, all projects (decided by: Vighnesh).

**Tests / checks**
```
pytest → 201 passed (test Postgres and local Redis running) · ruff → All checks passed!
vitest → 6 passed (frontend unchanged)
```

**Blockers / open questions**
- None. Push approved by Vighnesh.

**History rewrite (approved by Vighnesh, force-pushed)**
- Removed the `Co-Authored-By: Claude` line from all 37 earlier commit messages (`git filter-branch --msg-filter`); file contents unchanged, every commit ID changed. Commit IDs quoted in `reports/` updated to the new ones. Old history kept locally as branch `backup-before-rewrite`.
- After the push: live `/health` ok and limited (30×200, then 429). CI tests green (201 backend, 6 frontend), but pip-audit failed on a new filelock advisory (CVE-2026-112907/112913/112940); bumped filelock 4.0.12 → 4.2.4 in `backend/uv.lock`; local audit clean, 201 passed.

**Landing page: scroll flow (later the same day)**
- Prototyped "how DiffMate works" in six rounds with Vighnesh (two-sided story, video player, then the scroll flow he picked); critiques from design-critique, scroll-craft and Impeccable (installed by Vighnesh; its detector run with his OK).
- Built it: `frontend/src/lib/flow.ts` (timeline: real total time, AI waiting squeezed, a hold at the catch), `frontend/src/components/ReviewFlow.tsx`; replaces the pinned review and "Break one line" in `Landing.tsx`.
- Slop detector on the built page (desktop and phone): only the cream background left, kept on purpose (decided by: Vighnesh, keep paper and Inter).
- Honesty: per-step AI times are spread evenly inside the recorded total; the page says so.
- Agent skills and design notes stay out of git (`.agents/`, `.claude/skills/`, `docs/superpowers/`); no new Markdown files pushed (decided by: Vighnesh).

```
vitest → 11 passed · pnpm build → ok · impeccable detect (1366x900, 390x844) → cream-palette only
```

**Learn from votes (step 1 of the roadmap)**
- `backend/app/db/votes.py` (the rule, one query), filter step `dropped_stricter`, worker looks up the repo's stricter categories, `GET /api/feedback/summary` adds `stricter`, migration `0003_findings_stricter` (approved by Vighnesh via the spec), dashboard list and run-page label.
```
pytest → 210 passed · ruff → All checks passed! · vitest → 11 passed · pnpm build → ok
```

**One-click fixes (step 2)**
- Optional `fix` on each finding (schema: at most 10 lines, no code fences), offered in the tool declaration and prompt; `format_comment` adds a GitHub suggestion block only at 95% confidence or more. Not stored, so no migration; measuring how many are committed is left for later.
```
pytest → 214 passed · ruff → All checks passed!
```

**Next**
- Push after approval. Then, in order: one-click fixes, talk back, better catch rate (benchmark), plant a bug for real.
