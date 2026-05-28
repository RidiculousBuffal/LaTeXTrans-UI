#!/usr/bin/env sh

set -eu

APP_PORT="${PORT:-8000}"
DISCOVERY_HUEY_ENABLED="${DISCOVERY_HUEY_ENABLED:-false}"
DISCOVERY_HUEY_WORKERS="${DISCOVERY_HUEY_WORKERS:-2}"
DISCOVERY_HUEY_WORKER_TYPE="${DISCOVERY_HUEY_WORKER_TYPE:-thread}"

consumer_pid=""
api_pid=""

cleanup() {
  if [ -n "$api_pid" ] && kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
  fi
  if [ -n "$consumer_pid" ] && kill -0 "$consumer_pid" 2>/dev/null; then
    kill "$consumer_pid" 2>/dev/null || true
  fi
}

trap cleanup INT TERM EXIT

if [ "$DISCOVERY_HUEY_ENABLED" = "true" ]; then
  echo "Starting discovery Huey consumer..."
  huey_consumer -w "$DISCOVERY_HUEY_WORKERS" -k "$DISCOVERY_HUEY_WORKER_TYPE" backend.app.workers.discovery_schedule.huey &
  consumer_pid="$!"
else
  echo "Discovery Huey consumer disabled."
fi

echo "Starting FastAPI server on port ${APP_PORT}..."
uvicorn backend.app.main:app --host 0.0.0.0 --port "$APP_PORT" &
api_pid="$!"

wait "$api_pid"
