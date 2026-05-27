"""
config.py
=========
Central place for all paths, constants, and environment variables.
Import from here — never hard-code paths in routers or services.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# ── Root dirs ────────────────────────────────────────────────────────────────

BACKEND_ROOT      = Path(__file__).parent
UPLOAD_ROOT       = BACKEND_ROOT / "uploads"          # project-scoped raw uploads
PROJECT_ROOT      = BACKEND_ROOT / "projects"          # phase1 ATU state
INDICES_ROOT      = BACKEND_ROOT / "indices"           # phase2 retrieval indices
TRACEABILITY_ROOT = BACKEND_ROOT / "traceability"      # phase3 reports
FILES_ROOT        = BACKEND_ROOT / "uploaded_files"    # flat file store (FileUploader)
CHUNKS_ROOT       = FILES_ROOT   / "chunks"            # per-file chunk JSONs
FILES_META        = FILES_ROOT   / "files_meta.json"   # persistent metadata index

# ── Ensure directories exist ─────────────────────────────────────────────────

for _d in (UPLOAD_ROOT, PROJECT_ROOT, INDICES_ROOT, TRACEABILITY_ROOT, FILES_ROOT, CHUNKS_ROOT):
    _d.mkdir(parents=True, exist_ok=True)

# ── Environment ──────────────────────────────────────────────────────────────

load_dotenv(BACKEND_ROOT / ".env")

import os as _os

EMBEDDING_MODEL = _os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL       = _os.environ.get("OPENAI_LLM_MODEL",       "gpt-5-mini")
