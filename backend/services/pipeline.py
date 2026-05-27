"""
services/pipeline.py
====================
Thin wrapper around the three pipeline phases.

Each phase is called in a "best-effort" manner:
  - If a phase succeeds, its summary dict is returned.
  - If it raises or exits, success=False is returned and the server keeps running.

This is the only place in the codebase that touches Phase 1/2/3.
Routers should call these helpers, not the phase modules directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from preprocessor import Phase1Pipeline, PipelineResult
from scripts.run_reasoning_audit import run_reasoning_audit
from scripts.sync_project_index import sync_project_index

_pipeline = Phase1Pipeline()


def run_phase1(*, project_id: str, project_dir: Path) -> PipelineResult:
    """Run Phase 1 ATU extraction.  Always returns a PipelineResult."""
    return _pipeline.run_from_saved_files(
        project_id=project_id,
        project_dir=project_dir,
    )


def run_phase2(project_id: str) -> dict[str, Any]:
    """
    Run Phase 2 dense indexing.
    Returns {"success": bool, "summary": dict | None, "error": str | None}.
    """
    try:
        summary = sync_project_index(project_id, print_summary=False, run_smoke_tests=False)
        return {"success": True, "summary": summary, "error": None}
    except SystemExit as exc:
        return {"success": False, "summary": None, "error": f"Phase 2 exited with code {exc.code}."}
    except Exception as exc:
        return {"success": False, "summary": None, "error": f"Phase 2 failed: {exc}"}


def run_phase3(project_id: str) -> dict[str, Any]:
    """
    Run Phase 3 reasoning audit.
    Returns {"success": bool, "summary": dict | None, "error": str | None}.
    """
    try:
        summary = run_reasoning_audit(project_id)
        return {"success": True, "summary": summary, "error": None}
    except SystemExit as exc:
        return {"success": False, "summary": None, "error": f"Phase 3 exited with code {exc.code}."}
    except Exception as exc:
        return {"success": False, "summary": None, "error": f"Phase 3 failed: {exc}"}
