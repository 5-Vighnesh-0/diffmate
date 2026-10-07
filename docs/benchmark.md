# Benchmark

Status: method defined, no results yet. Every number below is a placeholder until the runner has been run.

## Goal

Measure whether DiffMate finds real bugs with few false alarms and low cost, compared with a linter-only baseline.

## Cases

- 60 to 100 pull requests.
- Two sources: real PRs from open-source repos (with a bug later fixed or reverted), and seeded PRs where a known bug is injected into a clean change.
- Each case has labels: file, line range, category, and whether it is a real bug.
- Python and TypeScript only.
- Case licensing: only use repos whose license allows it; record the source and license per case.

Repos for real cases are not chosen yet (open question).

## Splits

- Dev set: about 80%. Used for prompt and threshold tuning.
- Holdout set: about 20%. Run once, at the end, untouched.
- Freeze the case list and labels before any tuning (target: Oct 30).

## Setups

| Setup | Description |
| --- | --- |
| 1. Linter only | ruff and ESLint output turned into comments |
| 2. Agent only | Agent loop with tools, no filtering |
| 3. Agent plus filtering | Full DiffMate |

## Matching rule (proposed)

A posted finding counts as a true positive if it is in the labeled file, within 3 lines of the labeled range, and has a compatible category. The tolerance is a starting guess; settle it before freeze.

## Metrics

| Metric | Definition |
| --- | --- |
| Precision | True positives / findings posted |
| Recall | Labeled bugs found / labeled bugs |
| False positives per PR | Posted findings that match no label / PRs |
| Cost per PR | Mean token cost in USD |
| Latency | p50 and p95 seconds from job start to comments posted |

## Starting targets (guesses, revise after first run)

Precision 70% or higher, recall 60% or higher, at most 1 false positive per PR, cost 0.10 USD or less per PR, median latency 2 minutes or less.

## Results

| Setup | Precision | Recall | FP / PR | Cost / PR | p50 | p95 |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Linter only | not run | not run | not run | not run | not run | not run |
| 2. Agent only | not run | not run | not run | not run | not run | not run |
| 3. Agent + filtering | not run | not run | not run | not run | not run | not run |

Holdout result: not run.

## How to run

```bash
make bench          # runs all three setups on the dev set
make bench-holdout  # runs the holdout once; do not use for tuning
```

Results are written to `benchmark/results/` with the commit SHA, model, and date.

## Honesty rules

- Report all three setups, including where DiffMate loses.
- Never tune on the holdout.
- Resume numbers must come from a committed results file.
