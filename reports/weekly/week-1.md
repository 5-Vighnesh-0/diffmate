# Week 1 (from 2026-10-07)

The 2026-10-07 entries were written in `week-0.md` (Day 2) before this file existed; they stay there.

## Day 3: 2026-10-08 (Phase 4)

**Done**
- Run 1 moved to `benchmark/results/run-1/` (kept for comparison; the runner would otherwise have skipped every case as already done).
- Run 2 crashed on its first case: Google returned 503 "gemini-3.5-flash-lite is experiencing high demand". My progress watcher missed it (its process check matched its own command line), so I wrongly told Vighnesh it was progressing; Vighnesh asked and I found the crash.
- Fix (test first): the runner retries a case after a provider error (60 s, then 120 s) and stops cleanly with exit code 3 if it still fails, so `make bench` resumes later. Output is flushed so the log shows progress live.
- Run 2 completed through Google's flaky afternoon (several retries, one clean stop, one automatic restart 20 minutes later).

**Test output**
```
pytest → 184 passed · ruff → All checks passed!
```

**Results (dev set, 48 cases, gemini-3.5-flash-lite, 307 requests, $0)**
```
| 1. Linter only       | 17%  |  2% | 0.10 | $0.0000 |  0.2 s |   2.4 s |
| 2. Agent only        | 100% | 55% | 0.00 | $0.0037 | 38.6 s | 140.8 s |
| 3. Agent + filtering | 100% | 55% | 0.00 | $0.0037 | 38.6 s | 140.8 s |
```
- Versus run 1: recall 27% → 55%; precision 100% both; 0 step-cap endings (was 10); 11 cases newly found, 0 lost. One run each and the model is not deterministic, so some of the change may be variation. p95 includes the 503 retry waits.

**Files**
- moved: `benchmark/results/dev-…-2fe57354e31e.jsonl` → `benchmark/results/run-1/`
- added: `benchmark/results/dev-gemini-3.5-flash-lite-2fe57354e31e.jsonl` (run 2), `reports/weekly/week-1.md`
- changed: `benchmark/runner.py`, `backend/tests/unit/test_benchmark.py`, `docs/benchmark.md`, `README.md`

**Decisions**
- Re-run the dev set with the submit fix only (decided by: Vighnesh)
- Retry provider errors in the runner and keep retrying `make bench` every 20 min (up to 6 tries) instead of waiting for Vighnesh (decided by: Claude, within the approved re-run)

**Quota:** Flash Lite 347 of 400 today (307 in results; the rest went to calls that failed with 503 errors).
