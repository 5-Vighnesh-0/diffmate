# Benchmark

Method and metrics: `../docs/benchmark.md`.

## Layout

```
cases/     real PRs with labels
seeded/    clean changes with injected, labeled bugs
runner.py  replays cases through the three setups
score.py   computes precision, recall, FP per PR, cost, latency
results/   output files with commit SHA, model, and date
```

## Case format (proposed)

Each case has a `case.json` with: name, source repo and license, base and head SHAs or a patch, split (`dev` or `holdout`), and labels (file, line range, category, is_real_bug).

## Rules

- Freeze cases and labels before tuning.
- Holdout is run once at the end.
- Record the license for every real case.
