#!/bin/sh
set -e

if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL is not set. Add your Neon URL in Render → Environment."
  exit 1
fi

if [ -z "$REDIS_URL" ]; then
  echo "ERROR: REDIS_URL is not set. Add your Upstash rediss:// URL in Render → Environment."
  exit 1
fi

if [ -z "$LLM_API_KEY" ]; then
  echo "ERROR: LLM_API_KEY is not set. Add your Groq API key in Render → Environment."
  exit 1
fi

echo "Validating environment..."
if ! python scripts/validate_env.py; then
  echo "ERROR: Fix DATABASE_URL / REDIS_URL in Render → Environment, then redeploy."
  exit 1
fi

echo "Running database migrations..."
attempt=1
max_attempts=5
while [ "$attempt" -le "$max_attempts" ]; do
  if alembic upgrade head; then
    break
  fi
  if [ "$attempt" -eq "$max_attempts" ]; then
    echo "ERROR: Database migration failed after $max_attempts attempts."
    echo "Check DATABASE_URL uses postgresql+asyncpg://user:password@host/db?ssl=require"
    echo "If your Neon password has @, #, /, or %, URL-encode it (@ → %40, # → %23)."
    exit 1
  fi
  echo "Migration attempt $attempt failed, retrying in 5s..."
  attempt=$((attempt + 1))
  sleep 5
done

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
