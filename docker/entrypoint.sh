#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying database migrations..."
    alembic upgrade head
fi

WORKERS="${WEB_CONCURRENCY:-2}"
HOST="${APP_HOST:-0.0.0.0}"
PORT="${APP_PORT:-8000}"

exec uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --proxy-headers \
    --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}" \
    --no-access-log
