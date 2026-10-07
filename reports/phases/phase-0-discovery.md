# Phase 0: Discovery

**Dates:** 2026-10-06 to 2026-10-06
**Status:** approved (2026-10-06)

## Goal

Read the specs, settle open decisions, choose skills and dependencies, and get `docs/PLAN.md` approved.

## What was built

- Project directory, scaffold, `git init`, docs set imported, `docs/` and `reports/` split ([week 0, day 1](../weekly/week-0.md))
- `docs/PLAN.md` with decisions, $0 constraints, dependency proposal, benchmark repo shortlist
- ADR 0001 (stack, updated) and ADR 0003 (free-tier LLM and the $0 rule)
- `CLAUDE.md` and `docs/RULES.md` updated with the $0 rule
- 15 vetted skills installed, plus find-skills

## Acceptance checks (with output)

- [x] `docs/DESIGN.md` and `docs/PRD.md` read
- [x] Skills listed; find-skills run across 32 domain queries; vetted skills installed (user gave blanket install permission)
- [x] Opening questions answered (5 batches)
- [x] Dependency list approved (2026-10-06)
- [x] `docs/PLAN.md`, `CLAUDE.md`, `docs/adr/0001-stack.md` updated
- [x] Plan approved (2026-10-06)

No code or tests exist yet, so there is no test output for this phase.

## Decisions and ADRs

- See `docs/PLAN.md` → Decisions. ADR 0001 (stack), ADR 0003 (Gemini free tier, $0 enforced).

## Problems and fixes

- First PRD copy was a PDF-to-text conversion with broken tables. It was replaced by the Markdown PRD from the zip.
- First LLM pick (Claude Opus 5.5) conflicted with the user's $0 budget. Switched to the Gemini free tier after checking the options (ADR 0003).
- The `skills` CLI reports "PromptScript does not support global install" on every install. That target is a different agent tool; the Claude Code install succeeded each time.

## Metrics

- Spend so far: $0.

## Open questions for Phase 1

- Docker and uv installed? (Needed for `docker compose up` and `uv sync`.)
- Which GitHub repo should hold the test PR for the first comment? (A new public repo of yours is simplest.)
