# Phase 4: Benchmark

**Dates:** 2026-10-07 to 2026-10-21
**Status:** approved (2026-10-21) by Vighnesh

**Gate decisions (Vighnesh, 2026-10-21):** Phase 4 approved; recall of 30-55% accepted for v1; 3.8 Flash bonus continues and is added when done; no extra code review; start Phase 5.

## Decisions (Vighnesh, 2026-10-07)

60 offline snapshot cases (35 seeded, 15 real bug fixes undone, 10 clean); 12 held out; a finding counts if it is in the labelled file within ±3 lines; subagents build, Claude verifies every label, Vighnesh spot-checks 5; Flash Lite for the main runs, 3.8 Flash on the holdout as a bonus. Later: fix the missing-submit problem and re-run the dev set with that fix only (2026-10-07); spot-check delegated to Claude (2026-10-07).

## What was built

- `benchmark/corpus.py`: loads and validates cases, builds GitHub-style diffs with stdlib `difflib` (autojunk off), fingerprints the case set (`2fe57354e31e`).
- `benchmark/score.py`: matching, precision, recall, false positives per PR, estimated cost, p50/p95; writes tables into `docs/benchmark.md` and the README between markers.
- `benchmark/runner.py` `bench` mode: one agent run scored three ways (linter only, agent only, agent + filter); appends one result per case; resumes after the daily cap; retries Google 503 errors (60 s, 120 s) then stops cleanly.
- `make bench`, `make bench-holdout`, `make bench-score`.
- 60 cases from httpx, flask, click, requests, fastapi, zod, ky, hono, trpc, vitest (all MIT, BSD or Apache; full licence texts in `benchmark/cases/THIRD_PARTY.md`).
- Agent fix found by the benchmark: a step offering one tool sets Gemini `tool_choice: "any"`, so the last step always submits (`app/agent/llm.py`).

## Results

Dev set (48 cases), `gemini-3.5-flash-lite`, run 2 (with the fix):

| Setup | Precision | Recall | FP / PR | Est. cost / PR | p50 | p95 |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Linter only | 17% | 2% | 0.10 | $0.0000 | 0.2 s | 2.4 s |
| 2. Agent only | 100% | 55% | 0.00 | $0.0037 | 38.6 s | 140.8 s |
| 3. Agent + filtering | 100% | 55% | 0.00 | $0.0037 | 38.6 s | 140.8 s |

Run 1 (before the fix): agent recall 27%, 10 of 48 runs ended at the step cap with no answer.

Holdout (12 cases, run once), `gemini-3.5-flash-lite`:

| Setup | Precision | Recall | FP / PR | Est. cost / PR | p50 | p95 |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Linter only | 67% | 20% | 0.08 | $0.0000 | 0.1 s | 1.4 s |
| 2. Agent only | 100% | 30% | 0.00 | $0.0030 | 29.9 s | 40.0 s |
| 3. Agent + filtering | 100% | 30% | 0.00 | $0.0030 | 29.9 s | 40.0 s |

Bonus, `gemini-3.8-flash` on the holdout: 1 of 12 cases so far (found the bug Flash Lite missed). Its free tier allows 20 requests a day; the runner resumes it on later days.

**Honest reading**
- Precision is 100% and false positives 0 on every run, including all 10 clean PRs.
- Recall is 55% on dev and 30% on holdout. The gap is partly that the fix was judged on the dev set and partly sample size (10 holdout bugs). Treat 30-55% as the range.
- Setups 2 and 3 are identical: the model posts few, confident findings, so the filter has nothing to remove. The filter's value is not shown by this benchmark.
- The linter's holdout recall is really 10%: one "hit" was an unrelated ESLint warning within the ±3-line window. The rule was not changed after seeing the holdout.
- p95 latency on dev includes Google 503 retry waits; most of each review is free-tier request spacing.
- Targets from `docs/benchmark.md`: precision ≥ 70% met; recall ≥ 60% not met; ≤ 1 FP per PR met; ≤ $0.10 per PR met (estimated, $0 actual); median ≤ 2 min met.

## Acceptance checks (with output)

```
pytest            → 184 passed (unit, security, integration on real Postgres + Redis)
ruff (app+bench)  → All checks passed! · 67 files already formatted
make bench        → dev, 48 cases, 307 requests, $0 (run 2)
make bench-holdout→ holdout, 12 cases, 65 requests, $0
```

- [x] Results table committed (`docs/benchmark.md`, `README.md`, `benchmark/results/`)
- [x] Reproducible with one command (`make bench`, resumable)
- [x] Holdout run once, after tuning
- [ ] 3.8 Flash bonus: 1 of 12 (continues on later days)

## Problems and fixes

- difflib's default autojunk misaligned 3 long files (case 03 showed an untouched class as deleted and re-added). Diffs now built without it; regression test pinned to case 03.
- 10 of 48 dev runs ended at the step cap with no answer: the last step offered only submit but did not require it. Fixed with `tool_choice: "any"`; recall 27% → 55%.
- Google 503 "high demand" crashed run 2 on its first case. The runner now retries and stops cleanly; an outer loop restarted it every 20 minutes.
- **My mistakes:** (1) I overwrote an empty placeholder `benchmark/score.py` without noticing it was tracked (nothing lost). (2) My progress watcher matched its own command line, and I told Vighnesh run 2 was progressing when it had crashed; Vighnesh asked and I found it. (3) In the holdout note I first credited the linter with two real catches; checking the data showed one was a coincidence, and I corrected it.
- Two subagents hit the Claude session limit after writing their cases and before reporting; their 24 cases were reviewed the same way as the others.
- The throwaway test Postgres container had gone after a Docker restart, so 19 integration tests skipped; restarted it and all 184 pass.

## Not done in this phase

- No independent code review of the benchmark code (earlier phases had one). It reads only local files and writes only to `benchmark/results/` and the two docs; offered at the gate.

## Open questions for the gate

- Approve Phase 4 with the 3.8 Flash bonus still running (results added when it finishes)?
- Accept recall below the 60% target for v1, or tune more on the dev set first (costs about one day of quota per try)?
- Phase 5 (frontend): ready to start?
