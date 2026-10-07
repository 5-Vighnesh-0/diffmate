# Runbook: GitHub App setup (local dev)

Everything here is free. Never paste secrets into chat or commit them. Values go only into your local `.env`.

## 0. Prerequisites

- Docker and uv installed (see [deploy.md](deploy.md) → Install Docker).
- `cp .env.example .env`, then fill in `POSTGRES_*`, `DATABASE_URL`, `REDIS_URL`.

## 1. Create a public test repo

On GitHub, create a new **public** repo (e.g. `diffmate-playground`) with a README. DiffMate only reviews public code on the free-tier LLM (ADR 0003).

## 2. Start the stack and a tunnel

```bash
make up
curl -s localhost:8000/health        # expect {"status":"ok"}
cloudflared tunnel --url http://localhost:8000
```

cloudflared prints a `https://<random>.trycloudflare.com` URL. It changes every time you restart the tunnel, so update the App's webhook URL (step 3) when it does.

## 3. Register the GitHub App

1. GitHub → Settings → Developer settings → GitHub Apps → **New GitHub App**.
2. **Name:** e.g. `diffmate-<your-username>`. **Homepage URL:** your repo URL.
3. **Webhook:** active. **URL:** `<tunnel URL>/webhooks/github`.
4. **Webhook secret:** generate a long random string on your machine and put it straight into `.env` as `GITHUB_WEBHOOK_SECRET`. Paste the same value into GitHub.

   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

5. **Repository permissions** (nothing else):
   - Metadata: Read-only
   - Contents: Read-only
   - Pull requests: Read and write
6. **Subscribe to events:** Pull request.
7. **Where can this app be installed?** Only on this account.
8. Create the app. Copy the **App ID** into `.env` as `GITHUB_APP_ID`.
9. **Generate a private key**. Move the downloaded `.pem` **outside the repo** (e.g. `~/.config/diffmate/github-app.pem`), run `chmod 600` on it, and set `GITHUB_APP_PRIVATE_KEY_PATH` to its absolute path.
10. Left menu → **Install App** → install on the test repo only.

## 4. Restart and check

```bash
make up                               # picks up the new .env values
docker compose logs -f worker
```

1. In the test repo, create a branch, change a file, open a PR.
2. Within a few seconds the PR gets one comment: "DiffMate received commit `abc1234`. Automated review is not enabled yet."
3. App settings → **Advanced** → Recent deliveries: the delivery shows **202**.
4. Click **Redeliver** on the same delivery: it shows **200** (replay ignored) and no second comment appears.
5. Bad-signature check (from your machine):

   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/webhooks/github \
     -H "X-GitHub-Event: pull_request" -H "X-GitHub-Delivery: manual-1" \
     -H "X-Hub-Signature-256: sha256=0000" -d '{}'
   ```

   Expect `401`.

## Dashboard login (GitHub OAuth through the same App)

1. App settings → **General** → **Callback URL**: `http://localhost:8000/auth/callback` (local dev; the deployed URL is added in Phase 6). Leave "Request user authorization (OAuth) during installation" unticked.
2. Copy the **Client ID** into `.env` as `GITHUB_OAUTH_CLIENT_ID`.
3. **Generate a new client secret** and paste it straight into `.env` as `GITHUB_OAUTH_CLIENT_SECRET` (never into chat). If an old secret ever leaked, delete it there.
4. `make up`, then open `http://localhost:8000/auth/login`: GitHub asks you to authorize the App and sends you back to the dashboard.

Login uses state + PKCE (S256); the session is an 8-hour HttpOnly cookie; the GitHub user token is used once and never stored.

## If a secret leaks

Follow [rotate-secrets.md](rotate-secrets.md).
