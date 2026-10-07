# Reports

A record of everything done on DiffMate. Specs and reference docs live in [`../docs/`](../docs/); this folder is the log of the work.

| Folder | One file per | Updated |
| --- | --- | --- |
| [`weekly/`](weekly/) | week (`week-N.md`), with a section per day | every working day |
| [`phases/`](phases/) | phase (`phase-N-name.md`) | at each phase gate, before asking for approval |

Weeks follow [`docs/PLAN.md`](../docs/PLAN.md): week 0 is Phase 0 (up to 2026-10-06), week 1 starts 2026-10-07.

## Rules

- Write the day's entry the same day. Never edit an old day except to fix a mistake, and say so.
- List every file created, changed, moved, or deleted.
- Record every decision and who made it.
- Paste real command and test output; do not summarize a failure as a pass.
- Never put secrets, tokens, or full diffs here.

## Daily entry template (inside `weekly/week-N.md`)

```markdown
## Day N: YYYY-MM-DD (Phase N)

**Done**
- ...

**Files**
- added / changed / moved / deleted: `path`

**Decisions**
- decision (decided by: name)

**Tests / checks**
- command and result

**Blockers / open questions**
- ...

**Next**
- ...
```

## Weekly summary (top of `weekly/week-N.md`)

```markdown
# Week N: YYYY-MM-DD to YYYY-MM-DD (Phase N)

**Goal:** ...
**Status:** in progress | done
**Summary:** filled in at the end of the week
```

## Phase report template (`phases/phase-N-name.md`)

```markdown
# Phase N: Name

**Dates:** start to end
**Status:** in progress | waiting for approval | approved (date)

## Goal
## What was built
## Acceptance checks (with output)
## Decisions and ADRs
## Problems and fixes
## Metrics (where relevant: tests, coverage, cost, latency)
## Open questions for next phase
```
