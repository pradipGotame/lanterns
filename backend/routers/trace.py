"""
routers/trace.py
================
Traceability retrieval and live report endpoints.

The live report flow under /api/trace persists five corpus-wide artifacts:
  - rerank_report.json       internal Stage 2 dependency
  - traceability_report.json final traceability report
  - assertion_input_report.json internal Stage 4 assertion input snapshot
  - assertion_report.json    dependent assertion export built from traceability
  - generated_tests_manifest.json plus generated source files from assertion gaps
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import json
import csv
import io
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from scripts.run_reasoning_audit import _get_client, _run_requirement_audit
from services.live_reports import (
    assertion_saved_status,
    build_traceability_view,
    clear_assertion_report,
    clear_generated_tests,
    clear_traceability_outputs_keep_rerank,
    clear_traceability_reports,
    extract_requirement_traceability_details,
    flatten_traceability_rows,
    generated_test_file_path,
    generated_tests_saved_status,
    load_assertion_input_report,
    load_generated_tests_manifest,
    load_assertion_report,
    load_rerank_report,
    load_traceability_report,
    save_assertion_input_report,
    save_assertion_report,
    save_generated_test_file,
    save_generated_tests_manifest,
    save_rerank_report,
    save_traceability_report,
    summarize_rows,
    traceability_saved_status,
)
from services.retriever import (
    CROSS_ENCODER_MODEL,
    RETRIEVAL_PARAMS,
    apply_test_safeguard,
    batch_embed_requirements,
    classify_requirement,
    dynamic_top_k_final_enabled,
    greedy_diversify,
    recall_all_requirements,
    recall_for_requirement,
    recall_with_vector,
    rerank_candidates,
    resolve_top_k_final,
    retrieve_all_requirements,
    retrieve_for_requirement,
)
from services.vector_store import get_store

router = APIRouter(prefix="/api/trace", tags=["Traceability"])


# ── Report job state ──────────────────────────────────────────────────────────

def _blank_job() -> dict:
    return {
        "running": False,
        "started_at": None,
        "finished_at": None,
        "progress": 0,
        "total": 0,
        "current": None,
        "logs": [],
        "done": False,
        "error": None,
        "warnings": [],
        "resumed": False,
    }


_report_job: dict = _blank_job()
_assertion_job: dict = _blank_job()
_tests_job: dict = _blank_job()

TRACE_STAGE3_MAX_CONCURRENCY = max(
    1,
    int(os.environ.get("TRACE_STAGE3_MAX_CONCURRENCY", "4")),
)
TRACE_ASSERTION_MAX_CONCURRENCY = max(
    1,
    int(os.environ.get("TRACE_ASSERTION_MAX_CONCURRENCY", "4")),
)
TRACE_GENERATED_TESTS_MAX_CONCURRENCY = max(
    1,
    int(os.environ.get("TRACE_GENERATED_TESTS_MAX_CONCURRENCY", "2")),
)

_FRAMEWORK_HINTS: dict[str, dict[str, str]] = {
    "cunit_c": {
        "framework": "cunit",
        "language": "c",
        "slug": "cunit_c",
        "extension": "c",
        "comment_style": "c",
    },
    "pytest_python": {
        "framework": "pytest",
        "language": "python",
        "slug": "pytest_python",
        "extension": "py",
        "comment_style": "hash",
    },
    "unittest_python": {
        "framework": "unittest",
        "language": "python",
        "slug": "unittest_python",
        "extension": "py",
        "comment_style": "hash",
    },
    "jest_javascript": {
        "framework": "jest",
        "language": "javascript",
        "slug": "jest_javascript",
        "extension": "js",
        "comment_style": "slash",
    },
    "vitest_typescript": {
        "framework": "vitest",
        "language": "typescript",
        "slug": "vitest_typescript",
        "extension": "ts",
        "comment_style": "slash",
    },
    "vitest_javascript": {
        "framework": "vitest",
        "language": "javascript",
        "slug": "vitest_javascript",
        "extension": "js",
        "comment_style": "slash",
    },
    "jest_typescript": {
        "framework": "jest",
        "language": "typescript",
        "slug": "jest_typescript",
        "extension": "ts",
        "comment_style": "slash",
    },
    "mocha_javascript": {
        "framework": "mocha",
        "language": "javascript",
        "slug": "mocha_javascript",
        "extension": "js",
        "comment_style": "slash",
    },
    "go_test": {
        "framework": "go test",
        "language": "go",
        "slug": "go_test",
        "extension": "go",
        "comment_style": "slash",
    },
    "junit_java": {
        "framework": "junit",
        "language": "java",
        "slug": "junit_java",
        "extension": "java",
        "comment_style": "slash",
    },
    "rspec_ruby": {
        "framework": "rspec",
        "language": "ruby",
        "slug": "rspec_ruby",
        "extension": "rb",
        "comment_style": "hash",
    },
    "csharp_test": {
        "framework": "csharp test",
        "language": "csharp",
        "slug": "csharp_test",
        "extension": "cs",
        "comment_style": "slash",
    },
    "generic_c": {
        "framework": "generic c test",
        "language": "c",
        "slug": "generic_c",
        "extension": "c",
        "comment_style": "c",
    },
    "generic_python": {
        "framework": "generic python test",
        "language": "python",
        "slug": "generic_python",
        "extension": "py",
        "comment_style": "hash",
    },
    "generic_javascript": {
        "framework": "generic javascript test",
        "language": "javascript",
        "slug": "generic_javascript",
        "extension": "js",
        "comment_style": "slash",
    },
    "generic_typescript": {
        "framework": "generic typescript test",
        "language": "typescript",
        "slug": "generic_typescript",
        "extension": "ts",
        "comment_style": "slash",
    },
    "generic_java": {
        "framework": "generic java test",
        "language": "java",
        "slug": "generic_java",
        "extension": "java",
        "comment_style": "slash",
    },
}

_ASSERTION_SYSTEM_PROMPT = """You are a strict assertion-quality checker in a software traceability pipeline.
Your task:
1) Decide whether retrieved tests contain assertion evidence that verifies the requirement.
2) Highlight missing assertions and weak/prohibited patterns using project standards context.
3) Return a strict JSON object only (no markdown, no prose outside JSON).

## Evidence Rules

- Use only text from the provided context blocks.
- Do not invent tests, code, lines, or rules.
- If a value is unknown, use `null`.


## Scoring Rules (for `assertion_verdict`)

- `"assertions_verified"`** → all stated behaviours, boundaries, and error paths are asserted.
   Core behavior* means the essential action or outcome (e.g., a successful API call, a non‑zero length, a specific error code).

- `"partially_verified"` → core path covered, at least one stated behaviour or boundary missing

