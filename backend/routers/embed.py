"""
routers/embed.py
================
Embedding & vector-search endpoints with incremental change detection.

Change-detection logic (per run):
  NEW       — file is in the upload store but has no fingerprint in embed_index.json
  MODIFIED  — file is in both stores but SHA-256 hash differs
  DELETED   — fingerprint exists but file was removed from the upload store (full scan)
  UNCHANGED — hash matches; skipped entirely

Routes:
  POST   /api/embed              Start an incremental embedding job
  GET    /api/embed/status       Job state + index stats + diff preview
  POST   /api/embed/search       Semantic similarity search
  DELETE /api/embed/{file_id}    Remove a file's vectors from the index
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from services.embed_index import (
    compute_diff,
    load_index,
    remove_fingerprint,
    save_index,
    set_fingerprint,
)
from services.embedder import embed_single, embed_texts
from services.live_reports import invalidate_live_reports
from services.file_store import load_chunks, load_meta
from services.vector_store import get_store

router = APIRouter(prefix="/api/embed", tags=["Embedding"])

# ── Job state ─────────────────────────────────────────────────────────────────

_job: dict = {
    "running":    False,
    "started_at": None,
    "finished_at": None,
    "phase":      None,          # "deleted" | "modified" | "new" | None
    "total":      0,
    "done":       0,
    "errors":     [],
    "last_file":  None,
    # diff summary (populated before & during the job)
    "diff": {
        "new":       0,
        "modified":  0,
        "deleted":   0,
        "unchanged": 0,
    },
}


# ── Models ────────────────────────────────────────────────────────────────────

class EmbedRequest(BaseModel):
    file_ids: Optional[list[str]] = Field(
        default=None,
        description="Specific file IDs to embed. Omit for a full incremental scan.",
    )


class SearchRequest(BaseModel):
    query:    str
    category: Optional[str] = None
    top_k:    int = Field(default=10, ge=1, le=100)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _embed_file(
    file_id: str,
    entry: dict,
    store,
    *,
    delete_first: bool = False,
) -> Optional[int]:
    """
    Embed a single file.  Returns chunk count on success, None on error.
    Raises no exceptions — errors are returned as None so the caller can log.
    """
    if delete_first:
        store.delete_file(file_id)

    chunks = load_chunks(file_id)
    if not chunks:
        print(f"[embed] {entry['name']}: no chunks — skipping")
        return 0

    texts = [c["text"] for c in chunks]
    print(f"[embed] {entry['name']}: embedding {len(texts)} chunks…")

    embeddings: list[list[float]] = await asyncio.get_event_loop().run_in_executor(
        None, embed_texts, texts
    )

    meta_entries = [
        {
            "file_id":     file_id,
            "file_name":   entry.get("name", ""),
            "category":    entry.get("category", ""),
            "chunk_index": chunk["index"],
            "text":        chunk["text"],
            "chunk_size":  entry.get("chunk_size", 0),
        }
        for chunk in chunks
    ]

    store.add(embeddings, meta_entries)
    print(f"[embed] {entry['name']}: {len(embeddings)} vectors added")
    return len(chunks)


# ── Background task ───────────────────────────────────────────────────────────

async def _embed_job(file_ids: Optional[list[str]]) -> None:
    global _job
    store = get_store()
    meta  = load_meta()

    # ── Compute diff ──────────────────────────────────────────────────────────
    diff = compute_diff(meta, scope_ids=file_ids)

    new_ids      = diff["new"]
    modified_ids = diff["modified"]
    deleted_ids  = diff["deleted"]
    unchanged    = diff["unchanged"]

    total_ops = len(new_ids) + len(modified_ids) + len(deleted_ids)

    _job.update(
        running=True,
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None,
        phase=None,
        total=total_ops,
        done=0,
        errors=[],
        last_file=None,
        diff={
            "new":       len(new_ids),
            "modified":  len(modified_ids),
            "deleted":   len(deleted_ids),
            "unchanged": len(unchanged),
        },
    )

    print(
        f"[embed] Diff — new={len(new_ids)} modified={len(modified_ids)} "
        f"deleted={len(deleted_ids)} unchanged={len(unchanged)}"
    )

    if total_ops == 0:
        print("[embed] Nothing to do — all files unchanged")
        _job.update(running=False, finished_at=datetime.now(timezone.utc).isoformat(), phase=None)
        return

    invalidate_live_reports()

    # ── Phase 1: remove deleted-file vectors ──────────────────────────────────
    if deleted_ids:
        _job["phase"] = "deleted"
        for file_id in deleted_ids:
            try:
                _job["last_file"] = file_id
                removed = store.delete_file(file_id)
                remove_fingerprint(file_id)
                print(f"[embed] Removed {removed} vectors for deleted file {file_id}")
            except Exception as exc:
                msg = f"(deleted) {file_id}: {exc}"
                print(f"[embed] ERROR — {msg}")
                _job["errors"].append(msg)
            _job["done"] += 1

    # ── Phase 2: re-embed modified files ─────────────────────────────────────
    if modified_ids:
        _job["phase"] = "modified"
        for file_id in modified_ids:
            entry = meta.get(file_id, {})
            _job["last_file"] = entry.get("name", file_id)
            try:
                chunk_count = await _embed_file(file_id, entry, store, delete_first=True)
                if chunk_count is not None and chunk_count > 0:
                    set_fingerprint(
                        file_id,
                        entry.get("content_hash", ""),
                        chunk_count,
                    )
            except Exception as exc:
                msg = f"(modified) {entry.get('name', file_id)}: {exc}"
                print(f"[embed] ERROR — {msg}")
                _job["errors"].append(msg)
            _job["done"] += 1

    # ── Phase 3: embed new files ──────────────────────────────────────────────
    if new_ids:
        _job["phase"] = "new"
        for file_id in new_ids:
            entry = meta.get(file_id, {})
            _job["last_file"] = entry.get("name", file_id)
            try:
                chunk_count = await _embed_file(file_id, entry, store, delete_first=False)
                if chunk_count is not None and chunk_count > 0:
                    set_fingerprint(
                        file_id,
                        entry.get("content_hash", ""),
                        chunk_count,
                    )
            except Exception as exc:
                msg = f"(new) {entry.get('name', file_id)}: {exc}"
                print(f"[embed] ERROR — {msg}")
                _job["errors"].append(msg)
            _job["done"] += 1

    # ── Done ──────────────────────────────────────────────────────────────────
    _job.update(
        running=False,
        finished_at=datetime.now(timezone.utc).isoformat(),
        phase=None,
        last_file=None,
    )
    stats = store.get_stats()
    print(f"[embed] Job done — {stats['total_vectors']} total vectors in store")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("")
async def start_embed(body: EmbedRequest, background_tasks: BackgroundTasks) -> dict:
    """
    Kick off an incremental embedding job.
    Only new and modified files are (re-)embedded; unchanged files are skipped.
    Returns immediately; poll /api/embed/status for progress.
    """
    if _job["running"]:
        raise HTTPException(status_code=409, detail="An embedding job is already running.")

    background_tasks.add_task(_embed_job, body.file_ids)
    return {
        "message":    "Embedding job started",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status")
async def embed_status() -> dict:
    """
    Return:
      - Current job state (including diff summary and phase)
      - Overall vector index stats
      - Per-file status (indexed flag + change classification)
      - Diff preview (computed live from current metadata vs fingerprint store)
    """
    store = get_store()
    meta  = load_meta()
    stats = store.get_stats()
    ei    = load_index()           # raw fingerprint index for per-file annotation

    # Live diff preview (always up-to-date, not just during a job)
    live_diff = compute_diff(meta)

    # Classify each file for the UI
    changed_new  = set(live_diff["new"])
    changed_mod  = set(live_diff["modified"])
    changed_del  = set(live_diff["deleted"])

    files_status = []
    for fid, entry in meta.items():
        if fid in changed_new:
            change = "new"
        elif fid in changed_mod:
            change = "modified"
        else:
            change = "unchanged"

        # A file is "indexed" if it has a fingerprint in embed_index.json.
        # Using the fingerprint store (ei) rather than in-memory raw_data avoids
        # false "Pending" labels when the server restarts and raw_data.pkl is slow
        # to hydrate or is temporarily out of sync with the persisted Chroma files.
        files_status.append({
            "id":       fid,
            "name":     entry.get("name"),
            "category": entry.get("category"),
            "indexed":  fid in ei,
            "change":   change,                       # "new" | "modified" | "unchanged"
        })

    return {
        "job":  dict(_job),
        "index": stats,
        "files": files_status,
        "diff_preview": {
            "new":       len(live_diff["new"]),
            "modified":  len(live_diff["modified"]),
            "deleted":   len(live_diff["deleted"]),
            "unchanged": len(live_diff["unchanged"]),
        },
    }


@router.post("/search")
async def semantic_search(body: SearchRequest) -> list[dict]:
    """
    Run a semantic similarity search against the vector store.
    Returns ranked chunks with score, text, file name and category.
    """
    store = get_store()

    if store.get_stats()["total_vectors"] == 0:
        raise HTTPException(status_code=404, detail="Index is empty. Run /api/embed first.")

    try:
        query_vec: list[float] = await asyncio.get_event_loop().run_in_executor(
            None, embed_single, body.query
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Embedding failed: {exc}")

    results = store.search(query_vec, top_k=body.top_k, category=body.category)
    return results


@router.delete("")
async def clear_index() -> dict:
    """
    Wipe the entire vector index and fingerprint store.
    Does NOT re-embed — all vectors are gone and files are treated as
    un-indexed until the next /api/embed run.
    Returns 409 if an embedding job is currently running.
    """
    if _job["running"]:
        raise HTTPException(status_code=409, detail="Cannot clear while an embedding job is running.")

    store   = get_store()
    removed = store.reset()
    save_index({})
    invalidate_live_reports()

    print(f"[embed] Index cleared — {removed} vectors removed")
    return {
        "success":         True,
        "vectors_removed": removed,
        "cleared_at":      datetime.now(timezone.utc).isoformat(),
    }


@router.post("/purge")
async def purge_and_rerun(background_tasks: BackgroundTasks) -> dict:
    """
    Wipe the entire vector index and fingerprint store, then immediately
    re-embed every file in the upload store from scratch.
    Returns 409 if a job is already running.
    """
    if _job["running"]:
        raise HTTPException(status_code=409, detail="An embedding job is already running.")

    store = get_store()
    removed = store.reset()          # clear vector store
    save_index({})                   # clear embed_index.json (all fingerprints)
    invalidate_live_reports()

    print(f"[embed] Purge — cleared {removed} vectors and all fingerprints")

    # Re-embed everything (scope_ids=None → full scan, all files treated as new)
    background_tasks.add_task(_embed_job, None)

    return {
        "message":       "Index purged and full re-embed started",
        "vectors_removed": removed,
        "started_at":    datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/{file_id}")
async def delete_file_vectors(file_id: str) -> dict:
    """Remove all vectors for a given file from the vector index."""
    if _job["running"]:
        raise HTTPException(status_code=409, detail="Cannot delete while embedding job is running.")

    store   = get_store()
    removed = store.delete_file(file_id)
    remove_fingerprint(file_id)

    if removed == 0:
        raise HTTPException(status_code=404, detail="No vectors found for this file.")

    invalidate_live_reports()

    print(f"[embed] Deleted {removed} vectors for file {file_id}")
    return {"success": True, "file_id": file_id, "vectors_removed": removed}
