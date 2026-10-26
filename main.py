"""Root application entrypoint for Render and cloud deployments."""
from __future__ import annotations

import os
import sys

# Guarantee that the repository root is always in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.src.gitpulse.api.main import app, start  # noqa: E402

__all__ = ["app", "start"]

if __name__ == "__main__":
    start()