- "no_assertion_evidence"` → topically related but no assertion directly verifies the requirement


## Gap Definition

- `gap = true` true when verdict is "partially_verified" or "no_assertion_evidence".
"""

_TEST_GENERATION_SYSTEM_PROMPT = """You are an expert software test-generation assistant.

Your job is to generate project‑style executable test code strictly from assertion‑gap evidence.

## Inputs You Will Receive

You will receive:
1. A requirement text with its ID.
2. A list of assertion gaps (each with missing behaviour, suggested assertion, severity, type).
3. Existing verified tests (exemplars) showing the project's framework and style, if available.
4. Supporting code snippets (optional).

## Rules (Strict)

- Use **only** the provided requirement, gaps, exemplar tests, and code snippets.
- If no exemplar tests or framework context are available, fall back to a self-contained Python test using only `pytest` and the Python standard library.
- Do not invent project-specific APIs, helpers, fixtures, constants, imports, or behaviour unless explicitly shown in the exemplars or supporting code.
- Preserve the detected framework and language style **exactly** as in the exemplars when exemplars are available.
- Produce **one test function per distinct gap group**. A gap group is defined as:
  - Gaps that share the same `type` (e.g., `error_handling`, `boundary`, `happy_path`).
  - Gaps that can be covered by the same test without conflicting setup.
  - If gaps conflict (e.g., one requires a valid certificate, another an invalid one), separate them into different functions.
- Name each generated test function from the **semantic meaning** of the gap(s) it covers.
  - **Good:** `test_returns_null_for_invalid_credentials`, `test_ca_cert_copy_buffer_overflow`
  - **Bad:** `test_full_flow`, `test_RQ4_chunk2`, `test_gap1`
- Do not use requirement IDs, chunk numbers, placeholders like `full_flow`, or generic numbered names as the function name.
- If shared imports, includes, fixtures, or helpers are needed, place them in the `shared_prelude` field exactly once.
- Generated code must be copyable into the target project test suite and runnable as‑is, given the provided context.
- Return **only one strict JSON object** matching the schema below. No markdown, no prose outside the JSON.

## Output Schema

```json
{
  "generated_test_file": {
    "framework": "string (e.g., pytest, JUnit, CUnit, Jest)",
    "language": "string (e.g., Python, Java, C, JavaScript)",
    "filename": "string (suggested file name, e.g., test_auth_invalid.py)",
    "shared_prelude": "string (imports, includes, fixtures, setup code that all test functions need)",
    "test_functions": [
      {
        "function_name": "string (semantic name, e.g., test_returns_null_for_invalid_credentials)",
        "requirement_ids": ["array of requirement IDs that this test addresses"],
        "gap_key": "string (short unique identifier derived from the gap's missing behaviour, e.g., 'null_on_invalid_creds')",
        "reasoning_basis": "1-2 sentences explaining, based on the provided context, why this test covers the gap(s).",
        "code": "string (the complete test function code, properly indented)"
      }
    ]
  }
}
"""


_ASSERTION_STATUS_MAP: dict[str, tuple[str, str]] = {
    "direct": ("accepted", "full"),
    "partial": ("rejected", "partial"),
    "weak": ("rejected", "weak"),
    "missing": ("rejected", "weak"),
}


def _begin_job(job: dict) -> None:
    job.update(
        running=True,
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None,
        progress=0,
        total=0,
        current=None,
        logs=[],
        done=False,
        error=None,
        warnings=[],
        resumed=False,
    )


def _reset_job(job: dict) -> None:
    job.clear()
    job.update(_blank_job())


def _job_logger(job: dict, prefix: str):
    def _log(msg: str) -> None:
        job["logs"].append(msg)
        print(f"[{prefix}] {msg}")

    return _log


def _normalize_gap_text(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" \t\r\n.,;:!?\"'`()[]{}")


def _trim_text(text: object, max_chars: int = 1200) -> str:
    value = str(text or "").strip()
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars].rstrip()}..."


def _comment_prefix(comment_style: str) -> str:
    if comment_style == "hash":
        return "#"
    if comment_style == "c":
        return "*"
    return "//"


def _extract_declared_identifier(code: str) -> Optional[str]:
    patterns = [
        r"\bstatic\s+void\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bvoid\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bfunc\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bconst\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\(",
        r"\b(?:public|private|protected)?\s*(?:static\s+)?(?:void|int|bool|boolean|String|[A-Za-z_][A-Za-z0-9_<>,]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    ]
    for pattern in patterns:
        match = re.search(pattern, code, flags=re.MULTILINE)
        if match:
            return match.group(1)
    return None


def _rename_code_identifier(code: str, old_name: str, new_name: str) -> str:
    if not old_name or not new_name or old_name == new_name:
        return code

    replacements = [
        (rf"(\bstatic\s+void\s+){re.escape(old_name)}(\s*\()",
         r"\1" + new_name + r"\2"),
        (rf"(\bvoid\s+){re.escape(old_name)}(\s*\()",
         r"\1" + new_name + r"\2"),
        (rf"(\bdef\s+){re.escape(old_name)}(\s*\()", r"\1" + new_name + r"\2"),
        (rf"(\bfunc\s+){re.escape(old_name)}(\s*\()",
         r"\1" + new_name + r"\2"),
        (rf"(\bfunction\s+){re.escape(old_name)}(\s*\()",
         r"\1" + new_name + r"\2"),
        (rf"(\bconst\s+){re.escape(old_name)}(\s*=\s*(?:async\s*)?\()",
         r"\1" + new_name + r"\2"),
        (
            rf"(\b(?:public|private|protected)?\s*(?:static\s+)?(?:void|int|bool|boolean|String|[A-Za-z_][A-Za-z0-9_<>,]*)\s+){re.escape(old_name)}(\s*\()",
            r"\1" + new_name + r"\2",
        ),
    ]

    updated = code
    for pattern, replacement in replacements:
        candidate, count = re.subn(
            pattern, replacement, updated, count=1, flags=re.MULTILINE)
        if count:
            return candidate
    return updated


def _safe_generation_token(value: object, fallback: str = "generated", preserve_case: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    safe = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    if not safe:
        return fallback
    return safe if preserve_case else safe.lower()


def _cluster_requirement_prefix(cluster: dict, preserve_case: bool = False) -> str:
    primary = (cluster.get("requirements") or [{}])[0]
    requirement_file = str(primary.get("file", "")).strip()
    requirement_stem = Path(
        requirement_file).stem or requirement_file or "requirement"
    requirement_token = _safe_generation_token(
        requirement_stem,
        fallback="requirement",
        preserve_case=preserve_case,
    )
    chunk_index = str(primary.get("chunk_index", "")).strip()
    if not chunk_index:
        return requirement_token
    chunk_token = _safe_generation_token(
        f"chunk{chunk_index}",
        fallback="chunk",
        preserve_case=preserve_case,
    )
    return f"{requirement_token}_{chunk_token}"


def _cluster_test_name_base(cluster: dict) -> str:
    base = _cluster_requirement_prefix(cluster, preserve_case=False)
    if base and base[0].isdigit():
        return f"generated_{base}"
    return base or "generated"


def _preferred_function_name(
    cluster: dict,
    sequence_number: int = 1,
    framework_info: Optional[dict] = None,
) -> str:
    base = _cluster_test_name_base(cluster)
    index = max(1, int(sequence_number or 1))
    return f"{base}_missing_test_{index}"


def _render_generated_file(
    framework_info: dict,
    filename: str,
    shared_prelude: str,
    tests: list[dict],
) -> str:
    comment_style = framework_info.get("comment_style", "slash")
    header_lines = [
        "Generated from saved assertion gaps.",
        f"framework={framework_info.get('framework', '')}",
        f"language={framework_info.get('language', '')}",
        f"filename={filename}",
    ]
    if comment_style == "c":
        header = "/*\n" + \
            "\n".join(f" * {line}" for line in header_lines) + "\n */"
    else:
        prefix = _comment_prefix(comment_style)
        header = "\n".join(f"{prefix} {line}" for line in header_lines)

    body_parts = [header]
    prelude = str(shared_prelude or "").strip()
    if prelude:
        body_parts.append(prelude)
    for item in tests:
        code = str(item.get("code", "")).strip()
        if code:
            body_parts.append(code)
    return "\n\n".join(body_parts).strip() + "\n"


def _framework_from_candidate(file_name: object, text: object) -> Optional[str]:
    suffix = Path(str(file_name or "")).suffix.lower()
    lower = str(text or "").lower()

    if suffix == ".c":
        if "cunit/" in lower or "cu_assert" in lower or "cu_add_test" in lower:
            return "cunit_c"
        return "generic_c"
    if suffix == ".py":
        if "unittest" in lower or "testcase" in lower:
            return "unittest_python"
        if "pytest" in lower or "def test_" in lower:
            return "pytest_python"
        return "generic_python"
    if suffix in {".ts", ".tsx"}:
        if "vitest" in lower or "from 'vitest'" in lower or 'from "vitest"' in lower:
            return "vitest_typescript"
        if "jest" in lower or "@jest/globals" in lower:
            return "jest_typescript"
        return "generic_typescript"
    if suffix in {".js", ".jsx"}:
        if "vitest" in lower or "from 'vitest'" in lower or 'from "vitest"' in lower:
            return "vitest_javascript"
        if "jest" in lower or "@jest/globals" in lower or (
            "describe(" in lower and "it(" in lower and "expect(" in lower
        ):
            return "jest_javascript"
        if "mocha" in lower:
            return "mocha_javascript"
        return "generic_javascript"
    if suffix == ".go":
        return "go_test"
    if suffix == ".java":
        if "org.junit" in lower or "@test" in lower:
            return "junit_java"
        return "generic_java"
    if suffix == ".rb":
        return "rspec_ruby"
    if suffix == ".cs":
        return "csharp_test"
    return None


def _unique_preserve_order(values: list[object]) -> list[object]:
    seen = set()
    ordered = []
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=False) if isinstance(
            value, (dict, list)) else str(value)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return ordered


def _ranked(items: list[dict]) -> list[dict]:
    return [{**item, "rank": i + 1} for i, item in enumerate(items)]


def _requirement_label(requirement: dict, fallback_index: int = 0) -> str:
    fname = requirement.get("file", "?")
    cidx = requirement.get("chunk_index", fallback_index)
    return f"{fname}  [chunk {cidx}]"


def _test_id_from_candidate(candidate: dict) -> str:
    return f"{candidate.get('file_name', '')}::chunk{candidate.get('chunk_index', '')}"


def _promoted_test_debug_rows(candidates: list[dict]) -> list[dict]:
    return [
        {
            "test_id": _test_id_from_candidate(item),
            "file": item.get("file_name", ""),
            "chunk_index": item.get("chunk_index", ""),
            "stage1_rank": item.get("stage1_rank", ""),
            "score": item.get("score", ""),
            "rerank_score": item.get("rerank_score", ""),
            "safeguard_reason": item.get("safeguard_reason", ""),
        }
        for item in candidates
    ]


def _build_traceability_meta(traceability: list[dict], generated_at: str, rerank_generated_at: str) -> dict:
    rows = flatten_traceability_rows(
        {"meta": {"generated_at": generated_at}, "traceability": traceability}
    )
    counts = _traceability_progress_counts(traceability)
    covered = 0
    partially_covered = 0
    not_covered = 0
    verified_test_rows = 0
    implemented_by_rows = 0

    for entry in traceability:
        mapper = _derive_traceability_summary(entry)
        verdict = str(mapper.get("verdict", "")).strip()
        if verdict == "covered":
            covered += 1
        elif verdict == "partially_covered":
            partially_covered += 1
        elif verdict == "not_covered":
            not_covered += 1
        verified_test_rows += len(mapper.get("verified_tests", []))
        implemented_by_rows += len(mapper.get("implemented_by", []))

    return {
        "generated_at": generated_at,
        "rerank_generated_at": rerank_generated_at,
        "llm_generated_at": generated_at,
        "model_embedding": os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        "model_reranker": CROSS_ENCODER_MODEL,
        "model_llm": os.environ.get("OPENAI_LLM_MODEL", "gpt-5-mini"),
        "retrieval_params": RETRIEVAL_PARAMS,
        "total_requirements": counts["total_requirements"],
        "total_rows": len(rows),
        "verified_test_rows": verified_test_rows,
        "implemented_by_rows": implemented_by_rows,
        "covered": covered,
        "partially_covered": partially_covered,
        "not_covered": not_covered,
        "completed_requirements": counts["completed_requirements"],
        "failed_requirements": counts["failed_requirements"],
        "pending_requirements": counts["pending_requirements"],
        "finalized": counts["pending_requirements"] == 0,
        "complete": (
            counts["pending_requirements"] == 0
            and counts["failed_requirements"] == 0
        ),
    }


def _requirement_id(requirement: dict) -> str:
    req_file = requirement.get("file", "")
    req_chunk = requirement.get("chunk_index", "")
    return f"{req_file}::chunk{req_chunk}"


def _entry_has_completed_traceability(entry: dict) -> bool:
    report = entry.get("traceability_report")
    return isinstance(report, dict) and bool(report)


def _entry_has_failed_traceability(entry: dict) -> bool:
    error = entry.get("traceability_error")
    if not isinstance(error, dict):
        return False
    return bool(str(error.get("message", "")).strip())


def _traceability_progress_counts(
    traceability: list[dict],
    total_requirements: int | None = None,
) -> dict:
    completed = 0
    failed = 0
    pending = 0

    for entry in traceability:
        if _entry_has_completed_traceability(entry):
            completed += 1
        elif _entry_has_failed_traceability(entry):
            failed += 1
        else:
            pending += 1

    total = total_requirements if total_requirements is not None else len(
        traceability)
    if total > len(traceability):
        pending += total - len(traceability)

    return {
        "total_requirements": total,
        "completed_requirements": completed,
        "failed_requirements": failed,
        "pending_requirements": pending,
    }


def _traceability_report_complete(report: dict | None) -> bool:
    if not report:
        return False
    meta = report.get("meta", {}) or {}
    if "complete" in meta:
        return bool(meta.get("complete"))
    return True


def _traceability_report_needs_resume(report: dict | None) -> bool:
    if not report:
        return False
    meta = report.get("meta", {}) or {}
    if "complete" in meta or "pending_requirements" in meta or "failed_requirements" in meta:
        return not bool(meta.get("complete"))
    return False


def _rerank_report_needs_resume(report: dict | None) -> bool:
    if not report:
        return False
    meta = report.get("meta", {}) or {}
    if "complete" in meta:
        return not bool(meta.get("complete"))
    total = meta.get("total_requirements")
    completed = meta.get("completed_requirements")
    try:
        total_value = int(total)
        completed_value = int(completed)
    except (TypeError, ValueError):
        return False
    return total_value > 0 and completed_value < total_value


def _report_has_resumable_progress() -> bool:
    traceability_report = load_traceability_report()
    if _traceability_report_needs_resume(traceability_report):
        return True
    rerank_report = load_rerank_report()
    return _rerank_report_needs_resume(rerank_report)


def _save_rerank_checkpoint(
    traceability: list[dict],
    total_requirements: int,
    generated_at: str | None = None,
    *,
    complete: bool,
) -> str:
    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    save_rerank_report({
        "meta": {
            "generated_at": timestamp,
            "model_embedding": os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            "model_reranker": CROSS_ENCODER_MODEL,
            "retrieval_params": RETRIEVAL_PARAMS,
            "total_requirements": total_requirements,
            "completed_requirements": len(traceability),
            "remaining_requirements": max(total_requirements - len(traceability), 0),
            "complete": complete,
        },
        "traceability": traceability,
    })
    return timestamp


def _save_traceability_checkpoint(
    traceability: list[dict],
    total_requirements: int,
    rerank_generated_at: str,
) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    meta = _build_traceability_meta(
        traceability, generated_at, rerank_generated_at)
    meta["total_requirements"] = total_requirements
    progress = _traceability_progress_counts(traceability, total_requirements)
    meta["completed_requirements"] = progress["completed_requirements"]
    meta["failed_requirements"] = progress["failed_requirements"]
    meta["pending_requirements"] = progress["pending_requirements"]
    meta["finalized"] = progress["pending_requirements"] == 0
    meta["complete"] = (
        progress["pending_requirements"] == 0
        and progress["failed_requirements"] == 0
    )
    save_traceability_report({
        "meta": meta,
        "traceability": traceability,
    })
    return generated_at


def _load_resumable_traceability_entries(
    requirement_ids: set[str],
    _log=None,
    *,
    allow_completed_rerank: bool = False,
) -> tuple[dict[str, dict], str | None, str | None]:
    traceability_report = load_traceability_report()
    if _traceability_report_needs_resume(traceability_report):
        entries_by_id: dict[str, dict] = {}
        for entry in traceability_report.get("traceability", []):
            req_id = _requirement_id(entry.get("requirement", {}))
            if req_id in requirement_ids and req_id not in entries_by_id:
                entries_by_id[req_id] = deepcopy(entry)
        rerank_generated_at = str(
            traceability_report.get("meta", {}).get("rerank_generated_at", "")
        ).strip() or None
        if _log:
            _log(
                f"Resume checkpoint found in saved traceability report — reusable requirements={len(entries_by_id)}"
            )
        return entries_by_id, rerank_generated_at, "traceability"

    rerank_report = load_rerank_report()
    rerank_can_resume = _rerank_report_needs_resume(rerank_report)
    rerank_can_reuse = rerank_can_resume or (
        allow_completed_rerank
        and bool((rerank_report or {}).get("traceability"))
    )
    if rerank_can_reuse:
        entries_by_id = {}
        for entry in rerank_report.get("traceability", []):
            req_id = _requirement_id(entry.get("requirement", {}))
            if req_id in requirement_ids and req_id not in entries_by_id:
                entries_by_id[req_id] = deepcopy(entry)
        rerank_generated_at = str(
            rerank_report.get("meta", {}).get("generated_at", "")
        ).strip() or None
        if _log and entries_by_id:
            _log(
                (
                    "Resume checkpoint found in saved rerank report"
                    if rerank_can_resume
                    else "Saved rerank report found — reusing Stage 2 candidates for Stage 3 rerun"
                )
                + f" — reusable requirements={len(entries_by_id)}"
            )
        if entries_by_id:
            return entries_by_id, rerank_generated_at, "rerank"

    return {}, None, None


def _derive_traceability_summary(entry: dict) -> dict:
    details = extract_requirement_traceability_details(entry)
    candidate_test_judgments = details.get(
        "candidate_test_judgments", []) or details.get("verified_tests", [])
    return {
        "verdict": details.get("final_verdict", ""),
        "reasoning_summary": details.get("reasoning_preamble", ""),
        "requirement_reasoning": details.get("reasoning_preamble", ""),
        "covered_by": candidate_test_judgments,
        "candidate_test_judgments": candidate_test_judgments,
        "verified_by_tests": details.get("verified_tests", []),
        "missing_scenarios": details.get("missing_scenarios", []),
        "gap": details.get("gap_identified"),
        "gap_reason": details.get("gap_rationale"),
        "verified_tests": details.get("verified_tests", []),
        "implemented_by": details.get("implemented_by", []),
        "supporting_sources": details.get("supporting_sources", []),
    }


def _derive_assertion_traceability_summary(entry: dict) -> dict:
    summary = _derive_traceability_summary(entry)
    verified_tests = summary.get("verified_tests", []) or []

    # Assertion analysis should only inspect tests that Stage 3 accepted as
    # actual trace links. Passing the full candidate judgment list here causes
    # the assertion step to treat non-links as required evidence rows.
    return {
        **summary,
        "covered_by": verified_tests,
        "candidate_test_judgments": verified_tests,
        "verified_by_tests": verified_tests,
    }


def _build_assertion_input_report(traceability_report: dict) -> dict:
    traceability = traceability_report.get("traceability", []) or []
    traceability_generated_at = (
        traceability_report.get("meta", {}).get("generated_at")
    )
    generated_at = datetime.now(timezone.utc).isoformat()

    requirements: list[dict] = []
    for entry in traceability:
        requirement = deepcopy(entry.get("requirement", {}) or {})
        summary = _derive_assertion_traceability_summary(entry)
        requirements.append({
            "requirement": requirement,
            "traceability_summary": summary,
        })

    return {
        "meta": {
            "generated_at": generated_at,
            "traceability_generated_at": traceability_generated_at,
            "total_requirements": len(requirements),
            "model_llm": os.environ.get("OPENAI_LLM_MODEL", "gpt-5-mini"),
        },
        "requirements": requirements,
    }


def _ensure_assertion_input_report(
    traceability_report: dict,
    _log=None,
) -> dict:
    traceability_generated_at = (
        traceability_report.get("meta", {}).get("generated_at")
    )
    saved = load_assertion_input_report()
    saved_requirements = saved.get(
        "requirements") if isinstance(saved, dict) else None
    if (
        saved
        and isinstance(saved_requirements, list)
        and saved.get("meta", {}).get("traceability_generated_at")
        == traceability_generated_at
    ):
        if _log:
            _log("Assertion input snapshot reused from saved Stage 3 traceability data")
        return saved

    payload = _build_assertion_input_report(traceability_report)
    save_assertion_input_report(payload)
    if _log:
        _log(
            "Assertion input snapshot prepared from saved Stage 3 traceability data "
            f"({len(payload.get('requirements', []))} requirements)"
        )
    return payload


def _resolve_assertion_traceability_summary(entry: dict) -> dict:
    summary = entry.get("traceability_summary")
    if isinstance(summary, dict):
        return summary
    return _derive_assertion_traceability_summary(entry)


def _json_block(payload) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _assertion_candidate_tests(summary: dict) -> list[dict]:
    return (
        summary.get("covered_by", [])
        or summary.get("candidate_test_judgments", [])
        or summary.get("verified_tests", [])
        or []
    )


def _run_requirement_traceability_report(entry: dict, client, _log=None, log_label=None) -> dict:
    requirement = entry.get("requirement", {})
    requirement_id = _requirement_id(requirement)
    req_meta = {
        "atu_id": requirement_id,
        "file_id": requirement.get("file", ""),
        "file_name": requirement.get("file", ""),
        "chunk_index": requirement.get("chunk_index", ""),
        "section_title": requirement.get("file", ""),
    }
    candidates = {
        "tests": entry.get("final_candidates", {}).get("tests", []) or [],
        "sources": entry.get("final_candidates", {}).get("sources", []) or [],
    }

    model = os.environ.get("OPENAI_LLM_MODEL", "gpt-5-mini")
    print(f"[traceability-summary →] {model} | requirement={requirement_id}")
    if _log and log_label:
        _log(f"LLM →  {log_label}  (requirement-summary)")

    try:
        report = _run_requirement_audit(
            requirement.get("text", ""),
            req_meta,
            candidates,
            client,
        )
        print(
            f"[traceability-summary ←] requirement={requirement_id} | verdict={report.get('final_verdict', '')}"
        )
        if _log and log_label:
            _log(
                f"LLM ←  {log_label}  (requirement-summary)  "
                f"verdict={report.get('final_verdict', '')}"
            )
        return report
    except Exception as exc:
        print(
            f"[traceability-summary ✗] requirement={requirement_id} | error={exc}")
        if _log and log_label:
            _log(f"LLM ✗  {log_label}  (requirement-summary)  error={exc}")
        raise


def _build_assertion_prompt(entry: dict, summary: dict) -> str:
    requirement = entry.get("requirement", {})
    requirement_id = _requirement_id(requirement)
    covered_by = _assertion_candidate_tests(summary)
    candidate_tests = [
        {
            "test_id": item.get("test_id", ""),
            "file": item.get("file", ""),
            "traceability_verdict": item.get("verdict", ""),
            "line": item.get("line", ""),
            "matching_requirement_quotes": item.get("matching_requirement_quotes", []),
            "assertion_evidence_lines": item.get("assertion_evidence_lines", []),
            "verification_confidence": item.get("verification_confidence", ""),
            "traceability_reasoning": item.get("reasoning", ""),
            "retrieval_rank": item.get("retrieval_rank", ""),
            "rerank_score": item.get("rerank_score", ""),
            "safeguard_promoted": item.get("safeguard_promoted", False),
            "safeguard_reason": item.get("safeguard_reason"),
            "test_chunk_text": item.get("test_chunk_text", ""),
        }
        for item in covered_by
    ]
    supporting_code = [
        {
            "source_id": item.get("source_id", ""),
            "source_file": item.get("source_file", "") or item.get("file", ""),
            "function": item.get("function"),
            "implementation_confidence": item.get("implementation_confidence", ""),
            "reasoning": item.get("reasoning", ""),
            "retrieval_rank": item.get("retrieval_rank", ""),
            "rerank_score": item.get("rerank_score", ""),
            "source_chunk_text": item.get("source_chunk_text", ""),
        }
        for item in summary.get("implemented_by", [])
    ]
    supporting_code.extend([
        {
            "source_id": item.get("source_id", ""),
            "source_file": item.get("source_file", ""),
            "chunk_index": item.get("source_chunk_index", ""),
            "retrieval_rank": item.get("retrieval_rank", ""),
            "rerank_score": item.get("rerank_score", ""),
            "source_chunk_text": item.get("source_chunk_text", ""),
        }
        for item in summary.get("supporting_sources", [])
    ])

    return f"""[TARGET_REQUIREMENT]
