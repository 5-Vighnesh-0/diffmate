# Threat Model

Status: reviewed against the code at the end of Phase 3 (2026-10-07), including an independent security review and its fixes. Method: STRIDE over each trust boundary; every control names the test that proves it. Test paths are under `backend/tests/` unless noted.

## Assets

- GitHub App private key and installation tokens
- Webhook secret, OAuth client secret
- Gemini API key and the free daily quota it controls (20 requests/day on `gemini-3.8-flash`)
- Repository code the agent reads
- Findings, traces, and feedback in Postgres
- Dashboard sessions

## Trust boundaries

1. GitHub → API (webhooks): untrusted until the HMAC signature is verified.
2. PR content → agent: always untrusted, including file names, code, tool output, and linter messages.
3. LLM output → GitHub comments and the dashboard: untrusted; schema-validated and rendered as text.
4. Browser → dashboard API: untrusted until a session exists; every row is authorized by installation.
5. Internet → server: on the laptop only through the cloudflared tunnel (every published port binds to 127.0.0.1); hosted, only through Render's HTTPS edge to one web service (Redis has an empty IP allow-list; Postgres on Neon needs TLS and a password).
6. Worker → internet: GitHub API, codeload, and the Gemini API only.

## Threats and controls

| # | Threat (STRIDE) | Control | Test |
| --- | --- | --- | --- |
| 1 | Forged webhook (S) | HMAC SHA-256, constant-time byte compare; 401 | `security/test_webhook.py`, `unit/test_signature.py` |
| 2 | Replayed webhook, including under a new delivery ID (S) | Replay key = the signature, 7-day TTL; only signed requests are recorded | `test_replayed_delivery_is_ignored`, `test_same_signed_body_with_a_new_delivery_id_is_ignored` |
| 3 | Oversized or chunked bodies (D) | 1 MiB limit while streaming; 413 | `test_oversized_body_gets_413`, `test_oversized_chunked_body_without_length_gets_413` |
| 4 | Request floods (D) | Redis rate limit per client IP: webhook 120/min, dashboard 60/min, `/health` 30/min; 429 + Retry-After; counter keys always carry a TTL. Client IP from `CF-Connecting-IP`, set by Cloudflare (laptop tunnel, and in front of Render); on Render a client-sent value is rejected by Cloudflare (error 1000), tested live 2026-10-21 | `security/test_headers.py` (incl. Retry-After and TTL) |
| 5 | Payload fields steering GitHub API paths (T) | Repo name and SHA must match strict patterns; 400 | `test_suspicious_repo_or_sha_gets_400_and_no_job` |
| 6 | Prompt injection in title, body, diff, file names, code, tool output (T, E) | Everything PR-derived is wrapped in `<untrusted_pr_content>`, delimiter look-alikes in any case are defused; system prompt says it is data | `unit/test_loop.py` (markers, tag variants, file names, tool output); live suite `benchmark/injection/` (8/8 pass on Flash Lite, 2026-10-07) |
| 7 | An injected model trying to act (E) | Only 4 read-only tools + `submit_findings`; unknown tools refused; max 5 calls per step; findings schema with `extra="forbid"`; diff-line filter; cap 5; reviews are `COMMENT` only | `integration/test_injection_pipeline.py`, `unit/test_tools.py`, `unit/test_filters.py` |
| 8 | Agent reading outside the checkout (I) | Paths resolved and confined; symlinks out and symlink loops refused; tarball `filter="data"` | `test_paths_outside_the_checkout_are_refused`, `test_symlink_loops_are_errors_not_crashes`, `test_checkout_refuses_members_escaping_the_folder` |
| 9 | Linter argument injection (a file named like `--format=x.ts` loading PR code) (E) | `--` before file paths; DiffMate's own configs (`--isolated`, `--no-config-lookup`, `--no-inline-config`); empty env; timeout | `test_files_named_like_options_are_linted_as_files_not_options` |
| 10 | Decompression bomb or huge repos (D) | 50 MB download, 200 MB extracted, 20k entries; 1 MB files; capped tool output; walk cap 20k files | `test_checkout_refuses_archives_that_expand_past_the_limit`, `test_read_file_*` |
| 11 | Free-quota exhaustion or cost abuse (D) | 8 steps, 60k tokens (thinking counted); per-model daily cap counted on Google's Pacific quota day (code default 0 = no calls; `.env` 16); requests spaced 15 s; 429 pauses the run; one review per commit; one review at a time; the benchmark runner shares the same Redis counters per model | `test_agent_never_*`, `test_daily_cap_counts_per_model_and_per_google_day`, `test_requests_are_spaced_to_the_per_minute_limit`, `test_provider_rate_limit_*` |
| 12 | Comment spam or double posting (D) | Max 5 comments; one run per PR + SHA (DB unique); hidden per-commit marker, honoured only on Bot reviews | `test_a_retry_never_posts_a_second_review_for_the_same_commit`, `test_a_marker_in_a_human_review_does_not_suppress_posting` |
| 13 | Malicious comment content: links, images, HTML, @-mentions (T) | Model text escaped to plain text; URLs defanged | `unit/test_comments.py` |
| 14 | Leaked GitHub App key, OAuth secret, or Gemini key (I) | Env or secret file only; each container gets only its own secrets; httpx URLs not logged; gitleaks in CI; `docs/runbooks/rotate-secrets.md` | `test_http_client_request_urls_are_not_logged`, gitleaks (CI) |
| 15 | Over-broad GitHub permissions or long-lived tokens (E) | App: Metadata read, Contents read, PRs write; installation tokens scoped to one repo, fetched per run | `test_installation_token_is_scoped_to_one_repo_and_minimum_permissions` |
| 16 | OAuth login CSRF or code interception (S) | Random `state` used once (Redis GETDEL, 10 min) and bound to the starting browser by an HttpOnly state cookie (path `/auth`); PKCE S256; failed exchange or GitHub error makes no session | `test_login_state_is_bound_to_the_browser_that_started_it`, `test_state_is_single_use`, `test_github_errors_during_login_give_a_clean_502` |
| 17 | Session theft (S) | Random 32-byte ID; HttpOnly, Secure, SameSite=Lax, 8 h; server-side store; GitHub user token never stored | `test_callback_creates_a_safe_session_and_stores_no_github_token` |
| 18 | CSRF on feedback and logout (T) | Session-bound token in `X-CSRF-Token`, constant-time compare; SameSite=Lax | `test_logout_needs_csrf_then_ends_the_session`, `test_feedback_requires_csrf_and_keeps_one_vote_per_user` |
| 19 | IDOR on runs, traces, findings (I) | Every query filtered by the session's installations **and** the repos GitHub says the user can access in them (org membership alone is not enough); others → 404 | `integration/test_authz.py` (incl. `test_a_repo_i_cannot_access_in_my_own_installation_is_hidden`) |
| 20 | XSS from LLM text in the dashboard (T) | API returns text; the UI renders text only (Phase 5); API CSP `default-src 'none'` | `test_my_run_detail_returns_findings_as_plain_data`, `test_security_headers_on_every_response` (UI test in Phase 5) |
| 21 | Cross-origin reads (I) | CORS allows only `FRONTEND_ORIGIN`, with credentials | `test_cors_allows_only_the_frontend_origin` |
| 22 | SQL injection (T) | SQLAlchemy only, no string-built SQL; ruff `S` rules | ruff in CI |
| 23 | Secrets or code in logs (I) | JSON logs with IDs only; no bodies or diffs; httpx at WARNING | `test_http_client_request_urls_are_not_logged`, log review |
| 24 | Supply chain (packages, Actions, skills) (T) | Lockfiles; pip-audit and pnpm audit; Actions pinned to SHAs; uv version pinned; skills installed after a quality gate | CI |
| 25 | Exposure through the tunnel (I) | Only the API port is tunnelled; Postgres, Redis, worker, and frontend are on 127.0.0.1 or the private network | Compose review |
| 26 | Private code sent to the free AI tier, which may learn from it (I) | Webhook ignores any repository not marked `private: false`; the worker re-checks the live PR before any AI call and stops if the repo is private | `test_private_repository_is_ignored_and_not_queued`, `test_a_private_repository_is_never_sent_to_the_ai` |
| 27 | Anyone keeping the free Neon database awake through `/health` (D) | `/health` checks Redis only, never Postgres; rate-limited | `test_health_checks_time_out_instead_of_hanging` (fails if Postgres is touched), `test_health_rate_limit_is_30_per_minute` |
| 28 | Votes steering what DiffMate posts (T) | Votes only raise the bar for one category in one repo (70% → 90% confidence), never silence it; only people with access to the repo can vote; it lowers again when later votes are useful | `test_a_stricter_category_needs_the_higher_bar`, `test_votes_count_only_for_their_own_repo_and_category`, `test_feedback_summary_lists_stricter_categories_only_for_my_repos` |
| 29 | A harmful fix offered as a one-click suggestion (T) | The author must click to commit it and the comment says to check it first; only on notes 95% sure; the fix is a code block (schema rejects code fences, so model text cannot render as markdown) and at most 10 lines | `test_a_fix_cannot_break_out_of_its_code_block_or_run_long`, `test_no_suggestion_when_the_note_is_not_sure_enough_or_has_no_fix` |

## Out of scope for v1

Compromised GitHub, Cloudflare, or Google; multi-tenant billing abuse; physical access.

## Residual risk

- Prompt injection cannot be fully removed. A model that obeys an injection can still only write up to 5 plain-text comments on changed lines; it cannot act, read outside the PR, or approve.
- The free tier lets Google use prompts to improve its products, so only public code is reviewed (ADR 0003; enforced since 2026-10-27, row 26).
- Images and compose services are pinned by tag, not digest (Actions are pinned by SHA). Revisit before deployment.
- Access lists come from GitHub at login and last for the session (8 h): a user removed from a repo keeps read access until the session ends.
- Request spacing is exact for one worker process (`max_jobs = 1`); scaling workers would need an atomic Redis limiter.
- All API errors use one shape with no internals; unhandled errors are logged server-side and returned as a generic 500.
