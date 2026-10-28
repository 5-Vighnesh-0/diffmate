# Build context: the repo root (see /.dockerignore, an allow-list that keeps .env out).

# ESLint bundle for linting TypeScript PR files (DiffMate's own config only).
FROM node:22-slim AS eslint
RUN corepack enable
WORKDIR /eslint
COPY backend/app/checks/eslint/package.json backend/app/checks/eslint/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prod

# The frontend, built to call the API on its own origin (served by the API when hosted).
FROM node:22-slim AS web
RUN corepack enable
WORKDIR /web
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/index.html frontend/vite.config.ts frontend/tsconfig.json ./
COPY frontend/src ./src
RUN VITE_API_URL="" pnpm build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv
COPY --from=node:22-slim /usr/local/bin/node /usr/local/bin/node

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/alembic.ini backend/start.sh ./
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY --from=eslint /eslint/node_modules ./app/checks/eslint/node_modules
COPY --from=web /web/dist ./frontend-dist
# The live demo plants the landing page's recorded examples (app/api/demo.py).
COPY frontend/src/lib/demo.json ./demo.json

RUN useradd --uid 1000 --create-home diffmate
USER diffmate
EXPOSE 8000
# Compose: API only (the worker is its own service). Hosted: start.sh runs both.
# Apply approved migrations, then serve.
# --no-access-log: access lines would include query strings such as the one-time OAuth code.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
