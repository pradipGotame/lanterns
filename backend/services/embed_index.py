"""
services/embed_index.py
=======================
Fingerprint store for incremental embedding (change detection).

Storage: backend/vector_store/embed_index.json
Schema:  { file_id: { content_hash, embedded_at, chunk_count } }

Purpose:
  Before re-embedding, compare each file's current content_hash (stored in
  files_meta.json at upload time) against the hash recorded here.  Only embed
  files that are new (no fingerprint) or modified (hash differs).  Remove
  fingerprints for files that have been deleted from the upload store.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import BACKEND_ROOT

# ── Path ──────────────────────────────────────────────────────────────────────

EMBED_INDEX_PATH: Path = BACKEND_ROOT / "vector_store" / "embed_index.json"


# ── I/O ───────────────────────────────────────────────────────────────────────

def load_index() -> dict:
    """Return the full fingerprint index dict (empty dict if file missing)."""
    if not EMBED_INDEX_PATH.exists():
        return {}
    try:
        return json.loads(EMBED_INDEX_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_index(idx: dict) -> None:
    """Persist the fingerprint index atomically (write-then-rename)."""
    EMBED_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = EMBED_INDEX_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(EMBED_INDEX_PATH)


# ── Fingerprint ops ───────────────────────────────────────────────────────────

def get_fingerprint(file_id: str) -> dict | None:
    """Return the stored fingerprint for *file_id*, or None if not recorded."""
    return load_index().get(file_id)


def set_fingerprint(file_id: str, content_hash: str, chunk_count: int) -> None:
    """Record (or update) the fingerprint for *file_id* after successful embedding."""
    idx = load_index()
    idx[file_id] = {
        "content_hash": content_hash,
        "embedded_at":  datetime.now(timezone.utc).isoformat(),
        "chunk_count":  chunk_count,
    }
    save_index(idx)


def remove_fingerprint(file_id: str) -> None:
    """Delete the fingerprint for *file_id* (no-op if absent)."""
    idx = load_index()
    if file_id in idx:
        del idx[file_id]
        save_index(idx)


# ── Diff computation ──────────────────────────────────────────────────────────

def compute_diff(
    meta: dict,
    *,
    scope_ids: list[str] | None = None,
) -> dict:
    """
    Compare upload-store metadata against the fingerprint index and return a
    categorised diff.

    Args:
        meta:      Full files_meta dict  { file_id: entry }.
        scope_ids: If given, limit comparison to these file_ids.
                   When None, also detects files deleted from the upload store.

    Returns:
        {
          "new":       [file_id, ...],   # in meta, no fingerprint
          "modified":  [file_id, ...],   # in meta + fingerprint, hash differs
          "deleted":   [file_id, ...],   # fingerprint exists, not in meta (full scan only)
          "unchanged": [file_id, ...],   # in meta + fingerprint, hash matches
        }
    """
    idx = load_index()

    new_ids:       list[str] = []
    modified_ids:  list[str] = []
    unchanged_ids: list[str] = []

    scope = {fid: entry for fid, entry in meta.items()
             if scope_ids is None or fid in scope_ids}

    for fid, entry in scope.items():
        current_hash = entry.get("content_hash", "")
        fp = idx.get(fid)
        if fp is None:
            new_ids.append(fid)
        elif fp.get("content_hash") != current_hash:
            modified_ids.append(fid)
        else:
            unchanged_ids.append(fid)

    # Deletions only detected on a full scan (no scope_ids filter)
    deleted_ids: list[str] = []
    if scope_ids is None:
        for fid in idx:
            if fid not in meta:
                deleted_ids.append(fid)

    return {
        "new":       new_ids,
        "modified":  modified_ids,
        "deleted":   deleted_ids,
        "unchanged": unchanged_ids,
    }
