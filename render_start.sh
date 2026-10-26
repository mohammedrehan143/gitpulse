#!/usr/bin/env bash
# Startup script for Render deployment
set -o errexit

export PYTHONPATH=".:$PYTHONPATH"
PORT="${PORT:-8000}"

echo "==> Starting GitPulse API on port ${PORT} with PYTHONPATH=${PYTHONPATH}..."
exec uvicorn --app-dir . main:app --host 0.0.0.0 --port "${PORT}"
