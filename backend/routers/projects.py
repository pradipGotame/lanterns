"""
routers/projects.py
===================
Project management endpoints — start, list, files, ATUs, report, delete.

Routes:
  POST   /api/projects/start                 Upload files + run pipeline
  GET    /api/projects                       List all projects
  GET    /api/projects/{project_id}/files    List files in a project
  GET    /api/projects/{project_id}/atus     Get Phase 1 ATU output
  GET    /api/projects/{project_id}/report   Download traceability report
  DELETE /api/projects/{project_id}          Delete a project
"""

from __future__ import annotations

import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from config import (
    INDICES_ROOT,
    PROJECT_ROOT,
    TRACEABILITY_ROOT,
    UPLOAD_ROOT,
)
from models import (
    FileInfo,
    ProjectFileEntry,
    ProjectSummary,
    RunStats,
    StartResponse,
)
from preprocessor import PipelineResult
from services.pipeline import run_phase1, run_phase2, run_phase3

router = APIRouter(prefix="/api/projects", tags=["Projects"])


# ── Utilities ─────────────────────────────────────────────────────────────────

def _utc_iso(path: Optional[Path] = None) -> str:
    if path:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def _category(field_name: str) -> str:
    fn = field_name.lower()
    if fn.startswith("requirement"):
        return "requirement"
    if fn.startswith("test"):
        return "test"
    if fn.startswith("code"):
        return "code"
    return "other"


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


def _traceability_dir(project_id: str) -> Path:
    return TRACEABILITY_ROOT / project_id


def _traceability_report_path(project_id: str) -> Path:
    return _traceability_dir(project_id) / "traceability_report.md"


def _project_atu_path(project_id: str) -> Path:
    d = PROJECT_ROOT / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d / "atus.json"


def _read_json_if_exists(path: Path) -> Optional[Any]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _traceability_reports_from_matrix(matrix: Optional[Any]) -> list[dict[str, Any]]:
    if not isinstance(matrix, dict):
        return []
    reports = matrix.get("traceability_reports", [])
    if not isinstance(reports, list):
        return []
    return [item for item in reports if isinstance(item, dict)]


def _split_requirement_id(value: object) -> tuple[str, str]:
    raw = str(value or "").strip()
    if "::chunk" in raw:
        req_id, chunk_id = raw.rsplit("::chunk", 1)
        return req_id, chunk_id
    return raw, ""


# ── Report builder ────────────────────────────────────────────────────────────

