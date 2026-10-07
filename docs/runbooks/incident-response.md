# Runbook: Incident response

## Severity

| Level | Example |
| --- | --- |
| High | Leaked key, comments posted on the wrong repo, runaway spend |
| Medium | Worker down, queue backed up, repeated failed runs |
| Low | Single failed run, UI glitch |

## First 10 minutes

1. Stop the bleeding: pause new runs (set `DAILY_SPEND_LIMIT_USD=0` and restart the worker) or stop the worker.
2. Check `/health` and the worker heartbeat in Redis.
3. Check structured logs by run ID.
4. For a leaked secret, follow `rotate-secrets.md` now.

## Common cases

- **Runaway spend:** pause runs, check token logs, lower step and token caps, resume.
- **Comment flood:** confirm `MAX_COMMENTS_PER_PR` and the one-run-per-commit check; pause and investigate.
- **Webhook failures:** check the GitHub App's Advanced tab deliveries for status codes; 401 means a secret mismatch.
- **Queue backed up:** check the worker, then LLM provider errors and rate limits.

## After

Write a short note: what happened, impact, cause, fix, and the test or check added. Add a `CHANGELOG.md` entry if a fix shipped.
