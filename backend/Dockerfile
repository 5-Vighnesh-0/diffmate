# ESLint bundle for linting TypeScript PR files (DiffMate's own config only).
FROM node:22-slim AS eslint
RUN corepack enable
WORKDIR /eslint
COPY app/checks/eslint/package.json app/checks/eslint/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prod

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv
COPY --from=node:22-slim /usr/local/bin/node /usr/local/bin/node

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY --from=eslint /eslint/node_modules ./app/checks/eslint/node_modules

RUN useradd --uid 1000 --create-home diffmate
USER diffmate
EXPOSE 8000
# Apply approved migrations, then serve.
# --no-access-log: access lines would include query strings such as the one-time OAuth code.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
