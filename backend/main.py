"""Entrypoint for Render if Root Directory is configured as backend."""

from __future__ import annotations

import os
import sys

# Ensure both backend directory and repository root are on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

for path in [CURRENT_DIR, PROJECT_ROOT]:
    if path not in sys.path:
        sys.path.insert(0, path)

from src.gitpulse.api.main import app, start  # noqa: E402

__all__ = ["app", "start"]

if __name__ == "__main__":
    start()
