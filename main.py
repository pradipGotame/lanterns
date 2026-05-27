"""
Root-level ASGI entrypoint.

This keeps `uvicorn main:app` working when it is run from the repository root,
while the actual FastAPI application continues to live in `backend/main.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.main import app
