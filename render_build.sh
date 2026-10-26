#!/usr/bin/env bash
# Build script for Render deployment
set -o errexit

echo "==> Python version: $(python --version)"
echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "==> Installing package in editable mode..."
pip install -e .

echo "==> GitPulse build complete!"
