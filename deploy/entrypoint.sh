#!/bin/sh
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head || {
    echo "[entrypoint] alembic upgrade head failed — stamping current schema as head"
    alembic stamp head
}

echo "[entrypoint] Starting application..."
exec uvicorn app.presentation.main:app --host 0.0.0.0 --port 8000 --workers 1
