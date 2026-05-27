"""
services/live_reports.py
========================
Shared helpers for the live /api/trace report artifacts.

These reports are global to the currently indexed corpus and persist on disk
so the frontend can download them after server restarts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from config import TRACEABILITY_ROOT

LIVE_REPORTS_ROOT = TRACEABILITY_ROOT / "_live"
RERANK_REPORT_PATH = LIVE_REPORTS_ROOT / "rerank_report.json"
TRACEABILITY_REPORT_PATH = LIVE_REPORTS_ROOT / "traceability_report.json"
ASSERTION_INPUT_REPORT_PATH = LIVE_REPORTS_ROOT / "assertion_input_report.json"
ASSERTION_REPORT_PATH = LIVE_REPORTS_ROOT / "assertion_report.json"
GENERATED_TESTS_MANIFEST_PATH = LIVE_REPORTS_ROOT / "generated_tests_manifest.json"
GENERATED_TESTS_DIR = LIVE_REPORTS_ROOT / "generated_tests"

LIVE_REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(path)


def _read_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_rerank_report(payload: dict) -> None:
    _write_json(RERANK_REPORT_PATH, payload)


def save_traceability_report(payload: dict) -> None:
    _write_json(TRACEABILITY_REPORT_PATH, payload)


def save_assertion_input_report(payload: dict) -> None:
    _write_json(ASSERTION_INPUT_REPORT_PATH, payload)


def save_assertion_report(payload: dict) -> None:
    _write_json(ASSERTION_REPORT_PATH, payload)


def save_generated_tests_manifest(payload: dict) -> None:
    _write_json(GENERATED_TESTS_MANIFEST_PATH, payload)


def save_generated_test_file(filename: str, content: str) -> Path:
    safe_name = Path(filename).name
    if not safe_name:
        raise ValueError("Generated test filename cannot be empty.")
    path = GENERATED_TESTS_DIR / safe_name
    path.write_text(content, encoding="utf-8")
    return path


def load_rerank_report() -> Optional[dict]:
    return _read_json(RERANK_REPORT_PATH)


def load_traceability_report() -> Optional[dict]:
    return _read_json(TRACEABILITY_REPORT_PATH)


def load_assertion_input_report() -> Optional[dict]:
    return _read_json(ASSERTION_INPUT_REPORT_PATH)


def load_assertion_report() -> Optional[dict]:
    return _read_json(ASSERTION_REPORT_PATH)


def load_generated_tests_manifest() -> Optional[dict]:
    return _read_json(GENERATED_TESTS_MANIFEST_PATH)


def generated_test_file_path(filename: str) -> Optional[Path]:
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename:
        return None
    path = GENERATED_TESTS_DIR / safe_name
    return path if path.exists() else None


def list_generated_test_files() -> list[Path]:
    if not GENERATED_TESTS_DIR.exists():
        return []
    return sorted(path for path in GENERATED_TESTS_DIR.iterdir() if path.is_file())


def clear_generated_tests() -> dict:
    manifest_existed = GENERATED_TESTS_MANIFEST_PATH.exists()
    removed_files: list[str] = []
    if GENERATED_TESTS_DIR.exists():
        for path in list_generated_test_files():
            removed_files.append(path.name)
            path.unlink(missing_ok=True)
    GENERATED_TESTS_MANIFEST_PATH.unlink(missing_ok=True)
    return {
        "generated_tests_manifest": manifest_existed,
        "generated_test_files": removed_files,
    }


def clear_assertion_report() -> dict:
    input_existed = ASSERTION_INPUT_REPORT_PATH.exists()
    existed = ASSERTION_REPORT_PATH.exists()
    ASSERTION_INPUT_REPORT_PATH.unlink(missing_ok=True)
    ASSERTION_REPORT_PATH.unlink(missing_ok=True)
    generated_removed = clear_generated_tests()
    return {
        "assertion_input": input_existed,
        "assertion": existed,
        **generated_removed,
    }


def clear_traceability_outputs_keep_rerank() -> dict:
    removed = {
        "traceability": TRACEABILITY_REPORT_PATH.exists(),
        "assertion_input": ASSERTION_INPUT_REPORT_PATH.exists(),
        "assertion": ASSERTION_REPORT_PATH.exists(),
        "generated_tests_manifest": GENERATED_TESTS_MANIFEST_PATH.exists(),
        "generated_test_files": [path.name for path in list_generated_test_files()],
    }
    TRACEABILITY_REPORT_PATH.unlink(missing_ok=True)
    ASSERTION_INPUT_REPORT_PATH.unlink(missing_ok=True)
    ASSERTION_REPORT_PATH.unlink(missing_ok=True)
    GENERATED_TESTS_MANIFEST_PATH.unlink(missing_ok=True)
    for path in list_generated_test_files():
        path.unlink(missing_ok=True)
    return removed


def clear_traceability_reports() -> dict:
    removed = {
        "rerank": RERANK_REPORT_PATH.exists(),
        "traceability": TRACEABILITY_REPORT_PATH.exists(),
        "assertion_input": ASSERTION_INPUT_REPORT_PATH.exists(),
        "assertion": ASSERTION_REPORT_PATH.exists(),
        "generated_tests_manifest": GENERATED_TESTS_MANIFEST_PATH.exists(),
        "generated_test_files": [path.name for path in list_generated_test_files()],
    }
    RERANK_REPORT_PATH.unlink(missing_ok=True)
    TRACEABILITY_REPORT_PATH.unlink(missing_ok=True)
    ASSERTION_INPUT_REPORT_PATH.unlink(missing_ok=True)
    ASSERTION_REPORT_PATH.unlink(missing_ok=True)
    GENERATED_TESTS_MANIFEST_PATH.unlink(missing_ok=True)
    for path in list_generated_test_files():
        path.unlink(missing_ok=True)
    return removed


def invalidate_live_reports() -> dict:
    return clear_traceability_reports()


def _requirement_id(requirement: dict) -> str:
    file_name = requirement.get("file", "")
    chunk_index = requirement.get("chunk_index", "")
    return f"{file_name}::chunk{chunk_index}"


def _test_id(candidate: dict) -> str:
    file_name = candidate.get("file_name", "")
    chunk_index = candidate.get("chunk_index", "")
    if file_name != "":
        return f"{file_name}::chunk{chunk_index}"
    return str(candidate.get("file_id", ""))


def _source_id(candidate: dict) -> str:
    file_name = candidate.get("file_name", "")
    chunk_index = candidate.get("chunk_index", "")
    if file_name != "":
        return f"{file_name}::chunk{chunk_index}"
    return str(candidate.get("file_id", ""))


def _unique_preserve_order(values: list[object]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def _extract_likely_file_name(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("\\", "/").split("/")[-1]
    text = re.sub(r"::chunk\d+$", "", text, flags=re.IGNORECASE)
    return text.strip()


def _normalize_loose_token(value: object) -> str:
    text = _extract_likely_file_name(value)
    if not text:
        text = str(value or "").strip()
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _canonical_chunk_file_name(candidate: dict) -> str:
    for key in ("file_name", "file", "source_file", "test_file"):
        file_name = _extract_likely_file_name(candidate.get(key, ""))
        if file_name:
            return file_name
    for key in ("test_id", "source_id", "file_id"):
        fallback = _extract_likely_file_name(candidate.get(key, ""))
        if fallback:
            return fallback
    return ""


_RECORD_LIKE_SUFFIXES = {
    ".txt",
    ".md",
    ".rst",
    ".text",
    ".markdown",
    ".pdf",
    ".doc",
    ".docx",
}


def _is_record_like_file(file_name: object) -> bool:
    suffix = Path(_extract_likely_file_name(file_name)).suffix.lower()
    return suffix in _RECORD_LIKE_SUFFIXES


def _match_requirement_display_id(*values: object) -> str:
    pattern = re.compile(
        r"\b(?:rq|req|requirement)\s*[-_:]?\s*(\d+(?:\.\d+)*)\b",
        re.IGNORECASE,
    )
    for value in values:
        match = pattern.search(str(value or ""))
        if match:
            return f"RQ{match.group(1)}"
    return ""


def _match_test_display_id(*values: object) -> str:
    pattern = re.compile(
        r"\bTC\s*[-_ ]?\s*(\d+(?:[-_.]\d+)*)\b",
        re.IGNORECASE,
    )
    for value in values:
        match = pattern.search(str(value or ""))
        if not match:
            continue
        numeric_tail = re.sub(r"\s+", "", match.group(1)).replace("_", "-")
        numeric_tail = re.sub(r"^-+", "", numeric_tail)
        if numeric_tail:
            return f"TC{numeric_tail.upper()}"
    return ""


def _derive_requirement_display_id(requirement: dict) -> str:
    explicit_display_id = str(requirement.get("display_id", "")).strip()
    if explicit_display_id:
        return _match_requirement_display_id(explicit_display_id) or explicit_display_id

    requirement_file = str(requirement.get("file", "")).strip()
    if _is_record_like_file(requirement_file):
        parsed_display_id = _match_requirement_display_id(
            requirement.get("text", ""),
            requirement_file,
        )
        if parsed_display_id:
            return parsed_display_id

    return requirement_file or _requirement_id(requirement)


def _derive_test_display_id(
    *,
    candidate: Optional[dict],
    row_file: str,
    row_test_id: str,
    candidate_display_id: str,
    candidate_content_kind: str,
) -> str:
    if candidate_content_kind == "structured_test" and candidate_display_id:
        return candidate_display_id

    candidate_file = (
        str(candidate.get("file_name", "")).strip()
        if candidate is not None else ""
    )
    candidate_text = (
        str(candidate.get("text", "")).strip()
        if candidate is not None else ""
    )
    likely_file = row_file or candidate_file

    if _is_record_like_file(likely_file):
        parsed_display_id = _match_test_display_id(
            candidate_text,
            row_test_id,
            candidate_display_id,
        )
        if parsed_display_id:
            return parsed_display_id

    return row_file or candidate_file or candidate_display_id or row_test_id


def _chunk_mentions_function(candidate: dict, function_name: str) -> bool:
    normalized_function = _normalize_loose_token(function_name)
    if not normalized_function:
        return False

    for key in ("function", "function_name", "symbol_name", "symbolName"):
        candidate_name = str(candidate.get(key, "")).strip()
        if candidate_name and _normalize_loose_token(candidate_name) == normalized_function:
            return True

    chunk_text = str(candidate.get("text", "")).strip()
    if not chunk_text:
        return False

    escaped_name = re.escape(str(function_name).strip())
    if escaped_name and re.search(rf"\b{escaped_name}\b", chunk_text):
        return True
    return False


def _match_candidate_test_chunk(
    *,
    row_test_id: str,
    row_file: str,
    candidate_tests: list[dict],
) -> Optional[dict]:
    if not candidate_tests:
        return None

    strict_row_test_id = str(row_test_id or "").strip()
    if strict_row_test_id:
        for chunk in candidate_tests:
            strict_candidates = [
                str(_test_id(chunk)).strip(),
                str(chunk.get("test_id", "")).strip(),
            ]
            if any(candidate and candidate == strict_row_test_id for candidate in strict_candidates):
                return chunk

    normalized_row_test_id = re.sub(r"[^a-z0-9]+", "", strict_row_test_id.lower())
    if normalized_row_test_id:
        for chunk in candidate_tests:
            candidates = [
                _test_id(chunk),
                str(chunk.get("test_id", "")).strip(),
            ]
            if any(
                candidate
                and re.sub(r"[^a-z0-9]+", "", str(candidate).lower()) == normalized_row_test_id
                for candidate in candidates
            ):
                return chunk

    normalized_row_file = _normalize_loose_token(row_file)
    if normalized_row_file:
        for chunk in candidate_tests:
            canonical_file = _canonical_chunk_file_name(chunk)
            if canonical_file and _normalize_loose_token(canonical_file) == normalized_row_file:
                return chunk

    return candidate_tests[0] if len(candidate_tests) == 1 else None


def _match_supporting_code_chunk(
    *,
    row_function: str,
    row_file: str,
    supporting_code: list[dict],
) -> Optional[dict]:
    if not supporting_code:
        return None

    if str(row_function or "").strip():
        for chunk in supporting_code:
            if _chunk_mentions_function(chunk, row_function):
                return chunk

    normalized_row_file = _normalize_loose_token(row_file)
    if normalized_row_file:
        for chunk in supporting_code:
            canonical_file = _canonical_chunk_file_name(chunk)
            if canonical_file and _normalize_loose_token(canonical_file) == normalized_row_file:
                return chunk

    return supporting_code[0] if len(supporting_code) == 1 else None


def _materialize_test_items(
    items: list[dict],
    test_candidates: list[dict],
) -> list[dict]:
    materialized: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        test_id = str(item.get("test_id", "")).strip()
        file_name = str(item.get("file") or "").strip()
        candidate = _match_candidate_test_chunk(
            row_test_id=test_id,
            row_file=file_name,
            candidate_tests=test_candidates,
        )
        if not test_id and candidate is not None:
            test_id = _test_id(candidate)

        candidate_display_id = (
            str(candidate.get("display_id", "")).strip()
            if candidate is not None else ""
        )
        candidate_content_kind = (
            str(candidate.get("content_kind", "")).strip()
            if candidate is not None else ""
        )
        test_display_id = _derive_test_display_id(
            candidate=candidate,
            row_file=file_name,
            row_test_id=test_id,
            candidate_display_id=candidate_display_id,
            candidate_content_kind=candidate_content_kind,
        )

        matching_requirement_quotes = item.get(
            "matching_requirement_quotes", []) or []
        if not isinstance(matching_requirement_quotes, list):
            matching_requirement_quotes = []

        assertion_evidence_lines = item.get(
            "assertion_evidence_lines", []) or []
        if not isinstance(assertion_evidence_lines, list):
            assertion_evidence_lines = []

        materialized.append({
            "test_id": test_id,
            "test_display_id": test_display_id,
            "test_content_kind": candidate_content_kind,
            "file": item.get("file") or (candidate.get("file_name", "") if candidate else ""),
            "verdict": str(item.get("verdict", "")).strip(),
            "line": item.get("line", ""),
            "matching_requirement_quotes": matching_requirement_quotes,
            "assertion_evidence_lines": assertion_evidence_lines,
            "verification_confidence": str(item.get("verification_confidence", "")).strip(),
            "reasoning": str(item.get("reasoning", "")).strip(),
            "test_chunk_index": candidate.get("chunk_index", "") if candidate else "",
            "retrieval_rank": candidate.get("rank", "") if candidate else "",
            "rerank_score": candidate.get("rerank_score", "") if candidate else "",
            "test_chunk_text": candidate.get("text", "") if candidate else "",
            "safeguard_promoted": bool(candidate.get("safeguard_promoted", False)) if candidate else False,
            "safeguard_reason": candidate.get("safeguard_reason") if candidate else None,
            "stage1_rank": candidate.get("stage1_rank", "") if candidate else "",
            "score": candidate.get("score", "") if candidate else "",
        })
    return materialized


def extract_requirement_traceability_details(entry: dict) -> dict:
    requirement = entry.get("requirement", {}) or {}
    requirement_report = entry.get("traceability_report", {}) or {}
    evidence_inventory = requirement_report.get("evidence_inventory", {}) or {}
    gap_analysis = requirement_report.get("gap_analysis", {}) or {}
    final_candidates = entry.get("final_candidates", {}) or {}
    test_candidates = final_candidates.get("tests", []) or []
    source_candidates = final_candidates.get("sources", []) or []

    candidate_test_judgments = _materialize_test_items(
        requirement_report.get("candidate_test_judgments", []) or [],
        test_candidates,
    )
    verified_tests = _materialize_test_items(
        evidence_inventory.get("verified_by_tests", []) or [],
        test_candidates,
    )

    implemented_by: list[dict] = []
    for item in evidence_inventory.get("implemented_by", []) or []:
        if not isinstance(item, dict):
            continue
        file_name = str(item.get("file") or "").strip()
        candidate = _match_supporting_code_chunk(
            row_function=str(item.get("function") or "").strip(),
            row_file=file_name,
            supporting_code=source_candidates,
        )

        implemented_by.append({
            "function": item.get("function"),
            "file": item.get("file"),
            "implementation_confidence": str(item.get("implementation_confidence", "")).strip(),
            "reasoning": str(item.get("reasoning", "")).strip(),
            "source_id": _source_id(candidate) if candidate else file_name,
            "source_file": candidate.get("file_name", "") if candidate else file_name,
            "source_chunk_index": candidate.get("chunk_index", "") if candidate else "",
            "retrieval_rank": candidate.get("rank", "") if candidate else "",
            "rerank_score": candidate.get("rerank_score", "") if candidate else "",
            "source_chunk_text": candidate.get("text", "") if candidate else "",
        })

    supporting_sources = [
        {
            "source_id": _source_id(item),
            "source_file": item.get("file_name", ""),
            "source_chunk_index": item.get("chunk_index", ""),
            "retrieval_rank": item.get("rank", ""),
            "rerank_score": item.get("rerank_score", ""),
            "source_chunk_text": item.get("text", ""),
        }
        for item in source_candidates
    ]

    missing_scenarios = gap_analysis.get("missing_scenarios", []) or []
    if not isinstance(missing_scenarios, list):
        missing_scenarios = []

    verdict = str(requirement_report.get("final_verdict", "")).strip().lower()
    if verdict not in {"covered", "partially_covered", "not_covered"}:
        verdict = ""

    return {
        "requirement_id": _requirement_id(requirement),
        "reasoning_preamble": str(requirement_report.get("reasoning_preamble", "")).strip(),
        "final_verdict": verdict,
        "gap_identified": gap_analysis.get("gap_identified"),
        "gap_rationale": gap_analysis.get("gap_rationale"),
        "missing_scenarios": missing_scenarios,
        "candidate_test_judgments": candidate_test_judgments or verified_tests,
        "verified_tests": verified_tests,
        "implemented_by": implemented_by,
        "supporting_sources": supporting_sources,
        "traceability_report": requirement_report,
        "traceability_error": entry.get("traceability_error"),
    }


def _best_label(values: list[object], order: dict[str, int]) -> str:
    best_value = ""
    best_rank = -1
    for value in values:
        label = str(value or "").strip().lower()
        rank = order.get(label, -1)
        if rank > best_rank:
            best_rank = rank
            best_value = label
    return best_value


def _chunk_sort_key(value: object) -> tuple[int, int | str]:
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        raw = str(value or "").strip()
        return (1, raw or "9999")


_TRACEABILITY_VERDICT_ORDER = {
    "not_covered": 0,
    "partially_covered": 1,
    "covered": 2,
}
_TRACEABILITY_CONFIDENCE_ORDER = {
    "weak": 0,
    "partial": 1,
    "full": 2,
}


def _traceability_support_profile(verdicts: list[object]) -> dict[str, int]:
    counts = {
        "covered": 0,
        "partially_covered": 0,
        "not_covered": 0,
    }
    for verdict in verdicts:
        normalized = str(verdict or "").strip()
        if normalized in counts:
            counts[normalized] += 1
    return counts


def _traceability_support_status(profile: dict[str, int]) -> str:
    covered = int(profile.get("covered", 0) or 0)
    partial = int(profile.get("partially_covered", 0) or 0)
    not_covered = int(profile.get("not_covered", 0) or 0)

    if covered and not partial and not not_covered:
        return "direct_support"
    if partial and not covered and not not_covered:
        return "partial_support"
    if not_covered and not covered and not partial:
        return "no_support"
    if covered or partial or not_covered:
        return "mixed_support"
    return ""


def _traceability_support_summary(profile: dict[str, int]) -> str:
    parts: list[str] = []
    covered = int(profile.get("covered", 0) or 0)
    partial = int(profile.get("partially_covered", 0) or 0)
    not_covered = int(profile.get("not_covered", 0) or 0)

    if covered:
        parts.append(f"{covered} covered")
    if partial:
        parts.append(f"{partial} partial")
    if not_covered:
        parts.append(f"{not_covered} not covered")
    return ", ".join(parts)


def _group_test_artifacts(items: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}

    for item in items:
        if not isinstance(item, dict):
            continue

        artifact_display_id = str(item.get("test_display_id", "")).strip()
        artifact_file = _extract_likely_file_name(
            item.get("file") or item.get("test_id", "")
        )
        if artifact_display_id and artifact_file and artifact_display_id != artifact_file:
            artifact_id = f"{artifact_file}::{artifact_display_id}"
        else:
            artifact_id = (
                artifact_display_id
                or artifact_file
                or str(item.get("test_id", "")).strip()
                or "unknown_test"
            )
        group = groups.get(artifact_id)
        if group is None:
            group = {
                "artifact_id": artifact_id,
                "artifact_label": artifact_display_id or artifact_file or artifact_id,
                "test_file": artifact_file or str(item.get("file", "")).strip(),
                "reasoning_summaries": [],
                "matching_requirement_quotes": [],
                "assertion_evidence_lines": [],
                "test_ids": [],
                "evidence_chunks": [],
            }
            groups[artifact_id] = group

        reasoning = str(item.get("reasoning", "")).strip()
        if reasoning:
            group["reasoning_summaries"].append(reasoning)

        group["matching_requirement_quotes"].extend(item.get("matching_requirement_quotes", []) or [])
        group["assertion_evidence_lines"].extend(item.get("assertion_evidence_lines", []) or [])

        test_id = str(item.get("test_id", "")).strip()
        if test_id:
            group["test_ids"].append(test_id)

        group["evidence_chunks"].append({
            "chunk_id": test_id or artifact_id,
            "chunk_index": item.get("test_chunk_index", ""),
            "line": item.get("line", ""),
            "verdict": str(item.get("verdict", "")).strip(),
            "verification_confidence": str(item.get("verification_confidence", "")).strip(),
            "reasoning": reasoning,
            "matching_requirement_quotes": item.get("matching_requirement_quotes", []) or [],
            "assertion_evidence_lines": item.get("assertion_evidence_lines", []) or [],
            "retrieval_rank": item.get("retrieval_rank", ""),
            "rerank_score": item.get("rerank_score", ""),
            "test_chunk_text": item.get("test_chunk_text", ""),
            "safeguard_promoted": bool(item.get("safeguard_promoted", False)),
            "safeguard_reason": item.get("safeguard_reason"),
            "stage1_rank": item.get("stage1_rank", ""),
            "score": item.get("score", ""),
        })

    artifacts: list[dict] = []
    for group in groups.values():
        evidence_chunks = sorted(
            group["evidence_chunks"],
            key=lambda chunk: (
                _chunk_sort_key(chunk.get("chunk_index", "")),
                str(chunk.get("chunk_id", "")),
            ),
        )
        verdict = _best_label(
            [chunk.get("verdict", "") for chunk in evidence_chunks],
            _TRACEABILITY_VERDICT_ORDER,
        )
        confidence = _best_label(
            [chunk.get("verification_confidence", "") for chunk in evidence_chunks],
            _TRACEABILITY_CONFIDENCE_ORDER,
        )
        support_profile = _traceability_support_profile(
            [chunk.get("verdict", "") for chunk in evidence_chunks]
        )

        artifacts.append({
            "artifact_id": group["artifact_id"],
            "artifact_label": group["artifact_label"],
            "test_file": group["test_file"],
            "verdict": verdict,
            "support_status": _traceability_support_status(support_profile),
            "support_profile": support_profile,
            "support_profile_summary": _traceability_support_summary(support_profile),
            "verification_confidence": confidence,
            "reasoning_summaries": _unique_preserve_order(group["reasoning_summaries"]),
            "matching_requirement_quotes": _unique_preserve_order(group["matching_requirement_quotes"]),
            "assertion_evidence_lines": _unique_preserve_order(group["assertion_evidence_lines"]),
            "test_ids": _unique_preserve_order(group["test_ids"]),
            "chunk_count": len(evidence_chunks),
            "evidence_chunks": evidence_chunks,
        })

    artifacts.sort(
        key=lambda artifact: (
            str(artifact.get("test_file", "") or artifact.get("artifact_label", "")),
            str(artifact.get("artifact_id", "")),
        )
    )
    return artifacts


def _group_implemented_artifacts(items: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}

    for item in items:
        if not isinstance(item, dict):
            continue

        source_file = _extract_likely_file_name(
            item.get("source_file") or item.get("file") or item.get("source_id", "")
        )
        function_name = str(item.get("function") or "").strip()
        artifact_id = (
            f"{source_file}::{function_name}"
            if source_file and function_name
            else source_file or function_name or str(item.get("source_id", "")).strip() or "unknown_source"
        )

        group = groups.get(artifact_id)
        if group is None:
            group = {
                "artifact_id": artifact_id,
                "artifact_label": function_name or source_file or artifact_id,
                "source_file": source_file or str(item.get("file", "")).strip(),
                "function_names": [],
                "reasoning_summaries": [],
                "evidence_chunks": [],
            }
            groups[artifact_id] = group

        if function_name:
            group["function_names"].append(function_name)

        reasoning = str(item.get("reasoning", "")).strip()
        if reasoning:
            group["reasoning_summaries"].append(reasoning)

        group["evidence_chunks"].append({
            "source_id": item.get("source_id", ""),
            "source_file": source_file or str(item.get("source_file", "")).strip(),
            "source_chunk_index": item.get("source_chunk_index", ""),
            "retrieval_rank": item.get("retrieval_rank", ""),
            "rerank_score": item.get("rerank_score", ""),
            "source_chunk_text": item.get("source_chunk_text", ""),
            "implementation_confidence": str(item.get("implementation_confidence", "")).strip(),
            "reasoning": reasoning,
            "function": function_name or None,
        })

    artifacts: list[dict] = []
    for group in groups.values():
        evidence_chunks = sorted(
            group["evidence_chunks"],
            key=lambda chunk: (
                _chunk_sort_key(chunk.get("source_chunk_index", "")),
                str(chunk.get("source_id", "")),
            ),
        )
        confidence = _best_label(
            [chunk.get("implementation_confidence", "") for chunk in evidence_chunks],
            _TRACEABILITY_CONFIDENCE_ORDER,
        )
        artifacts.append({
            "artifact_id": group["artifact_id"],
            "artifact_label": group["artifact_label"],
            "source_file": group["source_file"],
            "function_names": _unique_preserve_order(group["function_names"]),
            "implementation_confidence": confidence,
            "reasoning_summaries": _unique_preserve_order(group["reasoning_summaries"]),
            "chunk_count": len(evidence_chunks),
            "evidence_chunks": evidence_chunks,
        })

    artifacts.sort(
        key=lambda artifact: (
            str(artifact.get("source_file", "") or artifact.get("artifact_label", "")),
            str(artifact.get("artifact_id", "")),
        )
    )
    return artifacts


def _group_supporting_source_artifacts(items: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}

    for item in items:
        if not isinstance(item, dict):
            continue

        source_file = _extract_likely_file_name(
            item.get("source_file") or item.get("source_id", "")
        )
        artifact_id = source_file or str(item.get("source_id", "")).strip() or "unknown_source"
        group = groups.get(artifact_id)
        if group is None:
            group = {
                "artifact_id": artifact_id,
                "artifact_label": source_file or artifact_id,
                "source_file": source_file,
                "evidence_chunks": [],
            }
            groups[artifact_id] = group

        group["evidence_chunks"].append({
            "source_id": item.get("source_id", ""),
            "source_file": source_file or str(item.get("source_file", "")).strip(),
            "source_chunk_index": item.get("source_chunk_index", ""),
            "retrieval_rank": item.get("retrieval_rank", ""),
            "rerank_score": item.get("rerank_score", ""),
            "source_chunk_text": item.get("source_chunk_text", ""),
        })

    artifacts: list[dict] = []
    for group in groups.values():
        evidence_chunks = sorted(
            group["evidence_chunks"],
            key=lambda chunk: (
                _chunk_sort_key(chunk.get("source_chunk_index", "")),
                str(chunk.get("source_id", "")),
            ),
        )
        artifacts.append({
            "artifact_id": group["artifact_id"],
            "artifact_label": group["artifact_label"],
            "source_file": group["source_file"],
            "chunk_count": len(evidence_chunks),
            "evidence_chunks": evidence_chunks,
        })

    artifacts.sort(
        key=lambda artifact: (
            str(artifact.get("source_file", "") or artifact.get("artifact_label", "")),
            str(artifact.get("artifact_id", "")),
        )
    )
    return artifacts


def _derive_traceability_mapper(entry: dict) -> dict:
    details = extract_requirement_traceability_details(entry)
    return {
        "verdict": details.get("final_verdict", ""),
        "reasoning": details.get("reasoning_preamble", ""),
        "gap": details.get("gap_identified"),
        "gap_reason": details.get("gap_rationale"),
    }


def _traceability_requirement_counts(report: Optional[dict]) -> dict:
    counts = {
        "covered": 0,
        "partially_covered": 0,
        "not_covered": 0,
    }
    if not report:
        return counts

    for entry in report.get("traceability", []):
        verdict = str(_derive_traceability_mapper(
            entry).get("verdict", "")).strip()
        if verdict in counts:
            counts[verdict] += 1
    return counts


def flatten_traceability_rows(report: Optional[dict]) -> list[dict]:
    if not report:
        return []

    generated_at = report.get("meta", {}).get("generated_at")
    rows: list[dict] = []

    for entry in report.get("traceability", []):
        requirement = entry.get("requirement", {})
        req_id = _requirement_id(requirement)
        mapper = _derive_traceability_mapper(entry)
        details = extract_requirement_traceability_details(entry)
        supporting_sources = details.get("supporting_sources", [])
        supporting_source_ids = " | ".join(
            str(item.get("source_id", "")).strip()
            for item in supporting_sources
            if str(item.get("source_id", "")).strip()
        )
        supporting_source_files = " | ".join(
            file_name
            for file_name in dict.fromkeys(
                str(item.get("source_file", "")).strip()
                for item in supporting_sources
                if str(item.get("source_file", "")).strip()
            )
        )
        supporting_source_texts = "\n\n---\n\n".join(
            f"[{item.get('source_id', '')}]\n{item.get('source_chunk_text', '')}".strip()
            for item in supporting_sources
            if str(item.get("source_chunk_text", "")).strip()
        )
        judged_tests = details.get(
            "candidate_test_judgments", []) or details.get("verified_tests", [])

        for item in judged_tests:
            rows.append({
                "requirement_raw_id": req_id,
                "requirement_display_id": requirement.get("display_id", "") or requirement.get("file", ""),
                "requirement_id": req_id,
                "requirement_verdict": mapper.get("verdict", ""),
                "requirement_reasoning": mapper.get("reasoning", ""),
                "test_raw_id": item.get("test_id", ""),
                "test_display_id": item.get("test_display_id", "") or item.get("file", ""),
                "test_id": item.get("test_id", ""),
                "verdict": item.get("verdict", ""),
                "candidate_verdict": item.get("verdict", ""),
                "candidate_reasoning": item.get("reasoning", ""),
                "verdict_confidence": item.get("verification_confidence", ""),
                "verification_confidence": item.get("verification_confidence", ""),
                "reasoning": item.get("reasoning", ""),
                "requirement_file": requirement.get("file", ""),
                "requirement_chunk_index": requirement.get("chunk_index", ""),
                "requirement_text": requirement.get("text", ""),
                "test_file": item.get("file", ""),
                "test_chunk_index": item.get("test_chunk_index", ""),
                "test_line": item.get("line", ""),
                "matching_requirement_quotes": item.get("matching_requirement_quotes", []),
                "assertion_evidence_lines": item.get("assertion_evidence_lines", []),
                "retrieval_rank": item.get("retrieval_rank", ""),
                "rerank_score": item.get("rerank_score", ""),
                "test_chunk_text": item.get("test_chunk_text", ""),
                "candidate_text": item.get("test_chunk_text", ""),
                "supporting_source_ids": supporting_source_ids,
                "supporting_source_files": supporting_source_files,
                "supporting_source_texts": supporting_source_texts,
                "traceability_verdict": mapper.get("verdict", ""),
                "traceability_gap": mapper.get("gap"),
                "traceability_gap_reason": mapper.get("gap_reason"),
                "missing_scenarios": details.get("missing_scenarios", []),
                "generated_at": generated_at,
            })

    return rows


def build_traceability_summary_rows(report: Optional[dict]) -> list[dict]:
    if not report:
        return []

    rows: list[dict] = []
    for entry in report.get("traceability", []):
        requirement = entry.get("requirement", {})
        req_file = str(requirement.get("file", "")).strip()
        req_chunk_index = requirement.get("chunk_index", "")
        req_display_id = _derive_requirement_display_id(requirement)
        mapper = _derive_traceability_mapper(entry)
        details = extract_requirement_traceability_details(entry)
        supporting_test_ids = " | ".join(
            dict.fromkeys(
                str(item.get("test_display_id", "")).strip()
                or str(item.get("file", "")).strip()
                for item in details.get("verified_tests", [])
                if (
                    str(item.get("test_display_id", "")).strip()
                    or str(item.get("file", "")).strip()
                )
            )
        ) or "—"
        supporting_code_files = " | ".join(
            dict.fromkeys(
                str(item.get("source_file", "")).strip()
                for item in details.get("supporting_sources", [])
                if str(item.get("source_file", "")).strip()
            )
        ) or "—"

        rows.append({
            "requirement_id": req_display_id or req_file or "—",
            "requirement_text": requirement.get("text", "") or "—",
            "verdict": mapper.get("verdict", "") or "—",
            "reasoning": mapper.get("reasoning", "") or "—",
            "test_id": supporting_test_ids,
            "supporting_file": supporting_code_files,
            "requirement_sort_file": req_file,
            "requirement_sort_chunk_index": req_chunk_index,
        })

    def _chunk_sort_value(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 9999

    rows.sort(
        key=lambda row: (
            str(row.get("requirement_sort_file", "")),
            _chunk_sort_value(row.get("requirement_sort_chunk_index", "")),
        )
    )
    return rows


def _build_requirement_chunk_view(entry: dict, generated_at: object) -> dict:
    requirement = entry.get("requirement", {})
    req_id = _requirement_id(requirement)
    mapper = _derive_traceability_mapper(entry)
    details = extract_requirement_traceability_details(entry)
    verified_tests = details.get("verified_tests", [])
    implemented_by = details.get("implemented_by", [])
    supporting_sources = details.get("supporting_sources", [])
    candidate_test_artifacts = _group_test_artifacts(
        details.get("candidate_test_judgments", [])
    )
    verified_test_artifacts = _group_test_artifacts(verified_tests)
    implemented_artifacts = _group_implemented_artifacts(implemented_by)
    supporting_source_artifacts = _group_supporting_source_artifacts(
        supporting_sources
    )
    stage2_debug = entry.get("stage2_debug") or {}
    chunk_index = requirement.get("chunk_index", "")
    chunk_label = (
        f"Chunk {chunk_index}"
        if str(chunk_index).strip() != ""
        else ""
    )

    return {
        "requirement_id": req_id,
        "requirement_file": requirement.get("file", ""),
        "requirement_display_id": _derive_requirement_display_id(requirement),
        "requirement_content_kind": requirement.get("content_kind", ""),
        "requirement_chunk_index": chunk_index,
        "requirement_chunk_label": chunk_label,
        "requirement_text": requirement.get("text", ""),
        "traceability_verdict": mapper.get("verdict", ""),
        "requirement_reasoning": mapper.get("reasoning", ""),
        "traceability_gap": mapper.get("gap"),
        "traceability_gap_reason": mapper.get("gap_reason"),
        "traceability_error": details.get("traceability_error"),
        "verified_test_count": len(verified_tests),
        "candidate_test_artifact_count": len(candidate_test_artifacts),
        "verified_test_artifact_count": len(verified_test_artifacts),
        "candidate_test_judgments": details.get("candidate_test_judgments", []),
        "implemented_by_count": len(implemented_by),
        "implemented_artifact_count": len(implemented_artifacts),
        "supporting_source_artifact_count": len(supporting_source_artifacts),
        "stage2_debug": {
            "dynamic_top_k_final_enabled": stage2_debug.get("dynamic_top_k_final_enabled"),
            "base_final_count": stage2_debug.get("base_final_count"),
            "effective_test_top_n": stage2_debug.get("effective_test_top_n"),
            "effective_source_top_n": stage2_debug.get("effective_source_top_n"),
            "rerank_input_tests": stage2_debug.get("rerank_input_tests", 0),
            "reranked_tests": stage2_debug.get("reranked_tests", 0),
            "safeguard_promoted_tests": stage2_debug.get("safeguard_promoted_tests", []),
            "final_test_count": stage2_debug.get("final_test_count", len(entry.get("final_candidates", {}).get("tests", []) or [])),
        },
        "candidate_test_artifacts": candidate_test_artifacts,
        "verified_test_artifacts": verified_test_artifacts,
        "verified_tests": verified_tests,
        "implemented_artifacts": implemented_artifacts,
        "implemented_by": implemented_by,
        "supporting_source_artifacts": supporting_source_artifacts,
        "supporting_sources": supporting_sources,
        "traceability_report": details.get("traceability_report"),
        "generated_at": generated_at,
    }


def _aggregate_requirement_verdict(verdicts: list[object]) -> str:
    normalized = [str(verdict or "").strip() for verdict in verdicts if str(verdict or "").strip()]
    verdict_set = set(normalized)
    if not verdict_set:
        return ""
    if verdict_set == {"covered"}:
        return "covered"
    if verdict_set == {"not_covered"}:
        return "not_covered"
    return "partially_covered"


def _aggregate_confidence(labels: list[object]) -> str:
    normalized = [str(label or "").strip() for label in labels if str(label or "").strip()]
    if not normalized:
        return ""
    if len(set(normalized)) > 1:
        return "partial"
    return normalized[0]


def _aggregate_requirement_text(chunk_views: list[dict]) -> str:
    if len(chunk_views) == 1:
        return str(chunk_views[0].get("requirement_text", "")).strip()

    parts: list[str] = []
    for chunk in chunk_views:
        chunk_label = str(chunk.get("requirement_chunk_label", "")).strip() or "Chunk"
        text = str(chunk.get("requirement_text", "")).strip()
        if not text:
            continue
        parts.append(f"[{chunk_label}]\n{text}")
    return "\n\n".join(parts)


def _aggregate_requirement_reasoning(chunk_views: list[dict]) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for chunk in chunk_views:
        chunk_label = str(chunk.get("requirement_chunk_label", "")).strip() or "Chunk"
        traceability_report = chunk.get("traceability_report")
        if not isinstance(traceability_report, dict):
            traceability_report = {}
        reasoning = (
            str(traceability_report.get("reasoning_preamble", "")).strip()
            or str(chunk.get("requirement_reasoning", "")).strip()
        )
        if not reasoning:
            continue
        labeled = f"[{chunk_label}] {reasoning}"
        if labeled in seen:
            continue
        seen.add(labeled)
        parts.append(labeled)
    return "\n\n".join(parts)


def _aggregate_gap_reason(chunk_views: list[dict]) -> str | None:
    parts: list[str] = []
    seen: set[str] = set()
    for chunk in chunk_views:
        reason = str(chunk.get("traceability_gap_reason", "") or "").strip()
        if not reason:
            continue
        chunk_label = str(chunk.get("requirement_chunk_label", "")).strip() or "Chunk"
        labeled = f"[{chunk_label}] {reason}"
        if labeled in seen:
            continue
        seen.add(labeled)
        parts.append(labeled)
    return "\n\n".join(parts) if parts else None


def _aggregate_stage2_debug(chunk_views: list[dict]) -> dict:
    promoted_tests: list[dict] = []
    for chunk in chunk_views:
        chunk_label = str(chunk.get("requirement_chunk_label", "")).strip() or "Chunk"
        for item in chunk.get("stage2_debug", {}).get("safeguard_promoted_tests", []) or []:
            if not isinstance(item, dict):
                continue
            promoted_tests.append({
                **item,
                "requirement_chunk_label": chunk_label,
            })

    first_debug = chunk_views[0].get("stage2_debug", {}) if chunk_views else {}
    return {
        "dynamic_top_k_final_enabled": first_debug.get("dynamic_top_k_final_enabled"),
        "base_final_count": first_debug.get("base_final_count"),
        "effective_test_top_n": first_debug.get("effective_test_top_n"),
        "effective_source_top_n": first_debug.get("effective_source_top_n"),
        "rerank_input_tests": sum(
            int(chunk.get("stage2_debug", {}).get("rerank_input_tests", 0) or 0)
            for chunk in chunk_views
        ),
        "reranked_tests": sum(
            int(chunk.get("stage2_debug", {}).get("reranked_tests", 0) or 0)
            for chunk in chunk_views
        ),
        "safeguard_promoted_tests": promoted_tests,
        "final_test_count": sum(
            int(chunk.get("stage2_debug", {}).get("final_test_count", 0) or 0)
            for chunk in chunk_views
        ),
    }


def _aggregate_requirement_chunks(chunk_views: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for chunk in chunk_views:
        chunks.append({
            "requirement_chunk_id": chunk.get("requirement_id", ""),
            "requirement_chunk_index": chunk.get("requirement_chunk_index", ""),
            "requirement_chunk_label": chunk.get("requirement_chunk_label", ""),
            "requirement_text": chunk.get("requirement_text", ""),
            "traceability_verdict": chunk.get("traceability_verdict", ""),
            "requirement_reasoning": chunk.get("requirement_reasoning", ""),
            "traceability_gap": chunk.get("traceability_gap"),
            "traceability_gap_reason": chunk.get("traceability_gap_reason"),
            "candidate_test_artifact_count": chunk.get("candidate_test_artifact_count", 0),
            "verified_test_artifact_count": chunk.get("verified_test_artifact_count", 0),
            "implemented_artifact_count": chunk.get("implemented_artifact_count", 0),
            "supporting_source_artifact_count": chunk.get("supporting_source_artifact_count", 0),
            "candidate_test_artifacts": chunk.get("candidate_test_artifacts", []),
            "verified_test_artifacts": chunk.get("verified_test_artifacts", []),
            "implemented_artifacts": chunk.get("implemented_artifacts", []),
            "supporting_source_artifacts": chunk.get("supporting_source_artifacts", []),
            "traceability_report": chunk.get("traceability_report"),
            "traceability_error": chunk.get("traceability_error"),
        })
    chunks.sort(
        key=lambda item: _chunk_sort_key(item.get("requirement_chunk_index", ""))
    )
    return chunks


def _aggregate_test_artifacts_across_chunks(
    chunk_views: list[dict],
    field_name: str,
) -> list[dict]:
    groups: dict[str, dict] = {}

    for chunk in chunk_views:
        chunk_label = str(chunk.get("requirement_chunk_label", "")).strip() or "Chunk"
        for artifact in chunk.get(field_name, []) or []:
            if not isinstance(artifact, dict):
                continue

            artifact_id = str(artifact.get("artifact_id", "")).strip() or "unknown_test"
            group = groups.get(artifact_id)
            if group is None:
                group = {
                    "artifact_id": artifact_id,
                    "artifact_label": artifact.get("artifact_label", artifact_id),
                    "test_file": artifact.get("test_file", ""),
                    "verdicts": [],
                    "confidences": [],
                    "reasoning_summaries": [],
                    "matching_requirement_quotes": [],
                    "assertion_evidence_lines": [],
                    "test_ids": [],
                    "evidence_chunks": [],
                }
                groups[artifact_id] = group

            group["verdicts"].append(artifact.get("verdict", ""))
            group["confidences"].append(artifact.get("verification_confidence", ""))
            group["reasoning_summaries"].extend(artifact.get("reasoning_summaries", []) or [])
            group["matching_requirement_quotes"].extend(artifact.get("matching_requirement_quotes", []) or [])
            group["assertion_evidence_lines"].extend(artifact.get("assertion_evidence_lines", []) or [])
            group["test_ids"].extend(artifact.get("test_ids", []) or [])

            for evidence in artifact.get("evidence_chunks", []) or []:
                if not isinstance(evidence, dict):
                    continue
                group["evidence_chunks"].append({
                    **evidence,
                    "requirement_chunk_id": chunk.get("requirement_id", ""),
                    "requirement_chunk_index": chunk.get("requirement_chunk_index", ""),
                    "requirement_chunk_label": chunk_label,
                    "requirement_text": chunk.get("requirement_text", ""),
                    "requirement_chunk_verdict": chunk.get("traceability_verdict", ""),
                })

    artifacts: list[dict] = []
    for group in groups.values():
        evidence_chunks = sorted(
            group["evidence_chunks"],
            key=lambda chunk: (
                _chunk_sort_key(chunk.get("requirement_chunk_index", "")),
                _chunk_sort_key(chunk.get("chunk_index", "")),
                str(chunk.get("chunk_id", "")),
            ),
        )
        support_profile = _traceability_support_profile(
            [chunk.get("verdict", "") for chunk in evidence_chunks]
        )
        artifacts.append({
            "artifact_id": group["artifact_id"],
            "artifact_label": group["artifact_label"],
            "test_file": group["test_file"],
            "verdict": _aggregate_requirement_verdict(group["verdicts"]),
            "support_status": _traceability_support_status(support_profile),
            "support_profile": support_profile,
            "support_profile_summary": _traceability_support_summary(support_profile),
            "verification_confidence": _aggregate_confidence(group["confidences"]),
            "reasoning_summaries": _unique_preserve_order(group["reasoning_summaries"]),
            "matching_requirement_quotes": _unique_preserve_order(group["matching_requirement_quotes"]),
            "assertion_evidence_lines": _unique_preserve_order(group["assertion_evidence_lines"]),
            "test_ids": _unique_preserve_order(group["test_ids"]),
            "chunk_count": len(evidence_chunks),
            "evidence_chunks": evidence_chunks,
        })

    artifacts.sort(
        key=lambda artifact: (
            str(artifact.get("test_file", "") or artifact.get("artifact_label", "")),
            str(artifact.get("artifact_id", "")),
        )
    )
    return artifacts


def _aggregate_implemented_artifacts_across_chunks(chunk_views: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}

    for chunk in chunk_views:
        chunk_label = str(chunk.get("requirement_chunk_label", "")).strip() or "Chunk"
        for artifact in chunk.get("implemented_artifacts", []) or []:
            if not isinstance(artifact, dict):
                continue

            artifact_id = str(artifact.get("artifact_id", "")).strip() or "unknown_source"
            group = groups.get(artifact_id)
            if group is None:
                group = {
                    "artifact_id": artifact_id,
                    "artifact_label": artifact.get("artifact_label", artifact_id),
                    "source_file": artifact.get("source_file", ""),
                    "function_names": [],
                    "confidences": [],
                    "reasoning_summaries": [],
                    "evidence_chunks": [],
                }
                groups[artifact_id] = group

            group["function_names"].extend(artifact.get("function_names", []) or [])
            group["confidences"].append(artifact.get("implementation_confidence", ""))
            group["reasoning_summaries"].extend(artifact.get("reasoning_summaries", []) or [])

            for evidence in artifact.get("evidence_chunks", []) or []:
                if not isinstance(evidence, dict):
                    continue
                group["evidence_chunks"].append({
                    **evidence,
                    "requirement_chunk_id": chunk.get("requirement_id", ""),
                    "requirement_chunk_index": chunk.get("requirement_chunk_index", ""),
                    "requirement_chunk_label": chunk_label,
                    "requirement_text": chunk.get("requirement_text", ""),
                    "requirement_chunk_verdict": chunk.get("traceability_verdict", ""),
                })

    artifacts: list[dict] = []
    for group in groups.values():
        evidence_chunks = sorted(
            group["evidence_chunks"],
            key=lambda chunk: (
                _chunk_sort_key(chunk.get("requirement_chunk_index", "")),
                _chunk_sort_key(chunk.get("source_chunk_index", "")),
                str(chunk.get("source_id", "")),
            ),
        )
        artifacts.append({
            "artifact_id": group["artifact_id"],
            "artifact_label": group["artifact_label"],
            "source_file": group["source_file"],
            "function_names": _unique_preserve_order(group["function_names"]),
            "implementation_confidence": _aggregate_confidence(group["confidences"]),
            "reasoning_summaries": _unique_preserve_order(group["reasoning_summaries"]),
            "chunk_count": len(evidence_chunks),
            "evidence_chunks": evidence_chunks,
        })

    artifacts.sort(
        key=lambda artifact: (
            str(artifact.get("source_file", "") or artifact.get("artifact_label", "")),
            str(artifact.get("artifact_id", "")),
        )
    )
    return artifacts


def _aggregate_supporting_source_artifacts_across_chunks(chunk_views: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}

    for chunk in chunk_views:
        chunk_label = str(chunk.get("requirement_chunk_label", "")).strip() or "Chunk"
        for artifact in chunk.get("supporting_source_artifacts", []) or []:
            if not isinstance(artifact, dict):
                continue

            artifact_id = str(artifact.get("artifact_id", "")).strip() or "unknown_source"
            group = groups.get(artifact_id)
            if group is None:
                group = {
                    "artifact_id": artifact_id,
                    "artifact_label": artifact.get("artifact_label", artifact_id),
                    "source_file": artifact.get("source_file", ""),
                    "evidence_chunks": [],
                }
                groups[artifact_id] = group

            for evidence in artifact.get("evidence_chunks", []) or []:
                if not isinstance(evidence, dict):
                    continue
                group["evidence_chunks"].append({
                    **evidence,
                    "requirement_chunk_id": chunk.get("requirement_id", ""),
                    "requirement_chunk_index": chunk.get("requirement_chunk_index", ""),
                    "requirement_chunk_label": chunk_label,
                    "requirement_text": chunk.get("requirement_text", ""),
                    "requirement_chunk_verdict": chunk.get("traceability_verdict", ""),
                })

    artifacts: list[dict] = []
    for group in groups.values():
        evidence_chunks = sorted(
            group["evidence_chunks"],
            key=lambda chunk: (
                _chunk_sort_key(chunk.get("requirement_chunk_index", "")),
                _chunk_sort_key(chunk.get("source_chunk_index", "")),
                str(chunk.get("source_id", "")),
            ),
        )
        artifacts.append({
            "artifact_id": group["artifact_id"],
            "artifact_label": group["artifact_label"],
            "source_file": group["source_file"],
            "chunk_count": len(evidence_chunks),
            "evidence_chunks": evidence_chunks,
        })

    artifacts.sort(
        key=lambda artifact: (
            str(artifact.get("source_file", "") or artifact.get("artifact_label", "")),
            str(artifact.get("artifact_id", "")),
        )
    )
    return artifacts


def build_traceability_view(report: Optional[dict]) -> dict:
    if not report:
        return {
            "meta": {},
            "requirements": [],
        }

    generated_at = report.get("meta", {}).get("generated_at")
    chunk_views = [
        _build_requirement_chunk_view(entry, generated_at)
        for entry in report.get("traceability", [])
    ]

    grouped_by_file: dict[str, list[dict]] = {}
    for chunk_view in chunk_views:
        requirement_display_id = str(
            chunk_view.get("requirement_display_id", "")
        ).strip()
        requirement_file = str(chunk_view.get("requirement_file", "")).strip()
        raw_requirement_id = str(chunk_view.get("requirement_id", "")).strip()
        if requirement_display_id and requirement_display_id not in {
            requirement_file,
            raw_requirement_id,
        }:
            requirement_group_key = (
                f"{requirement_file}::{requirement_display_id}"
                if requirement_file else requirement_display_id
            )
        else:
            requirement_group_key = requirement_file or raw_requirement_id
        grouped_by_file.setdefault(requirement_group_key, []).append(chunk_view)

    requirements: list[dict] = []
    for requirement_group_key, items in grouped_by_file.items():
        items.sort(
            key=lambda item: _chunk_sort_key(item.get("requirement_chunk_index", ""))
        )
        actual_requirement_file = str(
            items[0].get("requirement_file", "")
        ).strip() or requirement_group_key
        requirement_chunks = _aggregate_requirement_chunks(items)
        candidate_test_artifacts = _aggregate_test_artifacts_across_chunks(
            items, "candidate_test_artifacts"
        )
        verified_test_artifacts = _aggregate_test_artifacts_across_chunks(
            items, "verified_test_artifacts"
        )
        implemented_artifacts = _aggregate_implemented_artifacts_across_chunks(items)
        supporting_source_artifacts = _aggregate_supporting_source_artifacts_across_chunks(items)

        requirements.append({
            "requirement_id": requirement_group_key,
            "requirement_file": actual_requirement_file,
            "requirement_display_id": str(items[0].get("requirement_display_id", "")).strip() or requirement_group_key,
            "requirement_chunk_index": "",
            "requirement_chunk_label": "",
            "requirement_chunk_count": len(requirement_chunks),
            "requirement_text": _aggregate_requirement_text(items),
            "traceability_verdict": _aggregate_requirement_verdict(
                [item.get("traceability_verdict", "") for item in items]
            ),
            "requirement_reasoning": _aggregate_requirement_reasoning(items),
            "traceability_gap": any(bool(item.get("traceability_gap")) for item in items),
            "traceability_gap_reason": _aggregate_gap_reason(items),
            "traceability_error": None,
            "verified_test_count": sum(
                int(item.get("verified_test_count", 0) or 0)
                for item in items
            ),
            "candidate_test_artifact_count": len(candidate_test_artifacts),
            "verified_test_artifact_count": len(verified_test_artifacts),
            "candidate_test_judgments": [],
            "implemented_by_count": sum(
                int(item.get("implemented_by_count", 0) or 0)
                for item in items
            ),
            "implemented_artifact_count": len(implemented_artifacts),
            "supporting_source_artifact_count": len(supporting_source_artifacts),
            "stage2_debug": _aggregate_stage2_debug(items),
            "requirement_chunks": requirement_chunks,
            "candidate_test_artifacts": candidate_test_artifacts,
            "verified_test_artifacts": verified_test_artifacts,
            "verified_tests": [],
            "implemented_artifacts": implemented_artifacts,
            "implemented_by": [],
            "supporting_source_artifacts": supporting_source_artifacts,
            "supporting_sources": [],
            "traceability_report": None,
            "generated_at": generated_at,
        })

    requirement_id_counts: dict[str, int] = {}
    for requirement in requirements:
        display_id = str(requirement.get("requirement_display_id", "")).strip() or str(
            requirement.get("requirement_id", "")
        ).strip()
        requirement_id_counts[display_id] = requirement_id_counts.get(display_id, 0) + 1

    for requirement in requirements:
        display_id = str(requirement.get("requirement_display_id", "")).strip() or str(
            requirement.get("requirement_id", "")
        ).strip()
        if requirement_id_counts.get(display_id, 0) <= 1:
            requirement["requirement_id"] = display_id
            continue
        requirement_file = str(requirement.get("requirement_file", "")).strip()
        requirement["requirement_id"] = (
            f"{display_id} [{requirement_file}]"
            if requirement_file else display_id
        )

    requirements.sort(
        key=lambda requirement: (
            str(requirement.get("requirement_display_id", "")),
            str(requirement.get("requirement_file", "")),
        )
    )

    return {
        "meta": {
            **report.get("meta", {}),
            "generated_at": generated_at,
            "total_requirement_artifacts": len(requirements),
        },
        "requirements": requirements,
    }


def summarize_rows(rows: list[dict]) -> dict:
    accepted = sum(1 for row in rows if row.get("verdict") == "accepted")
    rejected = sum(1 for row in rows if row.get("verdict") == "rejected")
    full = sum(
        1
        for row in rows
        if row.get("verdict") == "accepted"
        and row.get("verdict_confidence") == "full"
    )
    partial = sum(
        1
        for row in rows
        if row.get("verdict") == "accepted"
        and row.get("verdict_confidence") == "partial"
    )
    weak = sum(
        1
        for row in rows
        if row.get("verdict") == "accepted"
        and row.get("verdict_confidence") == "weak"
    )
    return {
        "accepted": accepted,
        "rejected": rejected,
        "full": full,
        "partial": partial,
        "weak": weak,
    }


def traceability_saved_status() -> dict:
    report = load_traceability_report()
    if not report:
        return {
            "exists": False,
            "generated_at": None,
            "total_requirements": 0,
            "total_rows": 0,
            "accepted": 0,
            "rejected": 0,
            "full": 0,
            "partial": 0,
            "weak": 0,
            "covered": 0,
            "partially_covered": 0,
            "not_covered": 0,
            "completed_requirements": 0,
            "failed_requirements": 0,
            "pending_requirements": 0,
            "complete": False,
            "finalized": False,
        }

    rows = flatten_traceability_rows(report)
    counts = _traceability_requirement_counts(report)
    meta = report.get("meta", {})
    return {
        "exists": True,
        "generated_at": meta.get("generated_at"),
        "total_requirements": meta.get("total_requirements", len(report.get("traceability", []))),
        "total_rows": len(rows),
        "accepted": 0,
        "rejected": 0,
        "full": 0,
        "partial": 0,
        "weak": 0,
        **counts,
        "completed_requirements": meta.get("completed_requirements", len(report.get("traceability", []))),
        "failed_requirements": meta.get("failed_requirements", 0),
        "pending_requirements": meta.get("pending_requirements", 0),
        "complete": bool(meta.get("complete", True)),
        "finalized": bool(meta.get("finalized", True)),
    }


def assertion_saved_status() -> dict:
    report = load_assertion_report()
    if not report:
        return {
            "exists": False,
            "generated_at": None,
            "total_requirements": 0,
            "total_rows": 0,
            "accepted": 0,
            "rejected": 0,
            "full": 0,
            "partial": 0,
            "weak": 0,
            "traceability_generated_at": None,
            "fresh": False,
        }

    rows = report.get("assertions", [])
    counts = summarize_rows(rows)
    meta = report.get("meta", {})
    trace_generated_at = meta.get("traceability_generated_at")
    current_trace = load_traceability_report()
    current_trace_generated_at = None
    if current_trace:
        current_trace_generated_at = current_trace.get(
            "meta", {}).get("generated_at")

    return {
        "exists": True,
        "generated_at": meta.get("generated_at"),
        "total_requirements": meta.get("total_requirements", 0),
        "total_rows": len(rows),
        **counts,
        "traceability_generated_at": trace_generated_at,
        "fresh": bool(
            current_trace_generated_at
            and trace_generated_at == current_trace_generated_at
        ),
    }


def generated_tests_saved_status() -> dict:
    manifest = load_generated_tests_manifest()
    if not manifest:
        return {
            "exists": False,
            "generated_at": None,
            "traceability_generated_at": None,
            "assertion_generated_at": None,
            "total_gap_requirements": 0,
            "total_gap_groups": 0,
            "total_files": 0,
            "fresh": False,
            "files": [],
            "warnings": [],
        }

    meta = manifest.get("meta", {})
    current_assertion = load_assertion_report()
    current_assertion_generated_at = None
    if current_assertion:
        current_assertion_generated_at = current_assertion.get(
            "meta", {}).get("generated_at")

    files = []
    for item in manifest.get("files", []):
        files.append({
            "filename": item.get("filename", ""),
            "framework": item.get("framework", ""),
            "language": item.get("language", ""),
            "requirement_ids": item.get("requirement_ids", []),
            "gap_keys": item.get("gap_keys", []),
            "test_functions": item.get("test_functions", []),
        })

    return {
        "exists": True,
        "generated_at": meta.get("generated_at"),
        "traceability_generated_at": meta.get("traceability_generated_at"),
        "assertion_generated_at": meta.get("assertion_generated_at"),
        "total_gap_requirements": meta.get("total_gap_requirements", 0),
        "total_gap_groups": meta.get("total_gap_groups", 0),
        "total_files": meta.get("total_files", len(files)),
        "fresh": bool(
            current_assertion_generated_at
            and current_assertion_generated_at == meta.get("assertion_generated_at")
        ),
        "files": files,
        "warnings": manifest.get("warnings", []),
    }
