# Contributing

DiffMate is a solo portfolio project, but fixes and ideas are welcome.

## Setup

See the quickstart in `README.md`. Copy `.env.example` to `.env` and fill in your own values. Never commit `.env`.

## Workflow

1. Open an issue first for anything bigger than a small fix.
2. Branch from `main`: `feat/...`, `fix/...`, `docs/...`.
3. Write tests first for backend logic.
4. Run `make lint` and `make test`.
5. Open a PR using the template.

## Commit messages

Short imperative subject, for example `Add replay protection to webhook`. Body explains why.

## Code rules

- Follow `CLAUDE.md` rules; they apply to humans too.
- Keep scope minimal; no extra features or abstractions.
- No new dependency without a reason in the PR.
- Frontend follows `docs/DESIGN.md`; animate only transform and opacity.

## Security

Report vulnerabilities privately; see `SECURITY.md`.
