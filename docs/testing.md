# Testing

Status: proposed. Tools are confirmed during Phase 0.

## Layers

| Layer | Tool | What it covers |
| --- | --- | --- |
| Backend unit | pytest | Signature check, filters, dedupe, caps, schema validation |
| Backend integration | pytest with Postgres and Redis (docker) | Webhook to queue to worker, idempotency, retries |
| Agent | pytest with a fake LLM | Tool loop, step and token caps, invalid output handling |
| Security | pytest | Bad signature, replay, oversized body, planted injection PRs, IDOR, CSRF |
| Frontend unit | Vitest and Testing Library | Components, hooks, motion fallbacks |
| End to end | Playwright | Landing page scroll, dashboard flow, reduced motion |
| Benchmark | `make bench` | Quality, not correctness; see `benchmark.md` |

## Rules

- Tests first for backend logic, filters, guardrails, and the agent loop.
- Never call the real LLM or GitHub in unit tests; use fakes.
- A test must exist proving the agent cannot exceed its caps.
- Every item in `threat-model.md` with a test listed has that test.

## Commands

```bash
make test   # all tests
make lint   # ruff, ESLint, type checks
```

## CI gates

A PR cannot merge unless these pass: lint, type checks, backend tests, frontend tests, pip-audit, npm audit, gitleaks.

## Frontend checks

- Reduced-motion mode renders the stacked layout.
- Keyboard navigation works in the dashboard.
- Lighthouse performance 90 or higher on the landing page.
