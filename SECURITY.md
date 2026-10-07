# Security Policy

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private vulnerability reporting on this repository (Security tab, "Report a vulnerability").

Include what you found, steps to reproduce, and the impact. Never include real secrets.

This is a solo portfolio project, so response times are best effort.

## Scope

In scope: webhook handling, authentication and sessions, authorization, prompt injection, secret handling, and the dashboard.

Out of scope: denial-of-service by volume, social engineering, and third-party services.

## Design summary

- Webhook signatures verified on every request; replays ignored
- Read-only agent tools; PR content treated as untrusted
- Minimal GitHub App permissions
- Secrets only in environment variables, never logged

See `docs/threat-model.md` for details.
