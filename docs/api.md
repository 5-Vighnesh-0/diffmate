# HTTP API

Status: implemented (Phases 1–3).

Conventions: JSON bodies, UTC ISO 8601 timestamps, errors as `{"error": {"code": "...", "message": "..."}}`. Dashboard endpoints require a session cookie. State-changing dashboard endpoints require a CSRF token.

## Public

### `GET /health`

Returns `200 {"status": "ok"}` when the API can reach Redis, else `503`. It does not touch Postgres, so it cannot wake the free Neon database (migrations run before the API starts). Rate limit: 30 per minute per client IP.

### `POST /webhooks/github`

Receives GitHub App webhooks.

Required headers: `X-Hub-Signature-256`, `X-GitHub-Delivery`, `X-GitHub-Event`.

Behavior:

Checks run in this order (implemented in Phase 1):

1. Body over 1 MiB (`WEBHOOK_MAX_BODY_BYTES`), by Content-Length or while streaming: `413`.
2. Missing or invalid `X-Hub-Signature-256` (HMAC SHA-256, constant-time compare): `401`.
3. Missing `X-GitHub-Delivery`: `400`.
4. Delivery ID already seen in the last 7 days: `200 {"status":"duplicate"}`, no action. Only signed requests reach this check, so forged requests cannot burn IDs.
5. Body is not a JSON object: `400`.
6. Event is not `pull_request`, or action is not `opened`, `synchronize`, `reopened`, or `ready_for_review`: `200 {"status":"ignored"}`.
7. Missing PR fields, or a repository name or SHA outside the strict patterns: `400`.
8. Private repository (or no `private: false` in the payload): `200 {"status":"ignored"}`. The worker checks again with GitHub before reviewing.
9. Enqueue fails (Redis down): `503`, and the delivery ID is released so GitHub's redelivery works.
10. Otherwise one job per (repo, PR, head SHA) is queued: `202 {"status":"queued"}`. A second delivery for the same commit queues nothing.

Replies (talk back): a `pull_request_review_comment` event with action `created` is checked after step 5 instead of steps 6 to 10. It is ignored (`200`) unless it is a reply (`in_reply_to_id`), from a person (not a bot), in a public repository, by the PR's author or someone whose `author_association` is `OWNER`, `MEMBER`, or `COLLABORATOR`. Otherwise one `answer_reply` job per reply comment is queued (`202`). The worker answers only replies to DiffMate's own notes, at most 3 per note, within the daily AI cap: it stands by the note with a reason, or withdraws it (strikes it through) and records the replier's Not useful vote.

## Auth

| Method and path | Purpose |
| --- | --- |
| `GET /auth/login` | Redirect to GitHub with `state` (single use, 10 min) and PKCE S256 |
| `GET /auth/callback` | Check `state`, exchange the code with the verifier, read the user and their installations, set the session cookie (HttpOnly, Secure, SameSite=Lax, 8 h), redirect to the dashboard. Bad or reused `state`, or a failed exchange: `400` |
| `POST /auth/logout` | CSRF required. Ends the session: `204` |
| `GET /api/me` | `{"user": {"id", "login"}, "installations": [ids], "csrf_token", "llm": {"requests_today", "daily_cap"}}` |

## Dashboard (session required: `401` without one)

All reads are filtered by the session's installations. A row from another installation returns `404`, so its ID is not confirmed. Errors use `{"error": {"code", "message"}}`.

### `GET /api/runs`

Query: `limit` (1–100, default 20), `cursor` (the last `id` seen), `status`. Newest first, keyset pagination.

```json
{ "items": [{ "id": 2, "repo": "owner/name", "pr": 2, "title": "Add calc", "commit_sha": "cac62f5…", "status": "done", "error": null, "llm_requests": 5, "tokens_in": 5421, "tokens_out": 325, "est_cost_usd": 0.0053, "findings": 3, "created_at": "…", "started_at": "…", "finished_at": "…" }], "next_cursor": null }
```

`status` is one of `queued`, `running`, `done`, `failed`, `paused_daily_cap`. `est_cost_usd` is an estimate at list price; actual spend is $0.

### `GET /api/runs/{id}`

The run plus `findings`: `id, file, line, category, severity, confidence, explanation, status, my_verdict`. `explanation` is LLM text: clients must render it as plain text.

### `GET /api/runs/{id}/trace`

Ordered steps: `step_no, tool, summary, tokens_in, tokens_out, duration_ms`. Summaries hold tool names and arguments only, never file contents.

### `POST /api/findings/{id}/feedback`

Body `{"verdict": "accept" | "reject"}` (other values: `422`). Requires the `X-CSRF-Token` header (`403` otherwise). One vote per user, and a later vote replaces it. Returns `204`.

### `GET /api/feedback/summary`

The signed-in user's own votes, limited to repos they can access: `{"useful": n, "not_useful": m, "stricter": [...]}`. Shown as "x% of your rated notes were useful" on the reviews list and after each vote. `stricter` lists, for repos the user can access, each category where everyone's votes made DiffMate stricter: `{"repo", "category", "not_useful", "total"}` (at least 3 votes, at least 2 of 3 Not useful). Notes in those categories need 90% confidence instead of 70%; ones held back get status `dropped_stricter`.

### Benchmark numbers (no endpoint)

The landing page's results are bundled at build time from `frontend/src/lib/benchmark.json`, which `make bench-score` writes. They change only when the benchmark is re-run, so a live endpoint was dropped in Phase 5 (decided by: Vighnesh, 2026-10-21).

## Live demo (no login)

Off unless `DEMO_REPO` and `DEMO_TOKEN` are set; then a visitor can open a real pull request in that public sandbox repo with one of the landing page's recorded examples, and DiffMate (installed there) reviews it like any other.

| Method and path | Purpose |
| --- | --- |
| `GET /api/demo` | `{"enabled": bool}` |
| `POST /api/demo` | Body `{"example": "loop" \| "slice" \| "shell"}` and nothing else (`422` otherwise): visitors never send code or text. Closes demo PRs older than 30 minutes, then opens a new one: `201 {"pr", "url"}`. `404` when off; `429` past 3 a minute per visitor or `DEMO_DAILY_CAP` (10) a day in total. |
| `GET /api/demo/{pr}` | `{"reviewed", "url", "comments": [{"line", "body"}]}`, DiffMate's comments only; the page polls it every 5 s. |

## Rate limits

Per client IP and minute, counted in Redis: `/webhooks/*` 120, `/auth/*` and `/api/*` together 60. Over the limit: `429` with `Retry-After`. The client IP comes from `CF-Connecting-IP` (`CLIENT_IP_HEADER`), which is trusted because the API is reachable only through the tunnel or 127.0.0.1.

## Response headers

Every response carries `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and `Strict-Transport-Security`. CORS allows only `FRONTEND_ORIGIN`, with credentials.
