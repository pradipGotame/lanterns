"""
services/file_store.py
======================
All I/O for the flat file store used by the FileUploader feature.

Responsibilities:
  - Read / write files_meta.json  (metadata index)
  - Read / write per-file chunk JSONs
  - Nothing else — no FastAPI, no business logic
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from config import FILES_META, CHUNKS_ROOT


# ── Metadata index ────────────────────────────────────────────────────────────

def load_meta() -> dict[str, dict]:
    """Return the full metadata dict keyed by file_id."""
    if not FILES_META.exists():
        return {}
    try:
        return json.loads(FILES_META.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_meta(meta: dict[str, dict]) -> None:
    """Persist the metadata dict to disk atomically (write-then-rename)."""
    tmp = FILES_META.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(FILES_META)


def add_entry(entry: dict[str, Any]) -> None:
    """Insert or replace a single file entry in the index."""
    meta = load_meta()
    meta[entry["id"]] = entry
    save_meta(meta)


def remove_entry(file_id: str) -> Optional[dict[str, Any]]:
    """Remove a file entry from the index and return it (or None if missing)."""
    meta = load_meta()
    entry = meta.pop(file_id, None)
    if entry is not None:
        save_meta(meta)
    return entry


# ── Chunk store ───────────────────────────────────────────────────────────────

def _chunk_path(file_id: str) -> Path:
    return CHUNKS_ROOT / f"{file_id}.json"


def load_chunks(file_id: str) -> list[dict]:
    """Return the list of chunk dicts for a file, or [] if not found."""
    path = _chunk_path(file_id)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_chunks(file_id: str, chunks: list[dict]) -> None:
    """Persist chunk list to disk."""
    _chunk_path(file_id).write_text(
        json.dumps(chunks, ensure_ascii=False), encoding="utf-8"
    )


def delete_chunks(file_id: str) -> None:
    """Remove the chunk file for a given file_id (no-op if missing)."""
    _chunk_path(file_id).unlink(missing_ok=True)
