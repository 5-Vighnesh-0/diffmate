# Runbook: Deploy

Status: template. Hosting is not chosen yet (Phase 6, free options only); fill in the host-specific steps once it is.

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
