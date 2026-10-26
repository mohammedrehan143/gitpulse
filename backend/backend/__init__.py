"""Bridge package so that 'from backend.src...' works when working directory is backend/."""

from __future__ import annotations

import os

# Point this package's search path to the parent directory (backend/)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
__path__ = [_BACKEND_DIR]