requirement_id: {requirement_id}
file_id: {requirement.get("file_id", "")}
chunk_id: {requirement.get("chunk_index", "")}
section_title: {requirement.get("file", "")}
text: {requirement.get("text", "")}
[FROM_TRACEABILITY_MAPPER]
The rows below are trace links, not assertion proof.
verdict: {summary["verdict"]}
reasoning_summary: {summary["reasoning_summary"]}
covered_by:
{_json_block(summary.get("covered_by", []))}
candidate_test_judgments:
{_json_block(summary.get("candidate_test_judgments", []))}
verified_by_tests:
{_json_block(summary["verified_by_tests"])}
implemented_by:
{_json_block(summary.get("implemented_by", []))}
missing_scenarios:
{_json_block(summary["missing_scenarios"])}
gap_reason: {json.dumps(summary["gap_reason"], ensure_ascii=False)}
[CANDIDATE_TESTS]
{_json_block(candidate_tests)}
[OPTIONAL_SUPPORTING_CODE]
{_json_block(supporting_code)}

[ZERO_CANDIDATE_RULES]
- If candidate tests are empty, set assertion_verdict="no_assertion_evidence".
- If assertion lines are empty for all candidate tests, set assertion_verdict="no_assertion_evidence".
- When no assertion evidence exists, set evaluated_tests=[] and keep gap=true.

[OUTPUT_SCHEMA]
{{
  "assertion_gap_report": {{
    "requirement_id": "string",
    "assertion_verdict": "assertions_verified | partially_verified | no_assertion_evidence",
    "confidence_score": 0.0,
    "reasoning_summary": "2-3 sentences grounded in provided evidence",
    "evaluated_tests": [
      {{
        "test_id": "string",
        "file": "string or null",
        "line": 0,
        "assertion_text": "string",
        "assertion_status": "direct | partial | weak | missing",
        "reasoning": "one sentence grounded in requirement and assertion evidence"
      }}
    ],
    "missing_assertions": ["specific missing assertion behavior"],
    "standards_violations": ["specific rule violation from project standards context"],
    "gap": true,
    "gap_reason": "one sentence, or null when gap=false"
  }}
}}
"""


def _validate_assertion_evaluated_tests(
    requirement_id: str,
    candidate_tests: list[dict],
    evaluated_tests: list[dict],
) -> None:
    expected_ids = [
        str(item.get("test_id", "")).strip()
        for item in candidate_tests
        if str(item.get("test_id", "")).strip()
    ]

    if not candidate_tests:
        if evaluated_tests:
            raise ValueError(
                f"Assertion LLM returned evaluated_tests for {requirement_id} even though there were no candidate tests."
            )
        return

    actual_ids: list[str] = []

    for item in evaluated_tests:
        if not isinstance(item, dict):
            raise ValueError(
                f"Assertion LLM returned a non-object evaluated_tests entry for {requirement_id}."
            )
        test_id = str(item.get("test_id", "")).strip()
        if not test_id:
            raise ValueError(
                f"Assertion LLM returned an evaluated_tests row without test_id for {requirement_id}."
            )
        actual_ids.append(test_id)

    if actual_ids != expected_ids:
        raise ValueError(
            f"Assertion LLM returned invalid evaluated_tests for {requirement_id}: "
            f"expected exact test_id order {expected_ids!r}, got {actual_ids!r}"
        )


def _repair_assertion_evaluated_tests(
    requirement_id: str,
    candidate_tests: list[dict],
    evaluated_tests: list[dict],
) -> list[dict]:
    expected_by_id = {
        str(item.get("test_id", "")).strip(): item
        for item in candidate_tests
        if str(item.get("test_id", "")).strip()
    }

    if not candidate_tests:
        if evaluated_tests:
            raise ValueError(
                f"Assertion LLM returned evaluated_tests for {requirement_id} even though there were no candidate tests."
            )
        return []

    provided_by_id: dict[str, dict] = {}
    for item in evaluated_tests:
        if not isinstance(item, dict):
            raise ValueError(
                f"Assertion LLM returned a non-object evaluated_tests entry for {requirement_id}."
            )
        test_id = str(item.get("test_id", "")).strip()
        if not test_id:
            raise ValueError(
                f"Assertion LLM returned an evaluated_tests row without test_id for {requirement_id}."
            )
        if test_id not in expected_by_id or test_id in provided_by_id:
            continue
        provided_by_id[test_id] = item

    repaired: list[dict] = []
    for candidate in candidate_tests:
        test_id = str(candidate.get("test_id", "")).strip()
        if not test_id:
            continue
        provided = provided_by_id.get(test_id)
        if provided is not None:
            repaired.append(provided)
            continue

        repaired.append({
            "test_id": test_id,
            "file": candidate.get("file", ""),
            "line": 0,
            "assertion_text": "",
            "assertion_status": "missing",
            "reasoning": "No assertion evidence was returned for this trace-linked test.",
        })

    return repaired


def _normalized_assertion_summary_from_tests(
    evaluated_tests: list[dict],
    has_candidates: bool,
) -> tuple[str, float, str]:
    if not has_candidates:
        return (
            "no_assertion_evidence",
            0.0,
            "No traceability test candidates were available for assertion analysis.",
        )

    statuses = [str(item.get("assertion_status", "missing"))
                for item in evaluated_tests]
    if any(status == "direct" for status in statuses):
        return (
            "assertions_verified",
            1.0,
            "At least one traceability test contains direct assertion evidence for the requirement's core behavior.",
        )
    if any(status in {"partial", "weak"} for status in statuses):
        return (
            "partially_verified",
            0.5,
            "Only partial or weak assertion evidence was found across the traceability tests; full assertion verification is still missing.",
        )
    return (
        "no_assertion_evidence",
        0.0,
        "No assertion evidence was identified across the traceability tests for this requirement.",
    )


def _run_assertion_check(entry: dict, summary: dict, client, _log=None, log_label=None) -> dict:
    requirement = entry.get("requirement", {})
    requirement_id = _requirement_id(requirement)
    model = os.environ.get("OPENAI_LLM_MODEL", "gpt-5-mini")
    candidate_tests = [
        {
            "test_id": str(item.get("test_id", "")).strip(),
            "test_display_id": str(item.get("test_display_id", "")).strip(),
            "file": item.get("file", ""),
        }
        for item in _assertion_candidate_tests(summary)
    ]
    candidate_by_id = {
        item["test_id"]: item
        for item in candidate_tests
        if item["test_id"]
    }
    prompt = _build_assertion_prompt(entry, summary)

    print(f"[assertion →] {model} | requirement={requirement_id}")
    if _log and log_label:
        _log(f"LLM →  {log_label}  (assertion)")
    try:
        resp = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            temperature=1,
            messages=[
                {"role": "system", "content": _ASSERTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        payload = json.loads(resp.choices[0].message.content)
        report = payload.get("assertion_gap_report", {})
    except Exception as exc:
        print(f"[assertion ✗] requirement={requirement_id} | error={exc}")
        if _log and log_label:
            _log(f"LLM ✗  {log_label}  (assertion)  error={exc}")
        return {
            "requirement_id": requirement_id,
            "assertion_verdict": "no_assertion_evidence",
            "reasoning_summary": "Assertion LLM call failed.",
            "evaluated_tests": [
                {
                    "test_id": item["test_id"],
                    "test_display_id": item.get("test_display_id", ""),
                    "file": item.get("file", ""),
                    "line": 0,
                    "assertion_text": "",
                    "assertion_status": "missing",
                    "reasoning": "Assertion LLM call failed.",
                }
                for item in candidate_tests
            ],
            "missing_assertions": [],
            "standards_violations": [],
            "gap": True,
            "gap_reason": "Assertion LLM call failed.",
        }

    assertion_verdict = str(report.get(
        "assertion_verdict", "no_assertion_evidence")).strip()
    if assertion_verdict not in {
        "assertions_verified",
        "partially_verified",
        "no_assertion_evidence",
    }:
        raise ValueError(
            f"Assertion LLM returned invalid assertion_verdict for {requirement_id}: {assertion_verdict!r}"
        )

    confidence_score = report.get("confidence_score", 0.0)
    try:
        confidence_score = max(0.0, min(1.0, float(confidence_score)))
    except (TypeError, ValueError):
        confidence_score = 0.0

    raw_evaluated_tests = report.get("evaluated_tests", []) or []
    if not isinstance(raw_evaluated_tests, list):
        raise ValueError(
            f"Assertion LLM returned a non-list evaluated_tests payload for {requirement_id}."
        )

    repaired_evaluated_tests = _repair_assertion_evaluated_tests(
        requirement_id,
        candidate_tests,
        raw_evaluated_tests,
    )

    _validate_assertion_evaluated_tests(
        requirement_id,
        candidate_tests,
        repaired_evaluated_tests,
    )

    evaluated_tests: list[dict] = []
    for raw_item in repaired_evaluated_tests:
        raw_test_id = str(raw_item.get("test_id", "")).strip()
        candidate = candidate_by_id.get(raw_test_id)
        if not candidate:
            continue

        status = str(raw_item.get(
            "assertion_status", "missing")).strip().lower()
        if status not in _ASSERTION_STATUS_MAP:
            raise ValueError(
                f"Assertion LLM returned invalid assertion_status for {requirement_id}, test_id={raw_test_id}: {status!r}"
            )
        line = raw_item.get("line", 0)
        try:
            line = int(line)
        except (TypeError, ValueError):
            line = 0
        evaluated_tests.append({
            "test_id": raw_test_id,
            "test_display_id": str(raw_item.get("test_display_id", "")).strip()
            or str(candidate.get("test_display_id", "")).strip(),
            "file": raw_item.get("file") or candidate["file"],
            "line": line,
            "assertion_text": str(raw_item.get("assertion_text", "")),
            "assertion_status": status,
            "reasoning": str(raw_item.get("reasoning", "")),
        })

    if not candidate_tests and assertion_verdict != "no_assertion_evidence":
        raise ValueError(
            f"Assertion LLM returned verdict={assertion_verdict!r} for {requirement_id} even though there were no candidate tests."
        )

    if not evaluated_tests and assertion_verdict == "assertions_verified":
        raise ValueError(
            f"Assertion LLM returned assertions_verified for {requirement_id} without any evaluated_tests evidence."
        )

    reasoning_summary = str(report.get("reasoning_summary", "")).strip()
    if not reasoning_summary:
        _, _, reasoning_summary = _normalized_assertion_summary_from_tests(
            evaluated_tests,
            bool(candidate_tests),
        )

    gap = assertion_verdict != "assertions_verified"
    gap_reason = report.get("gap_reason")
    if not gap:
        gap_reason = None

    normalized = {
        "requirement_id": requirement_id,
        "assertion_verdict": assertion_verdict,
        "confidence_score": confidence_score,
        "reasoning_summary": reasoning_summary,
        "evaluated_tests": evaluated_tests,
        "missing_assertions": [
            str(item) for item in (report.get("missing_assertions", []) or [])
        ],
        "standards_violations": [
            str(item) for item in (report.get("standards_violations", []) or [])
        ],
        "gap": gap,
        "gap_reason": gap_reason,
    }

    print(
        f"[assertion ←] requirement={requirement_id} | verdict={normalized['assertion_verdict']} "
        f"| evaluated_tests={len(normalized['evaluated_tests'])}"
    )
    if _log and log_label:
        _log(
            f"LLM ←  {log_label}  (assertion)  "
            f"verdict={normalized['assertion_verdict']}  "
            f"evaluated={len(normalized['evaluated_tests'])}"
        )
    return normalized


def _build_assertion_row(
    requirement: dict,
    assertion_report: dict,
    evaluated_test: dict,
    generated_at: str,
) -> dict:
    req_file = requirement.get("file", "")
    req_chunk = requirement.get("chunk_index", "")
    test_file = evaluated_test.get("file") or ""
    verdict, confidence = _ASSERTION_STATUS_MAP.get(
        evaluated_test.get("assertion_status", "missing"),
        ("rejected", "weak"),
    )
    return {
        "requirement_id": f"{req_file}::chunk{req_chunk}",
        "verdict": verdict,
        "test_id": str(evaluated_test.get("test_id", "")),
        "test_display_id": str(evaluated_test.get("test_display_id", "")),
        "verdict_confidence": confidence,
        "reasoning": evaluated_test.get("reasoning", "") or assertion_report.get("reasoning_summary", ""),
        "requirement_file": req_file,
        "requirement_chunk_index": req_chunk,
        "test_file": test_file,
        "test_chunk_index": "",
        "retrieval_rank": "",
        "rerank_score": "",
        "candidate_text": evaluated_test.get("assertion_text", ""),
        "assertion_status": evaluated_test.get("assertion_status", "missing"),
        "assertion_verdict": assertion_report.get("assertion_verdict", ""),
        "confidence_score": assertion_report.get("confidence_score", 0.0),
        "reasoning_summary": assertion_report.get("reasoning_summary", ""),
        "gap": assertion_report.get("gap", True),
        "gap_reason": assertion_report.get("gap_reason"),
        "assertion_line": evaluated_test.get("line", 0),
        "missing_assertions": assertion_report.get("missing_assertions", []),
        "standards_violations": assertion_report.get("standards_violations", []),
        "generated_at": generated_at,
    }


def _collect_generation_clusters(
    assertion_report: dict,
    traceability_report: dict,
    rerank_report: Optional[dict],
) -> tuple[list[dict], list[str]]:
    traceability_map = {
        _requirement_id(entry.get("requirement", {})): entry
        for entry in traceability_report.get("traceability", [])
    }
    rerank_map = {}
    if rerank_report:
        rerank_map = {
            _requirement_id(entry.get("requirement", {})): entry
            for entry in rerank_report.get("traceability", [])
        }

    requirement_reports_by_req = {
        str(report.get("requirement_id", "")).strip(): report
        for report in assertion_report.get("requirements", [])
        if str(report.get("requirement_id", "")).strip()
    }

    warnings: list[str] = []
    clusters_by_key: dict[str, dict] = {}

    for row in assertion_report.get("assertions", []):
        req_id = str(row.get("requirement_id", "")).strip()
        test_id = str(row.get("test_id", "")).strip()
        assertion_status = str(row.get("assertion_status", "")).strip().lower()

        if not req_id or assertion_status not in {"partial", "weak", "missing"}:
            continue
        if not test_id:
            warnings.append(
                f"Skipped failing assertion row for {req_id} because test_id was empty."
            )
            continue

        trace_entry = traceability_map.get(req_id)
        rerank_entry = rerank_map.get(req_id)
        requirement = trace_entry.get("requirement", {}) if trace_entry else {}
        requirement_report = requirement_reports_by_req.get(req_id, {})

        missing_assertions = _unique_preserve_order([
            str(item)
            for item in (row.get("missing_assertions", []) or [])
            if str(item).strip()
        ])
        reasoning_summaries = _unique_preserve_order([
            str(item).strip()
            for item in [
                row.get("reasoning_summary", ""),
                requirement_report.get("reasoning_summary", ""),
                row.get("reasoning", ""),
            ]
            if str(item).strip()
        ])
        gap_reason = (
            str(row.get("gap_reason", "")).strip()
            or str(requirement_report.get("gap_reason", "")).strip()
            or str(row.get("reasoning", "")).strip()
            or (str(missing_assertions[0]) if missing_assertions else "")
            or "Assertion gap requires new test coverage."
        )

        source_test_file = str(row.get("test_file", "")).strip()
        # Grouped key:
        # - current: one cluster per requirement + source test file
        # - if you want one cluster per requirement only, change this to:
        #   group_key = _normalize_gap_text(req_id)
        group_key = _normalize_gap_text(
            f"{req_id}|{source_test_file or 'no_test_file'}"
        )

        cluster = clusters_by_key.get(group_key)
        if cluster is None:
            cluster = {
                "gap_key": group_key,
                "gap_reason": gap_reason,
                "requirement_ids": [req_id],
                "requirements": [{
                    "requirement_id": req_id,
                    "file": requirement.get(
                        "file",
                        req_id.split("::chunk")[
                            0] if "::chunk" in req_id else req_id,
                    ),
                    "chunk_index": requirement.get("chunk_index", ""),
                    "text": requirement.get("text", ""),
                }],
                "requirement_reports": [requirement_report] if requirement_report else [],
                "assertion_rows": [row],
                "traceability_entries": [trace_entry] if trace_entry else [],
                "rerank_entries": [rerank_entry] if rerank_entry else [],
                "warnings": [],
                "missing_assertions": missing_assertions,
                "reasoning_summaries": reasoning_summaries,
                "source_test_id": test_id,
                "source_test_file": source_test_file,
                "source_test_ids": [test_id],
                "source_test_files": [source_test_file] if source_test_file else [],
                "assertion_status": assertion_status,
            }
            if not trace_entry:
                cluster["warnings"].append(
                    f"No saved traceability entry found for {req_id}."
                )
            clusters_by_key[group_key] = cluster
            continue

        if req_id not in cluster["requirement_ids"]:
            cluster["requirement_ids"].append(req_id)

        existing_req_ids = {
            str(item.get("requirement_id", "")).strip()
            for item in cluster.get("requirements", [])
            if isinstance(item, dict)
        }
        if req_id not in existing_req_ids:
            cluster["requirements"].append({
                "requirement_id": req_id,
                "file": requirement.get(
                    "file",
                    req_id.split("::chunk")[
                        0] if "::chunk" in req_id else req_id,
                ),
                "chunk_index": requirement.get("chunk_index", ""),
                "text": requirement.get("text", ""),
            })

        existing_report_ids = {
            str(item.get("requirement_id", "")).strip()
            for item in cluster.get("requirement_reports", [])
            if isinstance(item, dict)
        }
        if requirement_report and req_id not in existing_report_ids:
            cluster["requirement_reports"].append(requirement_report)

        existing_trace_ids = {
            _requirement_id(item.get("requirement", {}))
            for item in cluster.get("traceability_entries", [])
            if isinstance(item, dict)
        }
        if trace_entry and req_id not in existing_trace_ids:
            cluster["traceability_entries"].append(trace_entry)

        existing_rerank_ids = {
            _requirement_id(item.get("requirement", {}))
            for item in cluster.get("rerank_entries", [])
            if isinstance(item, dict)
        }
        if rerank_entry and req_id not in existing_rerank_ids:
            cluster["rerank_entries"].append(rerank_entry)

        existing_assertion_rows = {
            (
                str(item.get("test_id", "")).strip(),
                str(item.get("assertion_status", "")).strip().lower(),
                str(item.get("reasoning", "")).strip(),
            )
            for item in cluster.get("assertion_rows", [])
            if isinstance(item, dict)
        }
        row_key = (
            test_id,
            assertion_status,
            str(row.get("reasoning", "")).strip(),
        )
        if row_key not in existing_assertion_rows:
            cluster["assertion_rows"].append(row)

        cluster["missing_assertions"] = _unique_preserve_order(
            list(cluster.get("missing_assertions", [])) + missing_assertions
        )
        cluster["reasoning_summaries"] = _unique_preserve_order(
            list(cluster.get("reasoning_summaries", [])) + reasoning_summaries
        )

        if gap_reason:
            combined_gap_reasons = _unique_preserve_order([
                str(cluster.get("gap_reason", "")).strip(),
                gap_reason,
            ])
            cluster["gap_reason"] = " | ".join(
                item for item in combined_gap_reasons if str(item).strip()
            )

        if test_id and test_id not in cluster.get("source_test_ids", []):
            cluster.setdefault("source_test_ids", []).append(test_id)

        if source_test_file and source_test_file not in cluster.get("source_test_files", []):
            cluster.setdefault("source_test_files", []
                               ).append(source_test_file)

        status_rank = {"missing": 3, "weak": 2, "partial": 1}
        current_rank = status_rank.get(assertion_status, 0)
        existing_rank = status_rank.get(
            str(cluster.get("assertion_status", "")).strip().lower(), 0)
        if current_rank > existing_rank:
            cluster["assertion_status"] = assertion_status

    clusters = list(clusters_by_key.values())

    def _cluster_sort_key(item: dict) -> tuple[str, int, str, str]:
        primary = item["requirements"][0]
        chunk_index = primary.get("chunk_index", 0)
        try:
            chunk_value = int(chunk_index)
        except (TypeError, ValueError):
            chunk_value = 0
        return (
            str(primary.get("file", "")),
            chunk_value,
            str(item.get("source_test_file", "")),
            item["gap_key"],
        )

    clusters.sort(key=_cluster_sort_key)
    return clusters, warnings


def _detect_cluster_framework(cluster: dict) -> tuple[Optional[dict], list[dict], list[dict], list[dict], list[str]]:
    scored = Counter()
    evidence_by_framework: dict[str, list[dict]] = defaultdict(list)
    warnings: list[str] = []

    def _add_evidence(source: str, weight: int, file_name: str, text: str, rank: object, extra: Optional[dict] = None) -> None:
        framework_key = _framework_from_candidate(file_name, text)
        if not framework_key:
            return
        scored[framework_key] += weight
        evidence_by_framework[framework_key].append({
            "source": source,
            "weight": weight,
            "file_name": file_name,
            "text": text,
            "rank": rank if isinstance(rank, int) else 9999,
            **(extra or {}),
        })

    for row in cluster.get("assertion_rows", []):
        file_name = str(row.get("test_file") or str(
            row.get("test_id", "")).split("::chunk")[0])
        _add_evidence(
            "assertion",
            3,
            file_name,
            str(row.get("candidate_text", "")),
            0,
            {
                "test_id": row.get("test_id", ""),
                "reasoning": row.get("reasoning", ""),
                "verdict_confidence": row.get("verdict_confidence", ""),
            },
        )

    for entry in cluster.get("traceability_entries", []):
        details = extract_requirement_traceability_details(entry)
        for item in details.get("verified_tests", []):
            _add_evidence(
                "traceability",
                2,
                str(item.get("file", "")),
                str(item.get("test_chunk_text", "")),
                item.get("retrieval_rank", 9999),
                {
                    "test_id": item.get("test_id", ""),
                    "confidence": item.get("verification_confidence", ""),
                    "reasoning": item.get("reasoning", ""),
                },
            )

    for entry in cluster.get("rerank_entries", []):
        for item in entry.get("final_candidates", {}).get("tests", []):
            _add_evidence(
                "rerank",
                1,
                str(item.get("file_name", "")),
                str(item.get("text", "")),
                item.get("rank", 9999),
                {
                    "test_id": f"{item.get('file_name', '')}::chunk{item.get('chunk_index', '')}",
                },
            )

    if not scored:
        fallback_reason = (
            "No supporting test evidence was available to detect a target framework. "
            "Falling back to pytest/Python generation."
        )
        warnings.append(fallback_reason)
        best_key = "pytest_python"
        framework_info = {
            "key": best_key,
            **_FRAMEWORK_HINTS[best_key],
            "fallback_mode": "python_no_context",
            "fallback_reason": fallback_reason,
        }
    else:
        best_key = sorted(
            scored,
            key=lambda key: (-scored[key], key),
        )[0]
        framework_info = {
            "key": best_key,
            **_FRAMEWORK_HINTS[best_key],
        }

    exemplar_tests = []
    seen_exemplar_keys = set()
    for item in sorted(
        evidence_by_framework[best_key],
        key=lambda row: (-row["weight"], row["rank"], row["file_name"]),
    ):
        exemplar_key = (item["file_name"], _trim_text(item["text"], 180))
        if exemplar_key in seen_exemplar_keys:
            continue
        seen_exemplar_keys.add(exemplar_key)
        exemplar_tests.append({
            "source": item["source"],
            "file": item["file_name"],
            "test_id": item.get("test_id", ""),
            "reasoning": item.get("reasoning", ""),
            "status": item.get("status", ""),
            "confidence": item.get("confidence", ""),
            "text": _trim_text(item["text"], 900),
        })
        if len(exemplar_tests) >= 6:
            break

    verified_tests = []
    seen_verified = set()
    for entry in cluster.get("traceability_entries", []):
        details = extract_requirement_traceability_details(entry)
        for item in details.get("verified_tests", []):
            file_name = str(item.get("file", ""))
            if _framework_from_candidate(file_name, item.get("test_chunk_text", "")) != best_key:
                continue
            test_id = str(item.get("test_id", "")).strip()
            if test_id in seen_verified:
                continue
            seen_verified.add(test_id)
            verified_tests.append({
                "test_id": test_id,
                "file": file_name,
                "line": item.get("line", ""),
                "rank": item.get("retrieval_rank", ""),
                "verification_confidence": item.get("verification_confidence", ""),
                "traceability_reasoning": item.get("reasoning", ""),
                "matching_requirement_quotes": item.get("matching_requirement_quotes", []),
                "assertion_evidence_lines": item.get("assertion_evidence_lines", []),
                "text": _trim_text(item.get("test_chunk_text", ""), 900),
            })
            if len(verified_tests) >= 8:
                break
        if len(verified_tests) >= 8:
            break

    supporting_sources = []
    seen_sources = set()
    for entry in cluster.get("traceability_entries", []):
        for item in entry.get("final_candidates", {}).get("sources", []):
            source_id = f"{item.get('file_name', '')}::chunk{item.get('chunk_index', '')}"
            if source_id in seen_sources:
                continue
            seen_sources.add(source_id)
            supporting_sources.append({
                "source_id": source_id,
                "file": item.get("file_name", ""),
                "rank": item.get("rank", ""),
                "rerank_score": item.get("rerank_score", ""),
                "text": _trim_text(item.get("text", ""), 900),
            })
            if len(supporting_sources) >= 6:
                break
        if len(supporting_sources) >= 6:
            break

    assertion_rows = []
    seen_rows = set()
    for row in cluster.get("assertion_rows", []):
        row_key = (row.get("test_id", ""), row.get("reasoning", ""))
        if row_key in seen_rows:
            continue
        seen_rows.add(row_key)
        assertion_rows.append({
            "test_id": row.get("test_id", ""),
            "test_file": row.get("test_file", ""),
            "assertion_status": row.get("assertion_status", ""),
            "assertion_verdict": row.get("assertion_verdict", ""),
            "verdict_confidence": row.get("verdict_confidence", ""),
            "reasoning": row.get("reasoning", ""),
            "candidate_text": _trim_text(row.get("candidate_text", ""), 600),
        })
        if len(assertion_rows) >= 8:
            break

    return framework_info, exemplar_tests, verified_tests, supporting_sources, warnings


def _build_generated_test_prompt(
    framework_info: dict,
    output_filename: str,
    clusters: list[dict],
) -> str:
    cluster_blocks = []
    for cluster in clusters:
        cluster_blocks.append({
            "gap_key": cluster["gap_key"],
            "gap_reason": cluster["gap_reason"],
            "preferred_function_name": cluster.get("preferred_function_name", ""),
            "requirement_ids": cluster["requirement_ids"],
            "requirements": cluster["requirements"],
            "missing_assertions": cluster.get("missing_assertions", []),
            "reasoning_summaries": cluster.get("reasoning_summaries", []),
            "assertion_rows": cluster.get("assertion_rows_for_prompt", []),
            "verified_tests": cluster.get("verified_tests_for_prompt", []),
            "supporting_code": cluster.get("supporting_sources_for_prompt", []),
        })

    exemplars = _unique_preserve_order([
        exemplar
        for cluster in clusters
        for exemplar in cluster.get("exemplar_tests_for_prompt", [])
    ])[:10]
    fallback_mode = bool(framework_info.get("fallback_mode"))
    fallback_reason = str(framework_info.get("fallback_reason", "")).strip()
    style_rule = (
        "Preserve the style, naming conventions, helper usage, imports, and assertion patterns exactly as shown in the exemplars."
        if exemplars
        else "No project test exemplars were provided. Generate a pytest-style Python test using only `pytest` and the Python standard library."
    )
    fallback_rule = (
        "11. Python fallback mode is active because no framework context was detected. Do not import or call project-specific modules unless they are explicitly present in the supporting code. If no concrete callable API is visible, generate a clearly marked pytest scaffold with honest TODO comments or `pytest.skip(...)` rather than inventing unsupported wiring."
        if fallback_mode
        else ""
    )

    return f"""[DETECTED_FRAMEWORK]
