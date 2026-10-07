# Runbook: Rotate secrets

Rotate on a schedule and immediately after any suspected leak.

| Secret | Variable | How to rotate |
| --- | --- | --- |
| Webhook secret | `GITHUB_WEBHOOK_SECRET` | Change in the GitHub App settings, update host env, restart API |
| App private key | `GITHUB_APP_PRIVATE_KEY_PATH` | Generate a new key in GitHub, deploy the file, restart, then delete the old key in GitHub |
| OAuth client secret | `GITHUB_OAUTH_CLIENT_SECRET` | Regenerate in GitHub, update env, restart |
| LLM API key | `LLM_API_KEY` | Create a new key at the provider, update env, restart, revoke the old key |
| Session secret | `SESSION_SECRET` | Change and restart; all users are logged out |

## If a secret leaked in git

1. Rotate it first. Removing it from history is not enough.
2. Remove it from the repo history only after rotating.
3. Check provider logs for misuse.
4. Note it in `CHANGELOG.md` under Security without including the value.
