"""
sync_project_index.py
=====================
Phase 2: builds the dense retrieval index from
Phase 1 ATUs saved at  projects/{project_id}/atus.json.

Steps
-----
1. Read Phase 1 PipelineResult from  projects/{project_id}/atus.json.
2. Delete any existing vectors for this project (idempotent re-run).
3. Embed all ATU texts in one batched OpenAI call.
4. Add embeddings + metadata to the shared VectorStore.
5. Return a summary dict matching the shape expected by pipeline.run_phase2().

Called synchronously from services/pipeline.run_phase2() which is itself
called from within a running FastAPI async handler.  All I/O here is
synchronous (embed_texts and store.add are sync); no event-loop interaction.
"""

from __future__ import annotations

import json
from pathlib import Path

from config import PROJECT_ROOT
from services.embedder import embed_texts
from services.vector_store import get_store


def sync_project_index(
    project_id: str,
    *,
    print_summary:   bool = True,
    run_smoke_tests: bool = False,
) -> dict:
    """
    Build or refresh the dense index for *project_id*.

    Reads Phase 1 ATU output, removes stale vectors for this project,
    embeds all ATUs, and inserts them into the shared VectorStore.

    Args:
        project_id:      Unique project identifier (matches Phase 1 output dir).
        print_summary:   If True, print a one-line summary to stdout.
        run_smoke_tests: Reserved for future smoke-test assertions; ignored now.

    Returns:
        {
            "embedding_counts": {active, embedded, reused, deleted},
            "file_counts":      {added, changed, unchanged, deleted},
        }
    """
    _empty = {
        "embedding_counts": {"active": 0, "embedded": 0, "reused": 0, "deleted": 0},
        "file_counts":      {"added": 0, "changed": 0, "unchanged": 0, "deleted": 0},
    }

    # ── 1. Load Phase 1 ATUs ──────────────────────────────────────────────────

    atu_path: Path = PROJECT_ROOT / project_id / "atus.json"
    if not atu_path.exists():
        if print_summary:
            print(f"[Phase2] {project_id}: atus.json not found — skipping")
        return _empty

    try:
        data = json.loads(atu_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        if print_summary:
            print(f"[Phase2] {project_id}: failed to read atus.json — {exc}")
        return _empty

    requirements: list[dict] = data.get("requirements", [])
    tests:        list[dict] = data.get("tests",        [])
    sources:      list[dict] = data.get("sources",      [])
    all_atus:     list[dict] = requirements + tests + sources

    if not all_atus:
        if print_summary:
            print(f"[Phase2] {project_id}: no ATUs found — nothing to index")
        return _empty

    # ── 2. Remove stale vectors for this project ──────────────────────────────

    store   = get_store()
    deleted = store.delete_project(project_id)

    # ── 3. Embed all ATU texts in one batched call ────────────────────────────

    texts:      list[str]         = [atu["text"] for atu in all_atus]
    embeddings: list[list[float]] = embed_texts(texts)

    # ── 4. Build metadata entries and insert ──────────────────────────────────

    meta_entries: list[dict] = [
        {
            # file_id must be unique per chunk; use project-scoped ATU id
            "file_id":     f"{project_id}::{atu['id']}",
            "file_name":   atu.get("source_file", ""),
            "category":    atu.get("category", ""),
            "chunk_index": idx,
            "text":        atu["text"],
            "chunk_size":  len(atu["text"]),
            # project_id stored in metadata so delete_project() can filter
            "project_id":  project_id,
            "atu_id":      atu["id"],
        }
        for idx, atu in enumerate(all_atus)
    ]

    added = store.add(embeddings, meta_entries)

    # ── 5. Build summary ──────────────────────────────────────────────────────

    by_cat:       dict[str, int] = {}
    source_files: set[str]       = set()
    for atu in all_atus:
        cat = atu.get("category", "unknown")
        by_cat[cat] = by_cat.get(cat, 0) + 1
        sf = atu.get("source_file", "")
        if sf:
            source_files.add(sf)

    if print_summary:
        print(
            f"[Phase2] {project_id}: indexed {added} ATUs "
            f"({by_cat}) from {len(source_files)} source files"
            + (f", removed {deleted} stale vectors" if deleted else "")
        )

    return {
        "embedding_counts": {
            "active":   added,
            "embedded": added,
            "reused":   0,
            "deleted":  deleted,
        },
        "file_counts": {
            "added":     len(source_files),
            "changed":   0,
            "unchanged": 0,
            "deleted":   0,
        },
        # Sorted list of source file names newly added to the index this run.
        # Used by the frontend to show "Embedded ✓" badges on new files only.
        "newly_embedded_files": sorted(source_files),
    }
