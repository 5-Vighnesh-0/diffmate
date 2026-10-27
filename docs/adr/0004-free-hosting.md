# ADR 0004: Free hosting without a card

**Status:** Accepted (2026-10-21)
**Date:** 2026-10-21
**Deciders:** Vighnesh

## Context

Until Phase 6, DiffMate ran on the laptop behind a cloudflared quick tunnel. Reviews stopped whenever the laptop slept, and the tunnel's address changed on every restart, breaking the GitHub App's webhook. Phase 6 needs it running all the time for a small group of users, under the $0 rule (ADR 0003) and with no card on file anywhere (Vighnesh's decision).

What the system needs: a web process (API and frontend), a background worker, Postgres, Redis, a stable HTTPS address, and inbound webhooks answered within GitHub's timeout (about 10 seconds).

Options checked on 2026-10-21:

| Option | Card? | Problem |
| --- | --- | --- |
| Hugging Face Spaces (Docker) | No | Docker Spaces now need a paid plan |
| Koyeb free instance | Yes | Card required; also scales to zero after 1 hour |
| Oracle Cloud Always Free | Yes | Card required for identity |
| Laptop + ngrok free static domain | No | Only works while the laptop is on |
| Render free web service + Neon | No | Sleeps after 15 minutes idle; free Postgres on Render expires after 30 days |

## Decision

- **Render free web service** runs one container: migrations, the API, the review worker, and the built frontend served from the same origin (`backend/start.sh`, `render.yaml`). Render's free tier has no background workers, so the worker runs beside uvicorn; if either exits, the container exits and Render restarts it.
- **Render free Key Value** for the queue, sessions, quota counters and replay keys, with an empty IP allow-list (no outside access).
- **Neon free Postgres** for runs, findings, traces and votes (does not expire; TLS required).
- **UptimeRobot free** checks `/` every 5 minutes, so the free server never reaches its 15-minute sleep and webhooks are never lost to a cold start.
- Health checks and the pinger use `/`, never `/health`, because `/health` used to touch the database (it no longer does, since 2026-10-27, but `/` stays the target) and Neon's free plan allows 100 compute-hours a month.
- Frontend and API share one origin, so the session cookie is first-party and no CORS is needed.
- Secrets are entered by Vighnesh in Render (`sync: false`), never in files.

## Consequences

- $0 and no card, with a fixed address: `https://diffmate-kgzb.onrender.com`. First hosted review: 41 seconds from commit to comment.
- Render may restart the free server at any time. Sessions, today's request counter and replay keys reset (users sign in again; Google's own limit still caps spend at $0). Reviews and votes in Neon are kept.
- The client IP for rate limits comes from `CF-Connecting-IP`, set by Cloudflare in front of Render; a forged value is rejected by Cloudflare (tested live, threat model row 4).
- Everything shares one free Gemini quota, so this suits a small group, not the public.
- UptimeRobot's free plan is for personal, non-commercial use, which fits a portfolio project.
- Moving hosts later means changing `render.yaml` and the deploy runbook; the image itself is host-neutral.
