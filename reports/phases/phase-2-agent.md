# Phase 2: Agent

**Dates:** 2026-10-07 to (open)
**Status:** approved (2026-10-07) by Vighnesh; live re-check after the quota reset

## Goal

Linters + an AI agent with four read-only tools under hard caps, schema-validated findings, filtered to at most 5 inline review comments.

## Decisions (Vighnesh, 2026-10-07)

- One `COMMENT` review with up to 5 inline comments; linter output is only a hint for the agent; caps 8 steps / 60k tokens; on LLM failure or daily cap nothing is posted.
- Gemini free tier, `gemini-3.8-flash`, `store=False`; key verified with a free metadata call; daily cap 100 requests.
- Schema approved; first migration applied.

## What was built

- Alembic migration 0001 (the approved DDL, run statement by statement), SQLAlchemy models, session helpers.
- PR files + commentable lines (`parse_patch`), PR details, safe tarball checkout (50 MB cap, `filter="data"`).
- Tools: `read_file`, `search_repo`, `view_diff_hunk`, `list_related_tests` — confined to the checkout.
- Linters: ruff (`--isolated`, F/E9/B/S) and ESLint (bundled config, TS 6 API), empty env, 60 s timeout.
- Findings schema (`extra="forbid"`), filter (not in diff → low confidence → duplicates → severity/confidence → cap 5).
- Agent loop: step cap (last step can only submit), token cap (pre-call estimate), Redis daily cap, unknown tools refused, trace recorded.
- Guardrails: PR title/body/diff/lint wrapped in `<untrusted_pr_content>` (closing tag defused); comment text rendered as plain text (no links, images, HTML, mentions).
- Review posting with a hidden per-commit marker (no double posts on retry).
- Worker pipeline: claim run (DB unique PR+SHA, failed/paused runs re-open) → checkout → linters → agent → filter → post → save findings/trace → delete checkout.

## Acceptance checks (with output)

- [x] A test proves the caps hold (`tests/unit/test_loop.py`): 8 LLM calls max with the last offering only `submit_findings`; token total stays ≤ 60k; daily cap stops before any call.
- [x] Live: PR #2 on `diffmate-playground` (3 planted bugs) → one review, 3 inline comments, all 3 bugs found on the exact lines:

```
review 5-Vighnesh-0/diffmate-playground#2@cac62f5 done: 3 posted, stop=submitted, 86601 ms
line 5  bug      medium 0.80  average([]) → ZeroDivisionError
line 9  bug      high   1.00  range(len(users) + 1) → IndexError
line 16 security high   0.85  subprocess.run(shell=True) → shell injection
5 LLM requests · 5,421 in / 325 out tokens · est. $0.0053 at list price · paid $0
trace: view_diff_hunk → list_related_tests → search_repo ×2 → submit_findings
```

- [x] Independent review (subagent): 17 findings, 15 fixed test-first, 2 accepted/deferred (table below)
- [x] Fresh verification (2026-10-07 04:13 UTC):

```
make lint   → All checks passed! · 49 files formatted · ✓ built
pytest      → 122 passed (unit, security, integration on real Postgres 16 + Redis 7)
pip-audit / pnpm audit (frontend, ESLint bundle) → No known vulnerabilities found
gitleaks (staged) → no leaks found
```

- [ ] Live re-check of the post-review code: blocked until the Gemini daily quota resets (20/20 used). Both attempts reached Google and failed safely (nothing posted, run marked failed, retry path via close/reopen proven).

## Problems and fixes

- asyncpg rejects multi-statement SQL → the migration runs the approved DDL statement by statement (comments stripped first).
- typescript-eslint does not support TypeScript 7 → the ESLint bundle pins TypeScript 6 (frontend keeps 7).
- **Live review hung**: default Gemini "thinking" took ~55 s per tiny call (measured with a raw REST request); `thinking_level: low` took 4.2 s. Fix: thinking level `low` (configurable), 90 s timeout per LLM call, arq `job_timeout` 900 s, cancelled jobs recorded as `failed`. The stuck run from before the fix was marked failed in the dev DB.
- arq kept failed job IDs for 7 days, blocking retries → `keep_result` 60 s; the `runs` table now decides one review per commit.
- Redelivering the same webhook does not retry a failed review (the signature replay guard blocks identical bodies); a new commit or close/reopen does.

## Review findings (Phase 2 subagent) and actions

| # | Finding | Action |
| --- | --- | --- |
| 1 | Linter argv injection (`--format=x.ts` → ESLint loads PR code) | Fixed: `--` before paths; test with `--fix.py` |
| 2 | Tarball decompression bomb | Fixed: 200 MB extracted / 20k entries cap, extraction off the event loop |
| 3 | httpx logs URLs (possible codeload token) | Fixed: httpx logger at WARNING |
| 4 | `read_file` unbounded | Fixed: 1 MB file cap, 500-char lines, 20k-char output |
| 5 | Unbounded tool calls per step, blocking tools | Fixed: max 5 calls/step, tools in a thread, walk cap 20k files |
| 6 | Symlink loop crashes | Fixed in tools and linters |
| 7 | Crashed run stuck in "running" | Fixed: reclaimed after the job timeout |
| 8 | "Retry by redelivery" wrong | Docs fixed: retry via close/reopen or next push |
| 9 | Forged marker suppresses review | Fixed: only Bot reviews count |
| 10 | File names / tag variants outside untrusted block | Fixed: listing wrapped, tag regex case-insensitive |
| 11 | Tool output not marked untrusted; bare URLs auto-link | Fixed |
| 12 | Token estimate optimistic; thinking tokens uncounted | Fixed: chars/3, thought tokens counted |
| 13 | Gemini network errors retried as GitHub errors | Fixed: `LlmError` |
| 14 | Linter child not reaped | Fixed |
| 15 | Daily cap UTC vs Pacific reset | Accepted: cap is 80% of the limit |
| 16 | Not-in-diff findings not stored | Approved at the gate: migration 0002 adds `dropped_not_in_diff`; now stored |
| 17 | Only first 50 files listed | Fixed: pagination up to 300, then 50 reviewed |

## Free-tier limits found live

- `gemini-3.8-flash`: 5 RPM, 20 RPD (AI Studio). Debugging plus reviews used all 20; Google then returned 429/503. The SDK's own retries hid this as timeouts.
- Fixes: SDK retries only 500/502/503/504 (never 429); a 429 pauses the run (`paused_daily_cap`); calls spaced to 4 per minute; cap set to 16/day. Recorded in ADR 0003.

## Open questions for the gate

- Benchmark timeline: ~300 requests at 16/day ≈ 19 days.
- Add `dropped_not_in_diff` to the approved `findings.status` values (migration 0002)? Today those findings are filtered out but not stored.

## Gate decisions (Vighnesh, 2026-10-07)

- Phase 2 approved; one live re-check of the hardened code after Google's daily quota resets.
- Benchmark: main runs (all 3 setups, full set) on `gemini-3.5-flash-lite` (500 RPD); `gemini-3.8-flash` on the ~20% holdout as a stronger-model comparison. Results labelled by model.
- Schema: migration 0002 adds `dropped_not_in_diff` (applied to dev DB; 123 tests pass).
- DeepSeek asked about: its own API is paid after signup credits (breaks $0); free routes (OpenRouter ~50/day, NVIDIA credits) are below Flash Lite's 500/day. Kept Gemini; DeepSeek possible later as an extra comparison model.
