"""
routers/files.py
================
FileUploader endpoints — upload, list, detail, delete.

All state is stored on disk via services.file_store so files survive
browser refreshes and server restarts.

Routes:
  POST   /api/files/upload          Upload a file + chunk it immediately
  GET    /api/files                 List all persisted files (optional ?category=)
  GET    /api/files/{file_id}       File metadata + all chunks
  DELETE /api/files/{file_id}       Remove file and its chunks
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from chunker import chunk_bytes, get_chunk_config
from config import FILES_ROOT
from models import UploadedFileDetail, UploadedFileMeta
from services.file_store import (
    add_entry,
    delete_chunks,
    load_chunks,
    load_meta,
    remove_entry,
    save_chunks,
    save_meta,
)
from services.live_reports import invalidate_live_reports

router = APIRouter(prefix="/api/files", tags=["FileUploader"])

ALLOWED_CATEGORIES = {"requirement", "test", "source"}


def _utc_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadedFileMeta)
async def upload_file(
    category: str = Form(...),
    file: UploadFile = File(...),
) -> UploadedFileMeta:
    """
    Upload a single file for a given category.
    File is saved to disk and chunked immediately with
    RecursiveCharacterTextSplitter.
    """
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"category must be one of {ALLOWED_CATEGORIES}",
        )

    content  = await file.read()
    file_id  = str(uuid.uuid4())
    cfg      = get_chunk_config(category)
    filename = file.filename or "file"

    # Save raw file
    raw_path = FILES_ROOT / f"{file_id}_{_safe_filename(filename)}"
    raw_path.write_bytes(content)

    # Chunk
    chunks = chunk_bytes(content, category, file_path=raw_path)
    save_chunks(file_id, chunks)

    # Persist metadata
    entry = {
        "id":            file_id,
        "name":          filename,
        "category":      category,
        "size_bytes":    len(content),
        "uploaded_at":   _utc_iso(),
        "chunk_count":   len(chunks),
        "chunk_size":    cfg["chunk_size"],
        "chunk_overlap": cfg["chunk_overlap"],
        "raw_path":      str(raw_path),
        "content_hash":  hashlib.sha256(content).hexdigest(),
    }
    add_entry(entry)
    invalidate_live_reports()

    print(f"[upload] {category}/{filename}  →  {len(chunks)} chunks  (id={file_id})")
    return UploadedFileMeta(**entry)


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[UploadedFileMeta])
async def list_files(category: Optional[str] = None) -> list[UploadedFileMeta]:
    """
    Return all persisted files, optionally filtered by ?category=.
    Called on every page load so the frontend restores state after refresh.
    """
    meta = load_meta()
    results = [
        UploadedFileMeta(**v)
        for v in meta.values()
        if category is None or v.get("category") == category
    ]
    results.sort(key=lambda f: f.uploaded_at)
    return results


# ── Detail ────────────────────────────────────────────────────────────────────

@router.get("/{file_id}", response_model=UploadedFileDetail)
async def get_file_detail(file_id: str) -> UploadedFileDetail:
    """Return file metadata + all its chunks."""
    meta = load_meta()
    if file_id not in meta:
        raise HTTPException(status_code=404, detail="File not found")
    chunks = load_chunks(file_id)
    return UploadedFileDetail(**meta[file_id], chunks=chunks)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{file_id}")
async def delete_file(file_id: str) -> dict:
    """Delete a file and its chunks from persistent storage."""
    entry = remove_entry(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    # Remove raw file from disk
    raw = Path(entry.get("raw_path", ""))
    raw.unlink(missing_ok=True)

    # Remove chunks
    delete_chunks(file_id)
    invalidate_live_reports()

    print(f"[delete] {entry['category']}/{entry['name']}  (id={file_id})")
    return {"success": True, "deleted_id": file_id}


# ── Rechunk ───────────────────────────────────────────────────────────────────

class RechunkRequest(BaseModel):
    categories: Optional[list[str]] = None  # None → all three categories


@router.post("/rechunk")
async def rechunk_files(body: RechunkRequest = None) -> dict:
    """
    Re-chunk every uploaded file (or a subset by category) using the current
    splitter config.

    For each file:
      1. Reads the original raw bytes from disk (raw_path stored at upload time).
      2. Runs chunk_bytes() with the category's current chunk_size / overlap.
      3. Overwrites the stored chunk JSON.
      4. Updates chunk_count / chunk_size / chunk_overlap in files_meta.json.

    Use this when:
      - The chunker config has changed.
      - A previous upload produced 0 or incorrect chunks.
      - You want to reset chunks before re-embedding.

    Returns a summary dict:
      {
        "rechunked": int,
        "skipped":   int,
        "errors":    [str, ...],
        "files":     [{"id", "name", "category", "chunk_count"}, ...]
      }
    """
    if body is None:
        body = RechunkRequest()

    target_cats = set(body.categories) if body.categories else ALLOWED_CATEGORIES

    meta    = load_meta()
    updated = dict(meta)   # work on a copy; commit at the end

    rechunked: list[dict] = []
    skipped   = 0
    errors:   list[str]  = []

    for file_id, entry in meta.items():
        cat = entry.get("category", "")
        if cat not in target_cats:
            skipped += 1
            continue

        raw_path = Path(entry.get("raw_path", ""))
        if not raw_path.exists():
            msg = f"{entry['name']}: raw file missing at {raw_path}"
            errors.append(msg)
            print(f"[rechunk] WARNING — {msg}")
            skipped += 1
            continue

        try:
            content = raw_path.read_bytes()
            chunks  = chunk_bytes(content, cat, file_path=raw_path)
            cfg     = get_chunk_config(cat)

            save_chunks(file_id, chunks)

            # Update metadata in-place
            updated[file_id] = {
                **entry,
                "chunk_count":   len(chunks),
                "chunk_size":    cfg["chunk_size"],
                "chunk_overlap": cfg["chunk_overlap"],
            }

            rechunked.append({
                "id":          file_id,
                "name":        entry["name"],
                "category":    cat,
                "chunk_count": len(chunks),
            })
            print(f"[rechunk] {cat}/{entry['name']}  →  {len(chunks)} chunks")

        except Exception as exc:
            msg = f"{entry['name']}: {exc}"
            errors.append(msg)
            print(f"[rechunk] ERROR — {msg}")
            skipped += 1

    save_meta(updated)
    if rechunked:
        invalidate_live_reports()

    return {
        "rechunked": len(rechunked),
        "skipped":   skipped,
        "errors":    errors,
        "files":     rechunked,
    }
