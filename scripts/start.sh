#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting ARQ worker in background..."
arq app.worker.WorkerSettings &
WORKER_PID=$!

cleanup() {
  echo "Shutting down..."
  kill "$WORKER_PID" 2>/dev/null || true
  wait "$WORKER_PID" 2>/dev/null || true
}
trap cleanup INT TERM

echo "Starting API server on port ${PORT:-8080}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
