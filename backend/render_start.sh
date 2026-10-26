#!/usr/bin/env bash
set -o errexit

export PYTHONPATH=".:$PYTHONPATH"
PORT="${PORT:-8000}"

echo "==> Starting GitPulse Backend API on port ${PORT}..."
exec uvicorn --app-dir . main:app --host 0.0.0.0 --port "${PORT}"
