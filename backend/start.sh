#!/bin/bash
# Hosted (one container): migrate, then run the API and the review worker side by side.
# If either exits, the container exits and the host restarts it, instead of half-running.
set -e
alembic upgrade head
# --no-access-log: access lines would include query strings such as the one-time OAuth code.
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --no-access-log &
arq app.queue.worker.WorkerSettings &
wait -n
exit 1
