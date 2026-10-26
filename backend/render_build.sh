#!/usr/bin/env bash
set -o errexit

echo "==> Python version: $(python --version)"
echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing backend dependencies..."
pip install -r requirements.txt

echo "==> Backend build complete!"