framework: {framework_info.get("framework", "")}
language: {framework_info.get("language", "")}
framework_key: {framework_info.get("key", "")}
target_filename: {output_filename}
fallback_mode: {"python_no_context" if fallback_mode else "none"}
fallback_reason: {fallback_reason or "—"}

## Rules (Strict)
1. Generate **exactly one** test function or framework‑equivalent test block **per gap group**.
2. {style_rule}
3. Use the provided `preferred_function_name` as the exact `function_name`.
4. The `function_name` must exactly match `preferred_function_name` and follow the `filename_missing_test_N` pattern.
5. The `code` field must declare or use the same `function_name` that you return in the JSON (self‑consistency).
6. The `shared_prelude` must contain only shared imports, includes, fixtures, or helpers that are needed **once for the entire generated file**.
7. The `code` field must contain **only** the individual test function or test block for that gap group (no duplicate imports or global setup).
8. The `requirement_ids` and `gap_key` must match the provided gap groups exactly.
9. If one generated test covers multiple requirements within the same gap group, include all those requirement IDs in the `requirement_ids` array.
10. **Do not invent** unsupported APIs, helper functions, constants, or behaviour unless they are already grounded in the exemplars or supporting code.
{fallback_rule}

[GAP_GROUPS]
{_json_block(cluster_blocks)}

[EXEMPLAR_TESTS]
{_json_block(exemplars)}