def _build_report(
    request: Request,
    *,
    project_id: str,
    project_name: str,
    counts: dict[str, int],
    pipeline_result: PipelineResult,
    phase2_status: dict[str, Any],
    phase3_status: dict[str, Any],
) -> dict[str, Any]:
    report_path = _traceability_report_path(project_id)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = _utc_iso()

    p2s = phase2_status.get("summary") if isinstance(
        phase2_status, dict) else None
    p3s = phase3_status.get("summary") if isinstance(
        phase3_status, dict) else None

    lines: list[str] = [
        "# Traceability Report",
        "",
        f"- Project Name: {project_name}",
        f"- Project ID: {project_id}",
        f"- Generated At: {generated_at}",
        "",
        "## Upload Summary",
        "",
        f"- Requirement files: {counts['requirement']}",
        f"- Test files: {counts['test']}",
        f"- Code files: {counts['code']}",
        f"- Total files: {counts['requirement'] + counts['test'] + counts['code']}",
        "",
        "## Phase 1",
        "",
        f"- Total artifacts: {pipeline_result.total_artifacts}",
        f"- Total ATUs: {pipeline_result.total_atus}",
        f"- Requirement ATUs: {len(pipeline_result.requirements)}",
        f"- Test ATUs: {len(pipeline_result.tests)}",
        f"- Source ATUs: {len(pipeline_result.sources)}",
    ]

    if pipeline_result.warnings:
        lines.append("- Warnings:")
        lines.extend(f"  - {w}" for w in pipeline_result.warnings)
    else:
        lines.append("- Warnings: none")

    # Phase 2
    lines.extend(["", "## Phase 2", ""])
    if phase2_status.get("success") and isinstance(p2s, dict):
        ec = p2s.get("embedding_counts", {})
        fc = p2s.get("file_counts", {})
        lines.extend([
            "- Status: success",
            f"- Active ATUs indexed: {ec.get('active', 0)}",
            f"- Embedded: {ec.get('embedded', 0)}",
            f"- Reused: {ec.get('reused', 0)}",
            f"- Deleted: {ec.get('deleted', 0)}",
            f"- Added files: {fc.get('added', 0)}",
            f"- Changed files: {fc.get('changed', 0)}",
        ])
    else:
        lines.extend(
            ["- Status: failed", f"- Error: {phase2_status.get('error', 'unknown')}"])

    # Phase 3
    lines.extend(["", "## Phase 3", ""])
    if phase3_status.get("success") and isinstance(p3s, dict):
        lines.extend([
            "- Status: success",
            "- Result source: raw requirement-level LLM JSON responses",
        ])
    else:
        lines.extend(
            ["- Status: failed", f"- Error: {phase3_status.get('error', 'Phase 3 not run.')}"])

    # Raw traceability reports from the LLM
    matrix = _read_json_if_exists(_traceability_dir(
        project_id) / "traceability_matrix.json")
    reports = _traceability_reports_from_matrix(matrix)

    lines.extend(["", "## Traceability Report", ""])
    if reports:
        lines.append(
            "| Requirement ID | Verdict | Global Confidence | Gap | Reasoning |")
        lines.append("|---|---|---|---|---|")
        for report in reports:
            gap_analysis = report.get("gap_analysis", {}) if isinstance(
                report.get("gap_analysis"), dict) else {}
            evidence_inventory = report.get("evidence_inventory", {}) if isinstance(
                report.get("evidence_inventory"), dict) else {}
            req_id = str(report.get("requirement_id", ""))
            verdict = str(report.get("final_verdict", ""))
            confidence = str(report.get("global_confidence_score", ""))
            gap = str(gap_analysis.get("gap_identified", ""))
            reasoning = str(report.get("reasoning_preamble", "")
                            ).replace("|", "\\|")
            lines.append(
                f"| {req_id} | {verdict} | {confidence} | {gap} | {reasoning} |")

            verified_by_tests = evidence_inventory.get("verified_by_tests", [])
            if isinstance(verified_by_tests, list) and verified_by_tests:
                lines.append("")
                lines.append(f"Verified by tests for `{req_id}`:")
                for item in verified_by_tests:
                    if not isinstance(item, dict):
                        continue
                    test_id = str(item.get("test_id", ""))
                    file_name = str(item.get("file", "") or "")
                    confidence_label = str(
                        item.get("verification_confidence", "") or "")
                    reasoning_text = str(item.get("reasoning", "") or "")
                    lines.append(
                        f"- {test_id} | {file_name} | {confidence_label} | {reasoning_text}"
                    )

            implemented_by = evidence_inventory.get("implemented_by", [])
            if isinstance(implemented_by, list) and implemented_by:
                lines.append("")
                lines.append(f"Implemented by for `{req_id}`:")
                for item in implemented_by:
                    if not isinstance(item, dict):
                        continue
                    function_name = str(item.get("function", "") or "")
                    file_name = str(item.get("file", "") or "")
                    confidence_label = str(
                        item.get("implementation_confidence", "") or "")
                    reasoning_text = str(item.get("reasoning", "") or "")
                    lines.append(
                        f"- {function_name} | {file_name} | {confidence_label} | {reasoning_text}"
                    )

            missing_scenarios = gap_analysis.get("missing_scenarios", [])
            if isinstance(missing_scenarios, list) and missing_scenarios:
                lines.append("")
                lines.append(f"Missing scenarios for `{req_id}`:")
                for item in missing_scenarios:
                    if not isinstance(item, dict):
                        continue
                    behaviour = str(item.get("behaviour", "") or "")
                    scenario = str(item.get("scenario", "") or "")
                    scenario_type = str(item.get("type", "") or "")
                    priority = str(item.get("priority", "") or "")
                    lines.append(
                        f"- {behaviour} | {scenario} | {scenario_type} | {priority}"
                    )

            gap_rationale = str(gap_analysis.get("gap_rationale", "") or "")
            if gap_rationale:
                lines.append("")
                lines.append(f"Gap rationale for `{req_id}`: {gap_rationale}")

            lines.append("")
    else:
        lines.extend(["No traceability reports generated.", ""])

    try:
        report_path.write_text(
            "\n".join(lines).rstrip() + "\n", encoding="utf-8")
    except Exception as exc:
        return {"available": False, "path": str(report_path), "filename": report_path.name,
                "download_url": None, "generated_at": generated_at, "error": str(exc)}

    # Extract newly embedded file names from Phase 2 summary for the UI badge
    p2_summary = phase2_status.get("summary") if isinstance(
        phase2_status, dict) else None
    newly_embedded: list[str] = (
        p2_summary.get("newly_embedded_files", [])
        if isinstance(p2_summary, dict) else []
    )

    return {
        "available":             True,
        "path":                  str(report_path),
        "filename":              report_path.name,
        "download_url":          str(request.url_for("download_project_report", project_id=project_id)),
        "generated_at":          generated_at,
        "error":                 None,
        # List of file names newly embedded in Phase 2 — consumed by the frontend
        "newly_embedded_files":  newly_embedded,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/start", response_model=StartResponse)
async def start_project(request: Request) -> StartResponse:
    """Upload project files and run the full analysis pipeline (Phase 1 → 3)."""
    try:
        form = await request.form()
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid multipart data: {exc}")

    project_name = str(form.get("projectName") or "unnamed")
    project_id = str(form.get("projectId") or "unknown")
    started_at = _utc_iso()

    project_dir = UPLOAD_ROOT / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    saved: list[FileInfo] = []
    counts: dict[str, int] = {"requirement": 0,
                              "test": 0, "code": 0, "other": 0}

    for field_name, value in form.multi_items():
        if field_name in ("projectName", "projectId") or not hasattr(value, "filename"):
            continue
        original_name = value.filename or "unnamed_file"
        content_type = value.content_type or "application/octet-stream"
        category = _category(field_name)
        ts = datetime.now().strftime("%H%M%S%f")[:10]
        save_name = f"{category}_{ts}_{_safe_filename(original_name)}"
        dest = project_dir / save_name
        contents = await value.read()
        dest.write_bytes(contents)
        counts[category] = counts.get(category, 0) + 1
        saved.append(FileInfo(
            field_name=field_name, original_name=original_name,
            size_bytes=len(contents), content_type=content_type,
            saved_as=str(dest.relative_to(UPLOAD_ROOT)),
        ))

    total = counts["requirement"] + counts["test"] + counts["code"]

    print(f"\n{'─'*54}")
    print(f"  START  |  {project_name!r}  ({project_id})")
    print(
        f"  Files  |  Req:{counts['requirement']} Test:{counts['test']} Code:{counts['code']} Total:{total}")

    # Phase 1
    pipeline_result = run_phase1(
        project_id=project_id, project_dir=project_dir)
    atu_path = project_dir / "phase1_atus.json"
    atu_path.write_text(pipeline_result.model_dump_json(
        indent=2), encoding="utf-8")
    _project_atu_path(project_id).write_text(
        pipeline_result.model_dump_json(indent=2), encoding="utf-8"
    )
    print(f"  Phase1 →  {pipeline_result.total_atus} ATUs")

    # Phase 2
    phase2 = run_phase2(project_id)
    print(f"  Phase2 →  {'ok' if phase2['success'] else phase2['error']}")

    # Phase 3 (only if Phase 2 succeeded)
    phase3 = run_phase3(project_id) if phase2["success"] else {
        "success": False, "summary": None, "error": "Phase 3 skipped (Phase 2 unavailable)."
    }
    print(f"  Phase3 →  {'ok' if phase3['success'] else phase3['error']}")

    report_info = _build_report(
        request, project_id=project_id, project_name=project_name,
        counts=counts, pipeline_result=pipeline_result,
        phase2_status=phase2, phase3_status=phase3,
    )
    print(f"{'─'*54}\n")

    pipeline_summary: dict[str, Any] = {
        "total_artifacts":  pipeline_result.total_artifacts,
        "total_atus":       pipeline_result.total_atus,
        "requirement_atus": len(pipeline_result.requirements),
        "test_atus":        len(pipeline_result.tests),
        "source_atus":      len(pipeline_result.sources),
        "warnings":         pipeline_result.warnings,
        "phase2_indexing":  phase2,
        "phase3_reasoning": phase3,
        "report":           report_info,
    }

    return StartResponse(
        success=True,
        message="Project started" if phase2["success"] and phase3[
            "success"] else "Project started (partial results)",
        project_name=project_name,
        project_id=project_id,
        started_at=started_at,
        stats=RunStats(
            requirement_files=counts["requirement"],
            test_files=counts["test"],
            code_files=counts["code"],
            total_files=total,
        ),
        files=saved,
        saved_to=str(project_dir),
        pipeline=pipeline_summary,
        atu_output_file=str(atu_path),
        report=report_info,
    )


@router.get("", response_model=list[ProjectSummary])
async def list_projects() -> list[ProjectSummary]:
    """List all projects, most recent first."""
    if not UPLOAD_ROOT.exists():
        return []
    results = []
    for p in sorted(UPLOAD_ROOT.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_dir():
            continue
        files = [f for f in p.iterdir() if f.is_file()]
        results.append(ProjectSummary(
            project_id=p.name,
            file_count=len(files),
            size_bytes=sum(f.stat().st_size for f in files),
            modified_at=_utc_iso(p),
        ))
    return results


@router.get("/{project_id}/files", response_model=list[ProjectFileEntry])
async def get_project_files(project_id: str) -> list[ProjectFileEntry]:
    """List all files saved for a specific project."""
    project_dir = UPLOAD_ROOT / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    return [
        ProjectFileEntry(
            name=f.name,
            size_bytes=f.stat().st_size,
            category=f.name.split("_")[0] if "_" in f.name else "other",
            modified_at=_utc_iso(f),
        )
        for f in sorted(project_dir.iterdir(), key=lambda x: x.stat().st_mtime)
        if f.is_file()
    ]


@router.get("/{project_id}/atus")
async def get_project_atus(project_id: str) -> dict:
    """Return Phase 1 ATU output for a project."""
    atu_file = UPLOAD_ROOT / project_id / "phase1_atus.json"
    if not atu_file.exists():
        raise HTTPException(
            status_code=404, detail="No ATU output. Run 'Start' first.")
    return json.loads(atu_file.read_text(encoding="utf-8"))


@router.get("/{project_id}/report", name="download_project_report")
async def download_project_report(project_id: str) -> FileResponse:
    """Download the generated traceability report (Markdown)."""
    report_path = _traceability_report_path(project_id)
    if not report_path.is_file():
        raise HTTPException(
            status_code=404, detail="No report found. Run 'Start Project' first.")
    return FileResponse(
        report_path,
        media_type="text/markdown; charset=utf-8",
        filename=f"{project_id}_traceability_report.md",
    )


@router.get("/{project_id}/report/csv", name="download_project_report_csv")
async def download_project_report_csv(project_id: str):
    """
    Download the raw requirement-level LLM traceability reports as CSV.
    """
    import csv
    import io

    matrix_path = _traceability_dir(project_id) / "traceability_matrix.json"
    if not matrix_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="No traceability matrix found. Run 'Start Project' first.",
        )

    matrix = _read_json_if_exists(matrix_path)
    reports = _traceability_reports_from_matrix(matrix)

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "requirement_id",
            "requirement_chunk_id",
            "reasoning",
            "final_verdict",
            "gap_identified",
            "gap_rationale",
            "verified_by_tests",
            "implemented_by",
            "missing_scenarios",
        ],
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for report in reports:
        gap = report.get("gap_analysis", {}) if isinstance(
            report.get("gap_analysis"), dict) else {}
        evidence_inventory = report.get("evidence_inventory", {}) if isinstance(
            report.get("evidence_inventory"), dict) else {}
        verified_by_tests = evidence_inventory.get("verified_by_tests", [])
        reasoning = " | ".join(
            str(item.get("reasoning", "")).strip()
            for item in verified_by_tests
            if isinstance(item, dict) and str(item.get("reasoning", "")).strip()
        )
        req_id, req_chunk_id = _split_requirement_id(
            report.get("requirement_id", ""))
        writer.writerow({
            "requirement_id": req_id,
            "requirement_chunk_id": req_chunk_id,
            "reasoning": reasoning,
            "final_verdict": report.get("final_verdict", ""),
            "gap_identified": gap.get("gap_identified", ""),
            "gap_rationale": gap.get("gap_rationale", ""),
            "verified_by_tests": json.dumps(
                verified_by_tests,
                ensure_ascii=False,
            ),
            "implemented_by": json.dumps(
                evidence_inventory.get("implemented_by", []),
                ensure_ascii=False,
            ),
            "missing_scenarios": json.dumps(
                gap.get("missing_scenarios", []),
                ensure_ascii=False,
            ),
        })

    from fastapi.responses import Response
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{project_id}_traceability.csv"'
        },
    )


@router.delete("/{project_id}")
async def delete_project(project_id: str) -> dict:
    """Delete a project and all generated artefacts."""
    targets = [
        UPLOAD_ROOT / project_id,
        PROJECT_ROOT / project_id,
        INDICES_ROOT / project_id,
        TRACEABILITY_ROOT / project_id,
    ]
    existing = [p for p in targets if p.exists()]
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")
    for p in existing:
        shutil.rmtree(p) if p.is_dir() else p.unlink(missing_ok=True)
    return {"success": True, "message": f"Project '{project_id}' deleted"}
