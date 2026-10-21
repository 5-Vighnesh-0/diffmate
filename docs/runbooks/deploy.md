# Runbook: Deploy

Status: hosting chosen in Phase 6 (2026-10-21): Render (free) + Neon (free) + UptimeRobot (free). All $0, no card. Setup file: `render.yaml`.

## Install Docker and uv (local machine, Ubuntu)

Both are free. Docker needs sudo, so you run it yourself:

```bash
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER      # then log out and back in
docker compose version
```

uv (no sudo; installs into `~/.local/bin`):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Pre-deploy checklist

- [ ] CI green on the commit to deploy
- [ ] `.env` values set on the host (names in `.env.example`)
- [ ] Database backup taken
- [ ] Migrations reviewed
- [ ] `LLM_DAILY_REQUEST_CAP` set below the free-tier limit; Gemini key is from a project with no billing account

## Steps

1. Pull the release commit on the host.
2. `docker compose build`
3. Run migrations (`alembic upgrade head`).
4. `docker compose up -d`
5. Check `GET /health` returns ok.
6. Open a test PR on the demo repo; confirm a comment appears.
7. Update the GitHub App webhook URL if the domain changed.

## Network rules

Only the proxy (Caddy) is exposed. Postgres, Redis, and the worker stay on the private network. Worker egress goes only to the GitHub API and the LLM provider.

## Rollback

1. Check out the previous release commit.
2. Rebuild and `docker compose up -d`.
3. If a migration must be undone, run the matching `alembic downgrade` after checking for data loss.

## Deploy to Render, step by step

You do these steps yourself: they create accounts and handle secrets. Never paste a secret into chat or into a file in this repo. Each service below has a free plan that needs no card.

### 1. Put the code on GitHub

1. On GitHub, create a new repository named `diffmate` (no README, no .gitignore). Public is fine: the code has no secrets (full-history scan: no leaks).
2. Tell Claude the repository URL. Claude adds it as the remote and pushes only after you say yes.

### 2. Create the database (Neon)

1. Sign up at neon.com with your GitHub account.
2. Create a project named `diffmate` in region **AWS US West 2 (Oregon)** (same region as Render, so the two are close).
3. Open **Connect**, turn **connection pooling off** (DiffMate needs the direct connection), and copy the connection string.
4. Change it in two places, in a text editor, not in chat:
   - `postgresql://` becomes `postgresql+asyncpg://`
   - everything from `?` onwards becomes `?ssl=require`
5. Keep it for step 3. It contains the database password.

### 3. Create the server (Render)

1. Sign up at render.com with your GitHub account and let Render see the `diffmate` repository.
2. Click **New, Blueprint**, pick the repository. Render reads `render.yaml` and shows two services: `diffmate` (web, free) and `diffmate-redis` (Key Value, free).
3. Fill in the secrets it asks for:

   | Setting | Value |
   | --- | --- |
   | `DATABASE_URL` | the string from step 2 |
   | `PUBLIC_API_URL` and `FRONTEND_ORIGIN` | `https://diffmate.onrender.com` (if Render gives the service a different address, use that one for both) |
   | `GITHUB_WEBHOOK_SECRET` | the same value as in your `.env` |
   | `GITHUB_APP_ID` | the same value as in your `.env` |
   | `GITHUB_APP_PRIVATE_KEY` | the whole contents of `~/.config/diffmate/github-app.pem`, including the BEGIN and END lines |
   | `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET` | the same values as in your `.env` |
   | `GEMINI_API_KEY` | the same key as in your `.env` |

4. Click **Apply**. The first build takes several minutes. Wait until the service says **Live**.
5. Open `https://<your address>/health`. It should say `{"status":"ok"}`.

### 4. Point the GitHub App at the server

On GitHub: **Settings, Developer settings, GitHub Apps, DiffMate, Edit**:

- **Homepage URL:** `https://<your address>`
- **Callback URL:** `https://<your address>/auth/callback`
- **Webhook URL:** `https://<your address>/webhooks/github`

Save. From now on GitHub sends pull request events to Render, not to your laptop.

### 5. Keep it awake (UptimeRobot)

Render's free server sleeps after 15 minutes without visits and takes about a minute to wake, which is longer than GitHub waits. A free pinger visits every 5 minutes so it never sleeps.

1. Sign up at uptimerobot.com (free plan, personal non-commercial use).
2. Add an **HTTP(s)** monitor for `https://<your address>/` (the home page, **not** `/health`, which would keep the database awake and use up Neon's free hours), every 5 minutes.

### 6. Check it works

1. Open `https://<your address>`, then **Dashboard, Sign in with GitHub**.
2. Open or update a pull request in a repository where the App is installed. The review should appear on GitHub and in the dashboard within a few minutes.

### 7. Let others use it (when ready)

1. GitHub App settings, **Advanced, Make public**.
2. Send Claude the App's public page (`https://github.com/apps/<name>`) to add an install link to the site.
3. Tell users to install it on public repositories only: the free Gemini tier may use what it receives to improve Google's products (ADR 0003).

### 8. Stop the laptop copy

Once Render works, stop the local stack and the tunnel so two copies do not share one Gemini key: `docker compose stop`, and close the cloudflared window.

### What resets, and what does not

- Render may restart the free server at any time. Sessions, today's AI request counter and webhook replay keys live in the free Redis and reset; users sign in again. Reviews and votes live in Neon and are kept.
- Google's own free limit still applies, so a reset counter cannot cost money.