[OUTPUT_SCHEMA]
{{
  "generated_test_file": {{
    "framework": "{framework_info.get('framework', '')}",
    "language": "{framework_info.get('language', '')}",
    "filename": "{output_filename}",
    "shared_prelude": "string",
    "test_functions": [
      {{
        "function_name": "string",
        "requirement_ids": ["string"],
        "gap_key": "string",
        "reasoning_basis": "1-2 sentences grounded in the provided context",
        "code": "string"
      }}
    ]
  }}
}}
"""


def _run_generated_test_file_generation(
    framework_info: dict,
    output_filename: str,
    clusters: list[dict],
    client,
) -> dict:
    model = os.environ.get("OPENAI_LLM_MODEL", "gpt-5-mini")
    prompt = _build_generated_test_prompt(
        framework_info, output_filename, clusters)
    print(
        f"[testgen ->] {model} | framework={framework_info.get('framework', '')} "
        f"| file={output_filename} | groups={len(clusters)}"
    )
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        temperature=1,
        messages=[
            {"role": "system", "content": _TEST_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    payload = json.loads(resp.choices[0].message.content)
    generated_file = payload.get("generated_test_file", {})
    shared_prelude = str(generated_file.get("shared_prelude", ""))
    normalized_tests = []
    for item in generated_file.get("test_functions", []) or []:
        normalized_tests.append({
            "function_name": str(item.get("function_name", "")).strip(),
            "requirement_ids": [str(req_id) for req_id in (item.get("requirement_ids", []) or []) if str(req_id).strip()],
            "gap_key": _normalize_gap_text(item.get("gap_key", "")),
            "reasoning_basis": str(item.get("reasoning_basis", "")).strip(),
            "code": str(item.get("code", "")).strip(),
        })

    print(
        f"[testgen <-] framework={framework_info.get('framework', '')} "
        f"| file={output_filename} | generated_tests={len(normalized_tests)}"
    )
    return {
        "framework": str(generated_file.get("framework", framework_info.get("framework", ""))).strip() or framework_info.get("framework", ""),
        "language": str(generated_file.get("language", framework_info.get("language", ""))).strip() or framework_info.get("language", ""),
        "filename": output_filename,
        "shared_prelude": shared_prelude,
        "test_functions": normalized_tests,
    }


def _split_requirement_id(value: object) -> tuple[str, str]:
    raw = str(value or "").strip()
    if "::chunk" in raw:
        req_id, chunk_id = raw.rsplit("::chunk", 1)
        return req_id, chunk_id
    return raw, ""


def _csv_requirement_id(raw_id: str, text: str) -> str:
    m = re.search(
        r"\b(?:rq|req|requirement)\s*[-_:]?\s*(\d+(?:\.\d+)*)\b", str(text or ""), re.I)
    if m:
        return f"RQ{m.group(1)}"
    base = str(raw_id or "").split("::chunk", 1)[0]
    return Path(base).stem or base or "—"


def _csv_test_value(item: dict, entry: dict) -> str:
    raw_file = str(item.get("file", "")).strip()
    raw_test_id = str(item.get("test_id", "")).strip()
    raw_test_id_base = raw_test_id.rsplit(
        "::chunk", 1)[0] if "::chunk" in raw_test_id else raw_test_id

    test_text = str(item.get("test_chunk_text", "")).strip()
    candidate_tests = entry.get("final_candidates", {}).get("tests", []) or []

    # 1) Resolve by exact test_id first (prevents cross-row mismatches when many
    #    candidates come from the same file, e.g., test_cases.txt).
    if not test_text and raw_test_id:
        for cand in candidate_tests:
            cand_id = f"{cand.get('file_name', '')}::chunk{cand.get('chunk_index', '')}"
            if raw_test_id == cand_id:
                test_text = str(cand.get("text", "") or "")
                break

    # 2) Only fall back to file-level lookup when there is exactly one candidate
    #    for that file; otherwise we cannot safely disambiguate.
    if not test_text and raw_file:
        same_file = [
            cand
            for cand in candidate_tests
            if raw_file == str(cand.get("file_name", "")).strip()
        ]
        if len(same_file) == 1:
            test_text = str(same_file[0].get("text", "") or "")

    spec_exts = {".txt", ".md", ".rst", ".text",
                 ".markdown", ".pdf", ".doc", ".docx"}
    suffix = Path(raw_file).suffix.lower()

    if suffix in spec_exts:
        m = re.search(r"\b(TC\s*[-_ ]?\s*\d+)\b", test_text, re.I)
        if m:
            return re.sub(r"[\s_-]+", "", m.group(1)).upper()
        m = re.search(r"\b(TC\s*[-_ ]?\s*\d+)\b", raw_test_id_base, re.I)
        if m:
            return re.sub(r"[\s_-]+", "", m.group(1)).upper()
        return raw_test_id_base or raw_file or "—"

    return raw_test_id_base or raw_file or "—"


def _normalize_traceability_verdict(verdict: str) -> str:
    v = str(verdict or "").strip().lower().replace(" ", "_")
    if v in {"covered", "full"}:
        return "covered"
    if v in {"partially_covered", "partial", "partially-covered"}:
        return "partially_covered"
    if v in {"not_covered", "not-covered", "none"}:
        return "not_covered"
    return v


def _csv_join_unique_strings(values: list[object], empty: str = "—") -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return " | ".join(ordered) if ordered else empty


def _csv_compact_text(value: object, empty: str = "—") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or empty


def _csv_requirement_chunks_value(requirement: dict) -> str:
    parts: list[str] = []
    for chunk in requirement.get("requirement_chunks", []) or []:
        if not isinstance(chunk, dict):
            continue
        label = str(chunk.get("requirement_chunk_label", "")).strip()
        verdict = _normalize_traceability_verdict(
            str(chunk.get("traceability_verdict", "")).strip()
        )
        if label and verdict:
            parts.append(f"{label}:{verdict}")
        elif label:
            parts.append(label)
    return _csv_join_unique_strings(parts)


def _csv_evidence_chunks_value(artifact: dict) -> str:
    parts: list[str] = []
    for evidence in artifact.get("evidence_chunks", []) or []:
        if not isinstance(evidence, dict):
            continue
        req_chunk_label = str(evidence.get(
            "requirement_chunk_label", "")).strip()
        test_chunk_id = str(evidence.get("chunk_id", "")).strip()
        if req_chunk_label and test_chunk_id:
            parts.append(f"{req_chunk_label}->{test_chunk_id}")
        elif test_chunk_id:
            parts.append(test_chunk_id)
        elif req_chunk_label:
            parts.append(req_chunk_label)
    return _csv_join_unique_strings(parts)


def _traceability_report_to_llm_csv(report: dict, filename: str) -> StreamingResponse:
    buf = io.StringIO()
    requirement_view = build_traceability_view(report)
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "Requirement Id",
            "Description",
            "Test",
            "Verdict",
            "Verdict Confidence",
            "Reason",
            "Supporting Files"
        ],
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()

    for requirement in requirement_view.get("requirements", []):
        if not isinstance(requirement, dict):
            continue

        raw_requirement_id = str(requirement.get("requirement_id", "")).strip()
        description = _csv_compact_text(
            requirement.get("requirement_text", ""))
        req_display_id = (
            str(requirement.get("requirement_display_id", "")).strip()
            or _csv_requirement_id(raw_requirement_id, description)
        )
        requirement_chunks_value = _csv_requirement_chunks_value(requirement)
        requirement_verdict = _normalize_traceability_verdict(
            requirement.get("traceability_verdict", "")
        )
        requirement_reasoning = (
            _csv_compact_text(requirement.get(
                "requirement_reasoning", ""), empty="")
            or _csv_compact_text(requirement.get("traceability_gap_reason", ""), empty="")
            or "—"
        )

        supporting_files = _csv_join_unique_strings([
            artifact.get("source_file", "")
            for artifact in (requirement.get("supporting_source_artifacts", []) or [])
            if isinstance(artifact, dict)
        ])

        candidate_artifacts = requirement.get(
            "candidate_test_artifacts", []) or []
        if not candidate_artifacts:
            writer.writerow({
                "Requirement Id": req_display_id,
                "Description": description,
                "Test": "—",
                "Requirement Verdict": requirement_verdict or "—",
                "Verdict": "—",
                "Verdict Confidence": "—",
                "Reason": requirement_reasoning,
                "Supporting Files": supporting_files,
            })
            continue

        for artifact in candidate_artifacts:
            if not isinstance(artifact, dict):
                continue
            writer.writerow({
                "Requirement Id": req_display_id,
                "Description": description,
                "Test": str(artifact.get("artifact_label", "")).strip()
                or str(artifact.get("test_file", "")).strip()
                or "—",
                "Requirement Verdict": requirement_verdict or "—",
                "Verdict": _normalize_traceability_verdict(artifact.get("verdict", "")) or "—",
                "Verdict Confidence": str(artifact.get("verification_confidence", "")).strip() or "—",
                "Reason": _csv_join_unique_strings(
                    [
                        _csv_compact_text(item, empty="")
                        for item in (artifact.get("reasoning_summaries", []) or [])
                    ],
                    empty=requirement_reasoning,
                ),
                "Supporting Files": supporting_files,
            })

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


def _assertion_report_to_presentation_csv(report: dict, filename: str) -> StreamingResponse:
    status_order = {
        "direct": 0,
        "partial": 1,
        "weak": 2,
        "missing": 3,
        "": 4,
    }
    confidence_order = {
        "full": 0,
        "partial": 1,
        "weak": 2,
        "": 3,
    }

    traceability_text_by_id: dict[str, str] = {}
    traceability_test_label_by_id: dict[str, str] = {}
    traceability_report = load_traceability_report()
    if traceability_report:
        for entry in traceability_report.get("traceability", []) or []:
            requirement = entry.get("requirement", {}) or {}
            req_id = _requirement_id(requirement)
            req_text = str(requirement.get("text", "")).strip()
            if req_id and req_text and req_id not in traceability_text_by_id:
                traceability_text_by_id[req_id] = req_text
            details = extract_requirement_traceability_details(entry)
            for item in details.get("candidate_test_judgments", []) or []:
                test_id = str(item.get("test_id", "")).strip()
                test_display_id = str(item.get("test_display_id", "")).strip()
                if test_id and test_display_id and test_id not in traceability_test_label_by_id:
                    traceability_test_label_by_id[test_id] = test_display_id

    presentation_rows: list[dict] = []
    for requirement_report in report.get("requirements", []):
        # requirement_id = str(requirement_report.get(
        #     "requirement_id", "")).strip() or "—"
        raw_requirement_id = str(
            requirement_report.get("requirement_id", "")).strip()
        description = (
            str(requirement_report.get("requirement_text", "")).strip()
            or traceability_text_by_id.get(raw_requirement_id, "")
        )
        _, req_chunk_id = _split_requirement_id(raw_requirement_id)

        req_display_id = _csv_requirement_id(
            raw_requirement_id,
            description)

        requirement_reasoning = (
            str(requirement_report.get("reasoning_summary", "")).strip()
            or str(requirement_report.get("gap_reason", "")).strip()
            or "—"
        )
        evaluated_tests = requirement_report.get("evaluated_tests", []) or []

        if not evaluated_tests:
            presentation_rows.append({
                "Requirement Id": req_display_id,
                "Chunk": raw_requirement_id or "—",
                "Description": description,
                "Test": "NO_TEST_CASE",
                "Verdict": requirement_report.get("assertion_verdict", "no_assertion_evidence"),
                "Confidence": "weak",
                "Gap": requirement_report.get("gap", True),
                "Reasoning": requirement_reasoning,
            })
            continue

        sorted_tests = sorted(
            evaluated_tests,
            key=lambda item: (
                status_order.get(str(item.get("assertion_status", "")), 4),
                confidence_order.get(
                    _ASSERTION_STATUS_MAP.get(
                        str(item.get("assertion_status", "missing")),
                        ("rejected", "weak"),
                    )[1],
                    3,
                ),
                str(item.get("file", "") or ""),
                str(item.get("test_id", "") or ""),
            ),
        )

        for index, item in enumerate(sorted_tests):
            status = str(item.get("assertion_status",
                         "missing")).strip().lower()
            _, confidence = _ASSERTION_STATUS_MAP.get(
                status, ("rejected", "weak"))

            presentation_rows.append({
                "Requirement Id": req_display_id,
                "Chunk": raw_requirement_id or "—",
                "Description": description,
                "Test": str(item.get("test_display_id", "")).strip()
                or traceability_test_label_by_id.get(str(item.get("test_id", "")).strip(), "")
                or _csv_test_value(item, requirement_report),
                "Verdict": requirement_report.get("assertion_verdict", "no_assertion_evidence"),
                "Confidence": confidence,
                "Gap": requirement_report.get("gap", True),
                "Reasoning": str(item.get("reasoning", "")).strip() or requirement_reasoning,
            })

    presentation_rows.sort(
        key=lambda row: (
            str(row.get("Requirement Id", "")),
            status_order.get(str(row.get("Verdict", "")), 4),
            confidence_order.get(str(row.get("Confidence", "")), 3),
            str(row.get("Test", "")),
        ),
    )

    buf = io.StringIO()
    fieldnames = [
        "Requirement Id",
        "Chunk",
        "Description",
        "Test",
        "Verdict",
        "Confidence",
        "Gap",
        "Reasoning",
    ]
    writer = csv.DictWriter(
        buf,
        fieldnames=fieldnames,
        lineterminator="\n",
    )
    writer.writeheader()
    for row in presentation_rows:
        writer.writerow(row)

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


async def _run_stage3_requirement(
    idx: int,
    entry: dict,
    traceability: list[dict],
    job: dict,
    _log,
    total: int,
    total_requirements: int,
    rerank_generated_at: str,
    llm_client,
    loop,
    checkpoint_lock: asyncio.Lock,
    semaphore: asyncio.Semaphore,
) -> None:
    requirement = entry["requirement"]
    label = _requirement_label(requirement, idx)

    async with semaphore:
        tests_reranked = entry.get("final_candidates", {}).get("tests", [])
        total_tests = len(tests_reranked)

        _log(
            f"[{idx + 1}/{total}]  Stage 3  →  {label}  "
            f"LLM auditing {total_tests} test candidate{'s' if total_tests != 1 else ''} together"
        )
        job["current"] = f"LLM auditing {label}"

        try:
            requirement_report = await loop.run_in_executor(
                None,
                lambda current_entry=entry, current_label=label: _run_requirement_traceability_report(
                    current_entry,
                    llm_client,
                    _log,
                    current_label,
                ),
            )
            entry["traceability_report"] = requirement_report
            entry.pop("traceability_error", None)
            traceability_mapper = _derive_traceability_summary(entry)

            _log(
                f"[{idx + 1}/{total}]  Stage 3 ✓  {label}  "
                f"verified_tests={len(traceability_mapper.get('verified_tests', []))}  "
                f"implemented_by={len(traceability_mapper.get('implemented_by', []))}  "
                f"verdict={traceability_mapper.get('verdict', '')}"
            )
        except Exception as exc:
            entry.pop("traceability_report", None)
            entry["traceability_error"] = {
                "message": str(exc),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
            _log(
                f"[{idx + 1}/{total}]  Stage 3 ⚠  {label}  error={exc}"
            )
        finally:
            async with checkpoint_lock:
                progress = _traceability_progress_counts(
                    traceability,
                    total_requirements,
                )
                job["progress"] = (
                    progress["completed_requirements"]
                    + progress["failed_requirements"]
                )
                job["current"] = (
                    f"Stage 3 running — "
                    f"{job['progress']}/{total_requirements} requirements finalized"
                )
                _save_traceability_checkpoint(
                    traceability,
                    total_requirements,
                    rerank_generated_at,
                )


async def _run_assertion_requirement(
    idx: int,
    entry: dict,
    job: dict,
    _log,
    total: int,
    llm_client,
    loop,
    semaphore: asyncio.Semaphore,
    progress_lock: asyncio.Lock,
    requirement_reports_by_index: list[dict | None],
    rows_by_index: list[list[dict]],
) -> None:
    requirement = entry.get("requirement", {})
    label = _requirement_label(requirement, idx)
    traceability_summary = _resolve_assertion_traceability_summary(entry)

    async with semaphore:
        _log(
            f"[{idx + 1}/{total}]  Assertion  →  {label}  "
            f"LLM analyzing {len(_assertion_candidate_tests(traceability_summary))} trace-linked tests"
        )
        job["current"] = f"LLM analyzing {label}"
        _log(f"LLM →  {label}  (assertion)")

        assertion_result = await loop.run_in_executor(
            None,
            lambda current_entry=entry, current_summary=traceability_summary: _run_assertion_check(
                current_entry,
                current_summary,
                llm_client,
            ),
        )

        _log(
            f"LLM ←  {label}  (assertion)  "
            f"verdict={assertion_result.get('assertion_verdict', 'no_assertion_evidence')}  "
            f"evaluated={len(assertion_result.get('evaluated_tests', []))}"
        )

        requirement_reports_by_index[idx] = assertion_result

        rows_for_requirement: list[dict] = []
        direct = 0
        partial = 0
        weak = 0
        missing = 0

        for evaluated_test in assertion_result.get("evaluated_tests", []):
            status = evaluated_test.get("assertion_status", "missing")
            if status == "direct":
                direct += 1
            elif status == "partial":
                partial += 1
            elif status == "weak":
                weak += 1
            else:
                missing += 1

            rows_for_requirement.append(
                _build_assertion_row(
                    requirement,
                    assertion_result,
                    evaluated_test,
                    "",
                )
            )

        rows_by_index[idx] = rows_for_requirement

        _log(
            f"[{idx + 1}/{total}]  Assertion ✓  {label}  "
            f"verdict={assertion_result.get('assertion_verdict', 'no_assertion_evidence')}  "
            f"evaluated={len(assertion_result.get('evaluated_tests', []))}  "
            f"direct={direct}  partial={partial}  weak={weak}  missing={missing}"
        )

        async with progress_lock:
            job["progress"] += 1
            job["current"] = (
                f"Assertion running — {job['progress']}/{total} requirements finalized"
            )


async def _run_generated_tests_cluster(
    idx: int,
    total: int,
    cluster: dict,
    framework_info: dict,
    output_filename: str,
    job: dict,
    _log,
    llm_client,
    loop,
    semaphore: asyncio.Semaphore,
    progress_lock: asyncio.Lock,
) -> dict:
    grouped_clusters = [cluster]

    async with semaphore:
        job["current"] = f"Generating {output_filename}"
        _log(
            f"[{idx + 1}/{total}]  Generate  →  {output_filename}  "
            f"framework={framework_info['framework']}  groups={len(grouped_clusters)}"
        )
        _log(f"LLM →  {output_filename}  ({framework_info['framework']})")

        generated_file = await loop.run_in_executor(
            None,
            lambda current_framework=framework_info, current_filename=output_filename, current_clusters=grouped_clusters: _run_generated_test_file_generation(
                current_framework,
                current_filename,
                current_clusters,
                llm_client,
            ),
        )

        _log(
            f"LLM ←  {output_filename}  ({framework_info['framework']})  "
            f"tests={len(generated_file.get('test_functions', []))}"
        )

        cluster_warnings: list[str] = []
        cluster_group_entries: list[dict] = []
        file_entry: dict | None = None

        expected_clusters = {
            item["gap_key"]: item for item in grouped_clusters
        }
        remaining_gap_keys = set(expected_clusters)
        functions_by_gap: dict[str, dict] = {}

        for test_fn in generated_file.get("test_functions", []):
            matched_gap_key = test_fn.get("gap_key", "")
            if matched_gap_key not in expected_clusters:
                req_ids = set(test_fn.get("requirement_ids", []))
                matching_by_req = [
                    key
                    for key, cluster_item in expected_clusters.items()
                    if req_ids.intersection(cluster_item.get("requirement_ids", []))
                ]
                if len(matching_by_req) == 1:
                    matched_gap_key = matching_by_req[0]
                elif len(remaining_gap_keys) == 1:
                    matched_gap_key = next(iter(remaining_gap_keys))

            if matched_gap_key not in expected_clusters:
                cluster_warnings.append(
                    f"Ignored generated test '{test_fn.get('function_name', '')}' because its gap key could not be matched."
                )
                continue
            if matched_gap_key in functions_by_gap:
                cluster_warnings.append(
                    f"Duplicate generated test returned for gap group '{matched_gap_key}'. Keeping the first one."
                )
                continue

            normalized_fn = {
                **test_fn,
                "gap_key": matched_gap_key,
                "requirement_ids": test_fn.get("requirement_ids")
                or expected_clusters[matched_gap_key]["requirement_ids"],
            }
            declared_identifier = _extract_declared_identifier(
                str(normalized_fn.get("code", ""))
            )
            if declared_identifier and not normalized_fn.get("function_name"):
                normalized_fn["function_name"] = declared_identifier
            functions_by_gap[matched_gap_key] = normalized_fn
            remaining_gap_keys.discard(matched_gap_key)

        ordered_functions = []
        file_requirement_ids: list[str] = []
        file_gap_keys: list[str] = []
        for cluster_item in grouped_clusters:
            gap_key = cluster_item["gap_key"]
            matched_fn = functions_by_gap.get(gap_key)
            if not matched_fn or not str(matched_fn.get("code", "")).strip():
                warning = f"LLM did not return usable code for gap group '{gap_key}'."
                cluster_warnings.append(warning)
                cluster_group_entries.append({
                    "gap_key": gap_key,
                    "gap_reason": cluster_item["gap_reason"],
                    "requirement_ids": cluster_item["requirement_ids"],
                    "framework": framework_info["framework"],
                    "language": framework_info["language"],
                    "output_file": None,
                    "test_function_name": None,
                    "status": "skipped",
                    "warning": warning,
                })
                continue

            preferred_name = cluster_item.get("preferred_function_name", "")
            current_name = str(matched_fn.get("function_name", "")).strip()
            declared_name = _extract_declared_identifier(
                str(matched_fn.get("code", ""))
            )
            effective_current_name = current_name or declared_name or ""
            if preferred_name:
                original_name = effective_current_name
                matched_fn["function_name"] = preferred_name
                if original_name and original_name != preferred_name:
                    matched_fn["code"] = _rename_code_identifier(
                        str(matched_fn.get("code", "")),
                        original_name,
                        preferred_name,
                    )
                    _log(
                        f"Renamed generated function '{original_name}' "
                        f"to '{preferred_name}' for gap group {gap_key}"
                    )
                elif declared_name and declared_name != preferred_name:
                    matched_fn["code"] = _rename_code_identifier(
                        str(matched_fn.get("code", "")),
                        declared_name,
                        preferred_name,
                    )

            ordered_functions.append(matched_fn)
            file_requirement_ids.extend(cluster_item["requirement_ids"])
            file_gap_keys.append(gap_key)
            cluster_group_entries.append({
                "gap_key": gap_key,
                "gap_reason": cluster_item["gap_reason"],
                "requirement_ids": cluster_item["requirement_ids"],
                "framework": framework_info["framework"],
                "language": framework_info["language"],
                "output_file": output_filename,
                "test_function_name": matched_fn.get("function_name", ""),
                "reasoning_basis": matched_fn.get("reasoning_basis", ""),
                "status": "generated",
            })

        if ordered_functions:
            content = _render_generated_file(
                framework_info,
                output_filename,
                generated_file.get("shared_prelude", ""),
                ordered_functions,
            )
            save_generated_test_file(output_filename, content)
            file_entry = {
                "filename": output_filename,
                "framework": framework_info["framework"],
                "language": framework_info["language"],
                "requirement_ids": _unique_preserve_order(file_requirement_ids),
                "gap_keys": _unique_preserve_order(file_gap_keys),
                "test_functions": [
                    {
                        "function_name": item.get("function_name", ""),
                        "requirement_ids": item.get("requirement_ids", []),
                        "gap_key": item.get("gap_key", ""),
                    }
                    for item in ordered_functions
                ],
            }
            _log(
                f"[{idx + 1}/{total}]  Generate ✓  {output_filename}  "
                f"tests={len(ordered_functions)}"
            )
            _log(f"Saved generated file: {output_filename}")
        else:
            _log(
                f"[{idx + 1}/{total}]  Generate !  {output_filename}  "
                f"no usable tests returned"
            )

        async with progress_lock:
            job["progress"] += 1
            job["current"] = (
                f"Generated tests running — {job['progress']}/{total} files finalized"
            )

        return {
            "idx": idx,
            "warnings": cluster_warnings,
            "group_entries": cluster_group_entries,
            "file_entry": file_entry,
        }


async def _run_stage3(
    traceability: list[dict],
    job: dict,
    _log,
    total_requirements: int,
    rerank_generated_at: str,
) -> None:
    llm_client = _get_client()
    loop = asyncio.get_event_loop()
    total = len(traceability)
    completed_before = sum(
        1 for entry in traceability if _entry_has_completed_traceability(entry)
    )
    failed_before = sum(
        1 for entry in traceability if _entry_has_failed_traceability(entry)
    )

    _log("─" * 48)
    _log(f"Stage 3 — judging reranked test candidates ({total} requirements)")
    _log(f"Stage 3 concurrency: {TRACE_STAGE3_MAX_CONCURRENCY}")
    if completed_before or failed_before:
        _log(
            f"Stage 3 resume — completed={completed_before}  retrying_failed={failed_before}"
        )
    _log("─" * 48)
    job["progress"] = completed_before

    checkpoint_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(TRACE_STAGE3_MAX_CONCURRENCY)
    tasks: list[asyncio.Task] = []

    for idx, entry in enumerate(traceability):
        requirement = entry["requirement"]
        label = _requirement_label(requirement, idx)
        if _entry_has_completed_traceability(entry):
            _log(f"[{idx + 1}/{total}]  Stage 3 ↷  {label}  reused from checkpoint")
            continue

        tasks.append(
            asyncio.create_task(
                _run_stage3_requirement(
                    idx,
                    entry,
                    traceability,
                    job,
                    _log,
                    total,
                    total_requirements,
                    rerank_generated_at,
                    llm_client,
                    loop,
                    checkpoint_lock,
                    semaphore,
                )
            )
        )

    if not tasks:
        job["current"] = None
        return

    job["current"] = (
        f"Stage 3 parallel — up to {TRACE_STAGE3_MAX_CONCURRENCY} requirements at a time"
    )
    await asyncio.gather(*tasks)
    job["current"] = None


async def _run_report_job(reuse_saved_rerank: bool = False) -> None:
    global _report_job

    _begin_job(_report_job)
    _log = _job_logger(_report_job, "report")

    try:
        if reuse_saved_rerank:
            rerank_report = load_rerank_report() or {}
            traceability = deepcopy(
                rerank_report.get("traceability", []) or [])
            rerank_generated_at = str(
                rerank_report.get("meta", {}).get("generated_at", "")
            ).strip() or datetime.now(timezone.utc).isoformat()
            total = len(traceability)
            _report_job["total"] = total

            if total == 0:
                raise ValueError(
                    "No saved rerank_report.json entries found — cannot run Stage 3 only."
                )

            _log(
                f"Starting Stage 3-only traceability report for {total} requirement chunk{'s' if total != 1 else ''}"
            )
            _log("Using saved rerank_report.json as the Stage 2 artifact")
            _log(
                f"LLM Judge: {os.environ.get('OPENAI_LLM_MODEL', 'gpt-5-mini')}")
            _log("─" * 48)

            _report_job["progress"] = 0
            await _run_stage3(
                traceability,
                _report_job,
                _log,
                total,
                rerank_generated_at,
            )

            generated_at = _save_traceability_checkpoint(
                traceability,
                total,
                rerank_generated_at,
            )
            final_report = load_traceability_report() or {
                "meta": _build_traceability_meta(traceability, generated_at, rerank_generated_at),
                "traceability": traceability,
            }
            final_meta = final_report.get("meta", {})
            failed_requirements = int(
                final_meta.get("failed_requirements", 0) or 0)
            pending_requirements = int(
                final_meta.get("pending_requirements", 0) or 0)

            _log("─" * 48)
            if failed_requirements or pending_requirements:
                warning = (
                    f"Traceability report saved with unresolved requirements — "
                    f"failed={failed_requirements} pending={pending_requirements}"
                )
                _report_job["warnings"].append(warning)
                _log(f"⚠  {warning}")
            else:
                _log(
                    f"✓  Traceability report saved — {len(traceability)} requirements analyzed")
            return

        store = get_store()
        req_chunks = store.get_chunks_by_category("requirement")
        total = len(req_chunks)
        _report_job["total"] = total

        if total == 0:
            raise ValueError(
                "No requirement chunks found — embed requirement files first.")

        requirement_ids = {
            _requirement_id({
                "file": meta.get("file_name", ""),
                "chunk_index": meta.get("chunk_index", idx),
            })
            for idx, (_, meta) in enumerate(req_chunks)
        }
        resumable_entries, rerank_generated_at, _ = _load_resumable_traceability_entries(
            requirement_ids,
            _log,
            allow_completed_rerank=reuse_saved_rerank,
        )
        resumed = bool(resumable_entries)
        _report_job["resumed"] = resumed

        _log(
            f"Starting traceability report for {total} requirement chunk{'s' if total != 1 else ''}")
        _log(
            f"Retrieval params: {RETRIEVAL_PARAMS}"
        )
        _log(f"Reranker: {CROSS_ENCODER_MODEL}")
        _log(f"LLM Judge: {os.environ.get('OPENAI_LLM_MODEL', 'gpt-5-mini')}")
        _log("─" * 48)
        missing_stage2 = [
            (text, meta)
            for idx, (text, meta) in enumerate(req_chunks)
            if _requirement_id({
                "file": meta.get("file_name", ""),
                "chunk_index": meta.get("chunk_index", idx),
            }) not in resumable_entries
        ]
        query_vecs_by_requirement: dict[str, list[float]] = {}

        if missing_stage2:
            _log(
                f"Batch embedding {len(missing_stage2)} missing requirement chunk{'s' if len(missing_stage2) != 1 else ''} (1 API call)…"
            )
            _report_job["current"] = "Batch embedding…"
            texts = [text for text, _ in missing_stage2]
            missing_vecs: list[list[float]] = await batch_embed_requirements(texts)
            for (text, meta), query_vec in zip(missing_stage2, missing_vecs):
                req_id = _requirement_id({
                    "file": meta.get("file_name", ""),
                    "chunk_index": meta.get("chunk_index", ""),
                })
                query_vecs_by_requirement[req_id] = query_vec
            _log(
                f"Batch embedding complete — {len(missing_vecs)} vectors returned"
            )
            _log("─" * 48)
        else:
            _log("Stage 2 resume — no new requirement embeddings needed")
            _log("─" * 48)

        traceability: list[dict] = []
        if rerank_generated_at is None:
            rerank_generated_at = datetime.now(timezone.utc).isoformat()
        reused_stage2 = 0

        for idx, (text, meta) in enumerate(req_chunks):
            fname = meta.get("file_name", "?")
            cidx = meta.get("chunk_index", idx)
            label = f"{fname}  [chunk {cidx}]"
            _report_job["current"] = label
            requirement_id = _requirement_id({
                "file": fname,
                "chunk_index": cidx,
            })

            existing_entry = resumable_entries.get(requirement_id)
            if existing_entry is not None:
                traceability.append(existing_entry)
                reused_stage2 += 1
                _log(
                    f"[{idx + 1}/{total}]  Stage 1/2 ↷  {label}  reused from checkpoint")
                _report_job["progress"] = len(traceability)
                continue

            req_type = classify_requirement(text)
            eff_recall = RETRIEVAL_PARAMS["top_k_recall"]
            pre_diverse_n = RETRIEVAL_PARAMS["pre_diverse_n"]
            pre_max_per_file = RETRIEVAL_PARAMS["pre_max_per_file"]
            eff_final = RETRIEVAL_PARAMS["top_k_final"]

            _log(
                f"[{idx + 1}/{total}]  [{req_type}]  Stage 1  →  {label}  "
                f"(recall={eff_recall}, pre_diverse={pre_diverse_n})"
            )

            query_vec = query_vecs_by_requirement.get(requirement_id)
            if query_vec is None:
                raise ValueError(
                    f"Missing checkpoint embedding vector for {requirement_id}"
                )

            recall = await recall_with_vector(text, query_vec, top_k=eff_recall)
            _log(
                f"[{idx + 1}/{total}]  Stage 1 ✓  tests={len(recall['tests'])}  sources={len(recall['sources'])}"
            )

            tests_pool = greedy_diversify(
                recall["tests"], top_n=pre_diverse_n, max_per_file=pre_max_per_file
            )
            sources_pool = greedy_diversify(
                recall["sources"], top_n=pre_diverse_n, max_per_file=pre_max_per_file
            )

            tests_all, sources_all = await asyncio.gather(
                rerank_candidates(text, tests_pool, top_n=len(tests_pool)),
                rerank_candidates(text, sources_pool, top_n=len(sources_pool)),
            )
            effective_test_final = resolve_top_k_final(tests_all, eff_final)
            effective_source_final = resolve_top_k_final(
                sources_all, eff_final)
            tests_reranked, promoted_tests = apply_test_safeguard(
                recall["tests"],
                tests_all,
                top_n=effective_test_final,
            )
            sources_reranked = sources_all[:effective_source_final]
            _log(
                f"[{idx + 1}/{total}]  Stage 2 ✓  tests={len(tests_reranked)}  "
                f"sources={len(sources_reranked)}  promoted={len(promoted_tests)}"
            )
            _log(
                f"[{idx + 1}/{total}]  Stage 2 · rerank_input_tests={len(tests_pool)}  "
                f"reranked_tests={len(tests_all)}  base_final={eff_final}  "
                f"effective_test_final={effective_test_final}  "
                f"effective_source_final={effective_source_final}  "
                f"final_tests={len(tests_reranked)}"
            )
            if promoted_tests:
                _log(
                    f"[{idx + 1}/{total}]  Safeguard ↑  "
                    + ", ".join(
                        f"{item.get('file_name', '?')}::chunk{item.get('chunk_index', '')}"
                        for item in promoted_tests
                    )
                )

            traceability.append({
                "requirement": {
                    "file": fname,
                    "file_id": meta.get("file_id", ""),
                    "chunk_index": cidx,
                    "text": text,
                    "requirement_type": req_type,
                },
                "candidate_pool": {
                    "stage": 1,
                    "method": "dense recall (Chroma cosine similarity)",
                    "top_k": eff_recall,
                    "tests": _ranked(recall["tests"]),
                    "sources": _ranked(recall["sources"]),
                },
                "final_candidates": {
                    "stage": 2,
                    "method": f"FlashRank ({CROSS_ENCODER_MODEL}) + greedy diversify",
                    "top_n": eff_final,
                    "effective_test_top_n": effective_test_final,
                    "effective_source_top_n": effective_source_final,
                    "pre_max_per_file": pre_max_per_file,
                    "tests": _ranked(tests_reranked),
                    "sources": _ranked(sources_reranked),
                },
                "stage2_debug": {
                    "dynamic_top_k_final_enabled": dynamic_top_k_final_enabled(),
                    "base_final_count": eff_final,
                    "effective_test_top_n": effective_test_final,
                    "effective_source_top_n": effective_source_final,
                    "rerank_input_tests": len(tests_pool),
                    "reranked_tests": len(tests_all),
                    "safeguard_promoted_tests": _promoted_test_debug_rows(promoted_tests),
                    "final_test_count": len(tests_reranked),
                },
            })

            _report_job["progress"] = idx + 1
            rerank_generated_at = _save_rerank_checkpoint(
                traceability,
                total,
                rerank_generated_at,
                complete=False,
            )

        if resumed and reused_stage2:
            _log(
                f"Stage 2 resume summary — reused={reused_stage2}  regenerated={len(missing_stage2)}"
            )

        traceability.sort(
            key=lambda record: (
                record["requirement"]["file"],
                record["requirement"]["chunk_index"],
            )
        )

        rerank_generated_at = _save_rerank_checkpoint(
            traceability,
            total,
            rerank_generated_at,
            complete=True,
        )
        _log(f"✓  Stage 2 artifact saved — {len(traceability)} requirements")

        _report_job["progress"] = 0
        await _run_stage3(
            traceability,
            _report_job,
            _log,
            total,
            rerank_generated_at,
        )

        generated_at = _save_traceability_checkpoint(
            traceability,
            total,
            rerank_generated_at,
        )
        final_report = load_traceability_report() or {
            "meta": _build_traceability_meta(traceability, generated_at, rerank_generated_at),
            "traceability": traceability,
        }
        final_meta = final_report.get("meta", {})
        failed_requirements = int(
            final_meta.get("failed_requirements", 0) or 0)
        pending_requirements = int(
            final_meta.get("pending_requirements", 0) or 0)

        _log("─" * 48)
        if failed_requirements or pending_requirements:
            warning = (
                f"Traceability report saved with unresolved requirements — "
                f"failed={failed_requirements}  pending={pending_requirements}"
            )
            _log(f"⚠  {warning}")
            _report_job["warnings"] = [warning]
        else:
            _log(
                f"✓  Traceability report saved — {len(traceability)} requirements analyzed")
        _report_job.update(
            running=False,
            done=True,
            error=None,
            current=None,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        _log(f"✗  Error: {exc}")
        _report_job.update(
            running=False,
            done=False,
            error=str(exc),
            current=None,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )


async def _run_assertion_job() -> None:
    global _assertion_job

    _begin_job(_assertion_job)
    _log = _job_logger(_assertion_job, "assertion")
    loop = asyncio.get_event_loop()

    try:
        traceability_report = load_traceability_report()
        if not traceability_report:
            raise ValueError(
                "No saved traceability report available. Generate traceability first.")

        assertion_input_report = _ensure_assertion_input_report(
            traceability_report,
            _log,
        )
        assertion_inputs = assertion_input_report.get("requirements", []) or []
        total = len(assertion_inputs)
        _assertion_job["total"] = total

        if total == 0:
            raise ValueError(
                "Saved assertion input snapshot has no requirement rows.")

        traceability_generated_at = assertion_input_report.get(
            "meta", {}).get("traceability_generated_at")
        llm_client = _get_client()
        _log(
            f"Building assertion report from saved assertion input snapshot ({total} requirements)")
        _log(f"LLM Judge: {os.environ.get('OPENAI_LLM_MODEL', 'gpt-5-mini')}")
        _log("─" * 48)

        _log(f"Assertion concurrency: {TRACE_ASSERTION_MAX_CONCURRENCY}")

        requirement_reports_by_index: list[dict | None] = [None] * total
        rows_by_index: list[list[dict]] = [[] for _ in range(total)]

        _assertion_job["progress"] = 0
        semaphore = asyncio.Semaphore(TRACE_ASSERTION_MAX_CONCURRENCY)
        progress_lock = asyncio.Lock()

        tasks = [
            asyncio.create_task(
                _run_assertion_requirement(
                    idx,
                    entry,
                    _assertion_job,
                    _log,
                    total,
                    llm_client,
                    loop,
                    semaphore,
                    progress_lock,
                    requirement_reports_by_index,
                    rows_by_index,
                )
            )
            for idx, entry in enumerate(assertion_inputs)
        ]

        _assertion_job["current"] = (
            f"Assertion parallel — up to {TRACE_ASSERTION_MAX_CONCURRENCY} requirements at a time"
        )
        await asyncio.gather(*tasks)

        requirement_reports = [
            report for report in requirement_reports_by_index if report is not None
        ]
        rows = [row for part in rows_by_index for row in part]

        generated_at = datetime.now(timezone.utc).isoformat()
        for row in rows:
            row["generated_at"] = generated_at

        counts = summarize_rows(rows)
        assertion_report = {
            "meta": {
                "generated_at": generated_at,
                "traceability_generated_at": traceability_generated_at,
                "model_llm": os.environ.get("OPENAI_LLM_MODEL", "gpt-5-mini"),
                "total_requirements": total,
                "total_rows": len(rows),
                **counts,
            },
            "requirements": requirement_reports,
            "assertions": rows,
        }
        save_assertion_report(assertion_report)

        _log("─" * 48)
        _log(
            f"✓  Assertion report saved — {len(requirement_reports)} requirements  "
            f"{len(rows)} evaluated assertion rows"
        )
        _assertion_job.update(
            running=False,
            done=True,
            current=None,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        _log(f"✗  Error: {exc}")
        _assertion_job.update(
            running=False,
            done=False,
            error=str(exc),
            current=None,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )


async def _run_generated_tests_job() -> None:
    global _tests_job

    _begin_job(_tests_job)
    _log = _job_logger(_tests_job, "tests")
    loop = asyncio.get_event_loop()

    try:
        traceability_report = load_traceability_report()
        if not traceability_report:
            raise ValueError(
                "No saved traceability report available. Generate traceability first.")

        assertion_report = load_assertion_report()
        if not assertion_report:
            raise ValueError(
                "No saved assertion report available. Run assertion first.")

        traceability_generated_at = traceability_report.get(
            "meta", {}).get("generated_at")
        assertion_generated_at = assertion_report.get(
            "meta", {}).get("generated_at")
        if assertion_report.get("meta", {}).get("traceability_generated_at") != traceability_generated_at:
            raise ValueError(
                "Saved assertion report is stale relative to traceability. Re-run assertion first.")

        rerank_report = load_rerank_report()
        llm_client = _get_client()

        clusters, collection_warnings = _collect_generation_clusters(
            assertion_report,
            traceability_report,
            rerank_report,
        )
        unique_gap_requirements = sorted({
            req_id
            for cluster in clusters
            for req_id in cluster.get("requirement_ids", [])
        })

        _tests_job["total"] = len(clusters)
        _log(
            f"Building generated tests from saved assertion report "
            f"({len(unique_gap_requirements)} gap requirements, {len(clusters)} failing assertion rows)"
        )
        _log(
            f"LLM Generator: {os.environ.get('OPENAI_LLM_MODEL', 'gpt-5-mini')}")
        _log("RAG context: assertion gaps + traceability verified tests + rerank/source exemplars")
        _log("─" * 48)

        warnings: list[str] = list(collection_warnings)
        group_entries: list[dict] = []
        resolved_clusters: list[dict] = []
        preferred_name_counts: dict[str, int] = defaultdict(int)

        for idx, cluster in enumerate(clusters):
            primary_req = cluster["requirements"][0]
            label = f"{primary_req.get('file', '?')}  [chunk {primary_req.get('chunk_index', '')}]"
            _tests_job["current"] = f"Clustering {label}"
            _log(
                f"[{idx + 1}/{max(len(clusters), 1)}]  Cluster  →  {label}  "
                f"requirements={len(cluster.get('requirement_ids', []))}"
            )

            framework_info, exemplar_tests, verified_tests, supporting_sources, detect_warnings = _detect_cluster_framework(
                cluster)
            warnings.extend(detect_warnings)
            cluster["warnings"].extend(detect_warnings)
            cluster["framework_info"] = framework_info
            name_base = _cluster_test_name_base(cluster)
            preferred_name_counts[name_base] += 1
            cluster["preferred_function_name"] = _preferred_function_name(
                cluster,
                preferred_name_counts[name_base],
                framework_info,
            )
            cluster["exemplar_tests_for_prompt"] = exemplar_tests
            cluster["verified_tests_for_prompt"] = verified_tests
            cluster["supporting_sources_for_prompt"] = supporting_sources
            cluster["assertion_rows_for_prompt"] = cluster.get("assertion_rows", [])[
                :8]

            if framework_info is None:
                warning = detect_warnings[0] if detect_warnings else "No framework could be detected."
                _log(
                    f"[{idx + 1}/{max(len(clusters), 1)}]  Cluster !  {label}  "
                    f"skipped={warning}"
                )
                group_entries.append({
                    "gap_key": cluster["gap_key"],
                    "gap_reason": cluster["gap_reason"],
                    "requirement_ids": cluster["requirement_ids"],
                    "framework": None,
                    "language": None,
                    "output_file": None,
                    "test_function_name": None,
                    "status": "skipped",
                    "warning": warning,
                })
                _tests_job["progress"] = idx + 1
                continue

            resolved_clusters.append(cluster)
            fallback_suffix = (
                f"  fallback={framework_info.get('fallback_mode')} "
                f"reason={framework_info.get('fallback_reason', '')}"
                if framework_info.get("fallback_mode")
                else ""
            )
            _log(
                f"[{idx + 1}/{max(len(clusters), 1)}]  Cluster ✓  {label}  "
                f"framework={framework_info['framework']}  language={framework_info['language']}  "
                f"gap_key={cluster['gap_key']}  function={cluster['preferred_function_name']}"
                f"{fallback_suffix}"
            )
            _tests_job["progress"] = idx + 1

        if not resolved_clusters:
            generated_at = datetime.now(timezone.utc).isoformat()
            manifest = {
                "meta": {
                    "generated_at": generated_at,
                    "traceability_generated_at": traceability_generated_at,
                    "assertion_generated_at": assertion_generated_at,
                    "model_llm": os.environ.get("OPENAI_LLM_MODEL", "gpt-5-mini"),
                    "total_gap_requirements": len(unique_gap_requirements),
                    "total_gap_groups": len(clusters),
                    "total_files": 0,
                },
                "files": [],
                "groups": group_entries,
                "warnings": warnings,
            }
            save_generated_tests_manifest(manifest)
            _log(
                "✓  Generated test manifest saved — no framework-resolved gap groups were available")
            _tests_job.update(
                running=False,
                done=True,
                current=None,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
            return

        _tests_job["progress"] = 0
        _tests_job["total"] = len(resolved_clusters)
        _log("─" * 48)
        _log(
            f"Generating {len(resolved_clusters)} framework-specific test file(s)")
        _log(
            f"Generation concurrency: {TRACE_GENERATED_TESTS_MAX_CONCURRENCY}"
        )

        generation_specs: list[tuple[int, dict, dict, str]] = []
        output_file_counts: dict[str, int] = defaultdict(int)
        for idx, cluster in enumerate(resolved_clusters):
            framework_info = cluster["framework_info"]
            requirement_prefix = _cluster_requirement_prefix(
                cluster, preserve_case=True)
            output_file_counts[requirement_prefix] += 1
            output_filename = (
                f"{requirement_prefix}_missing_test_"
                f"{output_file_counts[requirement_prefix]}.{framework_info['extension']}"
            )
            generation_specs.append(
                (idx, cluster, framework_info, output_filename))

        file_entries: list[dict] = []
        semaphore = asyncio.Semaphore(TRACE_GENERATED_TESTS_MAX_CONCURRENCY)
        progress_lock = asyncio.Lock()

        tasks = [
            asyncio.create_task(
                _run_generated_tests_cluster(
                    idx,
                    len(resolved_clusters),
                    cluster,
                    framework_info,
                    output_filename,
                    _tests_job,
                    _log,
                    llm_client,
                    loop,
                    semaphore,
                    progress_lock,
                )
            )
            for idx, cluster, framework_info, output_filename in generation_specs
        ]

        _tests_job["current"] = (
            f"Generated tests parallel — up to {TRACE_GENERATED_TESTS_MAX_CONCURRENCY} files at a time"
        )
        results = await asyncio.gather(*tasks)

        for result in sorted(results, key=lambda item: item["idx"]):
            warnings.extend(result["warnings"])
            group_entries.extend(result["group_entries"])
            file_entry = result.get("file_entry")
            if file_entry:
                file_entries.append(file_entry)

        generated_at = datetime.now(timezone.utc).isoformat()
        manifest = {
            "meta": {
                "generated_at": generated_at,
                "traceability_generated_at": traceability_generated_at,
                "assertion_generated_at": assertion_generated_at,
                "model_llm": os.environ.get("OPENAI_LLM_MODEL", "gpt-5-mini"),
                "total_gap_requirements": len(unique_gap_requirements),
                "total_gap_groups": len(clusters),
                "total_files": len(file_entries),
            },
            "files": file_entries,
            "groups": group_entries,
            "warnings": warnings,
        }
        save_generated_tests_manifest(manifest)

        _log("─" * 48)
        _log(
            f"✓  Generated test artifacts saved — files={len(file_entries)}  "
            f"gap_groups={len(clusters)}"
        )
        _tests_job.update(
            running=False,
            done=True,
            current=None,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        _log(f"✗  Error: {exc}")
        _tests_job.update(
            running=False,
            done=False,
            error=str(exc),
            current=None,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )


# ── Models ────────────────────────────────────────────────────────────────────

class TraceQueryRequest(BaseModel):
    query:            str = Field(...,
                                  description="Requirement text to trace.")
    requirement_type: Optional[str] = Field(
        default=None,
        description="Optional metadata label kept for backward compatibility. Retrieval params are fixed.",
    )


class TraceAllRequest(BaseModel):
    requirement_type: Optional[str] = Field(
        default=None,
        description="Optional metadata label kept for backward compatibility. Retrieval params are fixed.",
    )


class RecallRequest(BaseModel):
    query: str = Field(...,
                       description="Requirement text to recall candidates for.")
    top_k: int = Field(default=20, ge=1, le=100,
                       description="Number of dense candidates to retrieve per category.")


class RerankRequest(BaseModel):
    query:      str = Field(..., description="Original requirement query.")
    candidates: list[dict] = Field(
        ...,
        description=(
            "Pre-fetched candidate dicts from Stage 1 (the 'tests' or 'sources' list "
            "from /recall).  Each dict must contain at least a 'text' field."
        ),
    )
    top_n: int = Field(default=5, ge=1, le=50,
                       description="Number of top results to keep after reranking.")


class ReportRequest(BaseModel):
    reuse_saved_rerank: bool = Field(
        default=False,
        description="If true, reuse an existing saved rerank_report.json when available so only Stage 3 LLM traceability judgment reruns.",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_index() -> None:
    store = get_store()
    stats = store.get_stats()
    if stats["total_vectors"] == 0:
        raise HTTPException(
            status_code=404, detail="Index is empty — run /api/embed first.")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/recall")
async def trace_recall(body: RecallRequest) -> dict:
    """
    Stage 1 only — raw dense cosine-similarity recall, no reranking.

    Embeds the requirement query with OpenAI, then returns the top-*top_k*
    candidates from each of the "test" and "source" categories, ordered by
    descending cosine-similarity score.

    Use this endpoint to inspect what the recall stage produces before the
    FlashRank reranker filters it down.

    Response shape:
      {
        "query":   "...",
        "top_k":   20,
        "tests":   [
          { text, file_name, file_id, category, chunk_index, score }, ...
        ],
        "sources": [ ... ]
      }
    """
    _check_index()
    try:
        return await recall_for_requirement(body.query, top_k=body.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Recall failed: {exc}")


@router.post("/recall/all")
async def trace_recall_all(top_k: int = 20) -> list[dict]:
    """
    Stage 1 only — run dense recall for every requirement chunk in the index.

    Returns one record per requirement chunk, sorted by file name and chunk index.
    Each record has the same shape as /recall plus "req_file" and "chunk_index".

    One OpenAI embedding call is made per requirement chunk.
    """
    _check_index()

    stats = get_store().get_stats()
    if stats["by_category"].get("requirement", {}).get("vectors", 0) == 0:
        raise HTTPException(
            status_code=404,
            detail="No requirement chunks in the index. "
                   "Upload and embed requirement files first.",
        )
    try:
        return await recall_all_requirements(top_k=top_k)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Recall failed: {exc}")


@router.post("/rerank")
async def trace_rerank(body: RerankRequest) -> dict:
    """
    Stage 2 only — FlashRank reranking of pre-fetched candidates.

    Takes a list of candidate dicts (the "tests" or "sources" list from
    /api/trace/recall) and re-scores every (query, candidate_text) pair
    using LangChain's FlashRank wrapper.

    Use this to:
      - Inspect how reranking changes the ordering vs cosine similarity.
      - Re-run Stage 2 on Stage 1 results without hitting the embedding API again.

    The FlashRank model is loaded on first call and cached
    for the lifetime of the server process.

    Response shape:
      {
        "query":        "...",
        "top_n":        5,
        "total_input":  20,
        "results": [
          {
            text, file_name, file_id, category, chunk_index,
            score        (cosine similarity from Stage 1),
            rerank_score (FlashRank relevance score — higher = more relevant)
          }, ...
        ]
      }
    """
    _check_index()

    if not body.candidates:
        raise HTTPException(
            status_code=400, detail="candidates list is empty.")

    missing = [i for i, c in enumerate(body.candidates) if "text" not in c]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Candidates at indices {missing} are missing the required 'text' field.",
        )

    try:
        reranked = await rerank_candidates(
            body.query,
            body.candidates,
            top_n=body.top_n,
        )
        return {
            "query":       body.query,
            "top_n":       body.top_n,
            "total_input": len(body.candidates),
            "results":     reranked,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Reranking failed: {exc}")


@router.post("/query")
async def trace_query(body: TraceQueryRequest) -> dict:
    """
    Given a single requirement text, return the most relevant test code and
    source code chunks from the vector store.

    Pipeline:
      dense recall (top_k_recall per category)
        → CrossEncoder reranker (top_k_final per category)

    Response shape:
      {
        "query":   "...",
        "tests":   [{ text, file_name, file_id, category, chunk_index }, ...],
        "sources": [{ text, file_name, file_id, category, chunk_index }, ...],
      }
    """
    _check_index()
    try:
        return await retrieve_for_requirement(
            body.query,
            requirement_type=body.requirement_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Retrieval failed: {exc}")


@router.post("/all")
async def trace_all(body: TraceAllRequest) -> list[dict]:
    """
    Run retrieval for every requirement chunk currently in the vector store.

    Returns a list of traceability records sorted by requirement file name
    and chunk index.  Each record has the shape:

      {
        "query":        "requirement chunk text",
        "req_file":     "requirements.md",
        "chunk_index":  0,
        "tests":        [...],
        "sources":      [...],
      }

    This endpoint makes one OpenAI embedding call per requirement chunk.
    For large corpora it will be slow — that is expected for a baseline run.
    """
    _check_index()

    stats = get_store().get_stats()
    if stats["by_category"].get("requirement", {}).get("vectors", 0) == 0:
        raise HTTPException(
            status_code=404,
            detail="No requirement chunks found in the index. "
                   "Upload and embed requirement files first.",
        )

    try:
        results = await retrieve_all_requirements()
        return sorted(
            results,
            key=lambda r: (r.get("req_file", ""), r.get("chunk_index", 0)),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Retrieval failed: {exc}")


@router.post("/report/start")
async def start_report(body: ReportRequest, background_tasks: BackgroundTasks) -> dict:
    """Start a fresh traceability report job."""
    if _report_job["running"]:
        raise HTTPException(
            status_code=409, detail="A traceability report job is already running.")
    if _assertion_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot regenerate traceability while assertion is running.")
    if _tests_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot regenerate traceability while generated tests are running.")

    _check_index()

    stats = get_store().get_stats()
    if stats["by_category"].get("requirement", {}).get("vectors", 0) == 0:
        raise HTTPException(
            status_code=404,
            detail="No requirement chunks found. Upload and embed requirement files first.",
        )

    saved_rerank_available = bool(
        (load_rerank_report() or {}).get("traceability"))
    stage3_only_from_saved_rerank = bool(
        body.reuse_saved_rerank and saved_rerank_available
    )
    resumed = _report_has_resumable_progress() and not stage3_only_from_saved_rerank
    if stage3_only_from_saved_rerank:
        clear_traceability_outputs_keep_rerank()
    elif resumed:
        clear_assertion_report()
    else:
        clear_traceability_reports()
    _reset_job(_assertion_job)
    _reset_job(_tests_job)
    background_tasks.add_task(_run_report_job, stage3_only_from_saved_rerank)
    return {
        "message": (
            "Traceability report generation resumed"
            if resumed
            else "Traceability Stage 3 rerun started from saved rerank report"
            if stage3_only_from_saved_rerank
            else "Traceability report generation started"
        ),
        "resumed": resumed,
        "reuse_saved_rerank": stage3_only_from_saved_rerank,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/report/status")
async def report_status() -> dict:
    """Return current traceability job state plus saved artifact metadata."""
    job = dict(_report_job)
    saved = traceability_saved_status()
    if not job["running"] and not saved["exists"] and not job["error"]:
        job["done"] = False
    return {
        "job": job,
        "saved": saved,
    }


@router.get("/report/view")
async def report_view() -> JSONResponse:
    """Return a UI-friendly traceability view with requirement/test/source text."""
    report = load_traceability_report()
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No saved traceability report available. Run POST /api/trace/report/start first.",
        )
    return JSONResponse(content=build_traceability_view(report))


@router.get("/report/download")
async def download_report() -> JSONResponse:
    """Download the saved traceability report as requirement-level JSON."""
    report = load_traceability_report()
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No saved traceability report available. Run POST /api/trace/report/start first.",
        )
    requirement_level_report = build_traceability_view(report)
    return JSONResponse(
        content=requirement_level_report,
        headers={
            "Content-Disposition": "attachment; filename=traceability_report.json",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/report/download/csv")
async def download_report_csv() -> StreamingResponse:
    """Download the saved traceability report as grouped requirement-level CSV."""
    report = load_traceability_report()
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No saved traceability report available. Run POST /api/trace/report/start first.",
        )
    return _traceability_report_to_llm_csv(report, "traceability_report.csv")


@router.delete("/report")
async def clear_report() -> dict:
    """Clear saved live rerank, traceability, assertion, and generated-test artifacts."""
    if _report_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot clear traceability while its job is running.")
    if _assertion_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot clear traceability while assertion is running.")
    if _tests_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot clear traceability while generated tests are running.")

    removed = clear_traceability_reports()
    _reset_job(_report_job)
    _reset_job(_assertion_job)
    _reset_job(_tests_job)
    return {
        "success": True,
        "removed": removed,
        "cleared_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/assertion/start")
async def start_assertion(background_tasks: BackgroundTasks) -> dict:
    """Start a saved assertion report build from the traceability report."""
    if _assertion_job["running"]:
        raise HTTPException(
            status_code=409, detail="An assertion report job is already running.")
    if _report_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot run assertion while traceability is still generating.")
    if _tests_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot run assertion while generated tests are still generating.")
    traceability_report = load_traceability_report()
    if traceability_report is None:
        raise HTTPException(
            status_code=404, detail="Traceability report not found. Generate traceability first.")
    if not _traceability_report_complete(traceability_report):
        raise HTTPException(
            status_code=409,
            detail="Traceability report is incomplete or has failed requirements. Resume traceability first.",
        )

    clear_assertion_report()
    _reset_job(_tests_job)
    background_tasks.add_task(_run_assertion_job)
    return {
        "message": "Assertion report generation started",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/assertion/status")
async def assertion_status() -> dict:
    """Return current assertion job state plus saved artifact metadata."""
    traceability = traceability_saved_status()
    saved = assertion_saved_status()
    job = dict(_assertion_job)
    if not job["running"] and not saved["exists"] and not job["error"]:
        job["done"] = False
    return {
        "job": job,
        "saved": saved,
        "dependency": {
            "traceability_exists": traceability["exists"],
            "traceability_generated_at": traceability["generated_at"],
            "fresh": saved["fresh"],
        },
    }


@router.get("/assertion/download")
async def download_assertion() -> JSONResponse:
    """Download the saved assertion report JSON."""
    report = load_assertion_report()
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No saved assertion report available. Run POST /api/trace/assertion/start first.",
        )
    return JSONResponse(
        content=report,
        headers={
            "Content-Disposition": "attachment; filename=assertion_report.json",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/assertion/download/csv")
async def download_assertion_csv() -> StreamingResponse:
    """Download the saved assertion report as a flat CSV."""
    report = load_assertion_report()
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No saved assertion report available. Run POST /api/trace/assertion/start first.",
        )
    return _assertion_report_to_presentation_csv(
        report,
        "assertion_report.csv",
    )


@router.delete("/assertion")
async def clear_assertion() -> dict:
    """Clear only the saved assertion report artifact."""
    if _assertion_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot clear assertion while its job is running.")
    if _tests_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot clear assertion while generated tests are running.")

    removed = clear_assertion_report()
    _reset_job(_assertion_job)
    _reset_job(_tests_job)
    return {
        "success": True,
        "removed": removed,
        "cleared_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/tests/start")
async def start_generated_tests(background_tasks: BackgroundTasks) -> dict:
    """Start generated test creation from the saved assertion report."""
    if _tests_job["running"]:
        raise HTTPException(
            status_code=409, detail="A generated tests job is already running.")
    if _report_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot generate tests while traceability is still generating.")
    if _assertion_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot generate tests while assertion is still generating.")

    traceability = load_traceability_report()
    if traceability is None:
        raise HTTPException(
            status_code=404, detail="Traceability report not found. Generate traceability first.")

    assertion = load_assertion_report()
    if assertion is None:
        raise HTTPException(
            status_code=404, detail="Assertion report not found. Run assertion first.")

    if assertion.get("meta", {}).get("traceability_generated_at") != traceability.get("meta", {}).get("generated_at"):
        raise HTTPException(
            status_code=409, detail="Assertion report is stale. Re-run assertion first.")

    clear_generated_tests()
    background_tasks.add_task(_run_generated_tests_job)
    return {
        "message": "Generated tests job started",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/tests/status")
async def generated_tests_status() -> dict:
    """Return current generated tests job state plus saved artifact metadata."""
    assertion = assertion_saved_status()
    saved = generated_tests_saved_status()
    job = dict(_tests_job)
    if not job["running"] and not saved["exists"] and not job["error"]:
        job["done"] = False
    return {
        "job": job,
        "saved": saved,
        "dependency": {
            "assertion_exists": assertion["exists"],
            "assertion_generated_at": assertion["generated_at"],
            "fresh": saved["fresh"],
        },
    }


@router.get("/tests/download")
async def download_generated_tests_manifest() -> JSONResponse:
    """Download the saved generated-tests manifest JSON."""
    manifest = load_generated_tests_manifest()
    if manifest is None:
        raise HTTPException(
            status_code=404,
            detail="No saved generated tests manifest available. Run POST /api/trace/tests/start first.",
        )
    return JSONResponse(
        content=manifest,
        headers={
            "Content-Disposition": "attachment; filename=generated_tests_manifest.json",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/tests/download/file/{filename}")
async def download_generated_test_file(filename: str) -> FileResponse:
    """Download a generated source file from the saved generated-tests artifact."""
    path = generated_test_file_path(filename)
    if path is None:
        raise HTTPException(
            status_code=404,
            detail="Generated test file not found. Run POST /api/trace/tests/start first.",
        )
    media_type = "text/plain; charset=utf-8"
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name,
        headers={"Access-Control-Expose-Headers": "Content-Disposition"},
    )


@router.delete("/tests")
async def clear_generated_tests_route() -> dict:
    """Clear only the saved generated-tests artifact."""
    if _tests_job["running"]:
        raise HTTPException(
            status_code=409, detail="Cannot clear generated tests while their job is running.")

    removed = clear_generated_tests()
    _reset_job(_tests_job)
    return {
        "success": True,
        "removed": removed,
        "cleared_at": datetime.now(timezone.utc).isoformat(),
    }
