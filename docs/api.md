# HTTP API

Status: proposed. Final shapes are settled during Phase 1 to 3.

Conventions: JSON bodies, UTC ISO 8601 timestamps, errors as `{"error": {"code": "...", "message": "..."}}`. Dashboard endpoints require a session cookie. State-changing dashboard endpoints require a CSRF token.

## Public

### `GET /health`

Returns `200 {"status": "ok"}` when the API can reach Postgres and Redis.

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
7. Missing PR fields: `400`.
8. Enqueue fails (Redis down): `503`, and the delivery ID is released so GitHub's redelivery works.
9. Otherwise one job per (repo, PR, head SHA) is queued: `202 {"status":"queued"}`. A second delivery for the same commit queues nothing.

## Auth

| Method and path | Purpose |
| --- | --- |
| `GET /auth/login` | Start login (method to be decided; GitHub OAuth recommended) |
| `GET /auth/callback` | Complete login, set session cookie |
| `POST /auth/logout` | End the session |
| `GET /api/me` | Current user and their installations |

## Dashboard (session required)

### `GET /api/runs`

Query: `repo`, `status`, `limit`, `cursor`. Returns runs for the user's installations only.

```json
{ "items": [{ "id": "run_1", "repo": "owner/name", "pr": 12, "commit_sha": "abc123", "status": "done", "findings": 3, "cost_usd": 0.04, "started_at": "..." }], "next_cursor": null }
```

### `GET /api/runs/{id}`

Run details with findings. `404` if the run is not in the user's installations.

### `GET /api/runs/{id}/trace`

Ordered trace steps: step number, tool, short summary, tokens. No file contents.

### `POST /api/findings/{id}/feedback`

Body: `{"verdict": "accept" | "reject"}`. Requires CSRF token. Returns `204`.

### `GET /api/benchmark/summary`

Latest benchmark metrics for the three setups. Feeds the landing page results section.

## Rate limits

Webhook and dashboard endpoints each have a per-IP limit; exact values are set in config and recorded here once chosen.
