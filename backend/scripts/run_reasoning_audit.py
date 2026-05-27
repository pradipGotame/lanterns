"""
run_reasoning_audit.py
======================
Phase 3: LLM-assisted traceability mapping using GPT (model from config.LLM_MODEL).

Pipeline per requirement ATU
-----------------------------
1. Retrieve top test + source candidates via dense vector recall
   followed by FlashRank reranking — all synchronous (no event loop needed).
2. For each requirement call GPT with the requirement-level JSON prompt and
   receive a full `traceability_report`.
3. The raw LLM `traceability_report` objects are written to
   traceability/{project_id}/traceability_matrix.json exactly as returned by
   the model.

Called synchronously from services/pipeline.run_phase3(), which is itself
called from within a running FastAPI async handler.  All retrieval and
OpenAI calls here are synchronous.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import openai
from langchain_core.documents import Document

from config import LLM_MODEL, TRACEABILITY_ROOT
from services.embedder import embed_texts
from services.retriever import (
    FLASHRANK_META_PREFIX,
    RETRIEVAL_PARAMS,
    _rerank_sem,
    _get_flashrank_reranker,
    apply_test_safeguard,
    greedy_diversify,
    resolve_top_k_final,
)
from services.vector_store import get_store

# ── Prompts ───────────────────────────────────────────────────────────────────
# _AUDIT_SYSTEM_PROMPT = """
# You are a Senior Software Traceability Expert specializing in Verification and
# →
# Validation (V&V). Your task is to perform Trace Link Generation (TLG) between a high-level requirement, candidate test cases and supporting code.

# Determine whether a requirement is verified by tests and implemented by source code.
# Use only the provided evidence.
# Do not invent missing tests, requirements, assertions, or hidden behavior.
# Prefer semantic alignment over keyword overlap.
# A requirement may map to zero, one, or multiple tests.
# Be conservative. False positives are worse than false negatives.
# Confidence levels:
# - full: all stated behaviours, boundaries, and error paths are asserted
# - partial: core path covered, at least one stated behaviour or boundary missing
# - weak: topically related but no assertion directly verifies the requirement

# Verdict rules (derive — do not guess):

# - covered: at least one test is "full"
# - partially_covered: no "full" test, but at least one "partial"
# - not_covered: no "full" or "partial" test exists
# gap = true when verdict is partially_covered or not_covered.
# missing_scenarios must be [] when gap = false.
# evidence_inventory.verified_by_tests must be [] when no candidate tests were
# →
# retrieved.
# final_verdict must be not_covered when no candidate tests were retrieved.
# Respond with one valid JSON object. No markdown, no prose outside the JSON."""

_AUDIT_SYSTEM_PROMPT = """You are a Senior Software Traceability Expert specializing in Verification and Validation (V&V). Your task is to perform Trace Link Generation (TLG) between a high-level requirement, candidate test cases, and supporting source code.

## Core Rules
- Use only the provided evidence. Do not invent missing tests, requirements, assertions, or hidden behavior.
- Prefer semantic alignment over keyword overlap. A requirement may map to zero, one, or multiple tests/code functions.
- False negatives (missed gaps) are more costly than false positives.
- When evidence is ambiguous or incomplete, prefer not_covered.
- `candidate_test_judgments` must contain exactly one judgment for every object in `<candidate_tests>`, in the same order, reusing the exact `test_id` and `file` values from the input.
- `verified_by_tests` is the evidence subset only. Every item in `verified_by_tests` must also appear in `candidate_test_judgments`.
- Output **only** a single valid JSON object. No markdown, no explanatory prose outside the JSON.

## When evaluating test files, treat the following as assertion evidence:
- Any macro or function call that checks a return value against an expected outcome (e.g. ASSERT_*, CHECK_*, EXPECT_*, CU_ASSERT_*)
- Any function that invokes the system under test and then verifies the result with a boolean or comparison check
- Test helper functions that wrap assertions are still valid evidence

## Confidence levels:
- full: all stated behaviours, boundaries, and error paths are asserted
- partial: core path covered, at least one stated behaviour or boundary missing
- weak: topically related but no assertion directly verifies the requirement

## Gap Analysis Rules
- `gap_identified = true` when `final_verdict` is `"partially_covered"` or `"not_covered"`.
- `gap_identified = false` only when `final_verdict = "covered"`.
- When `gap_identified = false`, `missing_scenarios` must be an empty array `[]`, and `gap_rationale` must be an empty string `""`.- When `gap_identified = true`, `gap_rationale` must explain **exactly which part(s) of the requirement lack evidence**, and `missing_scenarios` must list concrete, actionable missing behaviors.
"""

_AUDIT_USER_TEMPLATE = """\
<requirement>
ID: {requirement_id} | File: {requirement_file_id} | Chunk: {requirement_chunk_id}
Text: {requirement_text}
</requirement>

<candidate_tests>
{candidate_tests_block}
</candidate_tests>

<supporting_code_context>
{supporting_code_block}
</supporting_code_context>

### Output Schema (Strict JSON)
{{
  "traceability_report": {{
    "requirement_id": "{requirement_id}",
    "requirement_text": "{requirement_text}",
    "reasoning_preamble": "Step-by-step extraction of facts from requirement and artifacts before making any judgment.",
    "candidate_test_judgments": [
      {{
        "test_id": "string",
        "file": "string or null",
        "verdict": "covered | partially_covered | not_covered",
        "line": 0,
        "matching_requirement_quotes": ["exact phrase from requirement"],
        "assertion_evidence_lines": ["exact assertion/code line from test"],
        "verification_confidence": "full | partial | weak",
        "reasoning": "Grounded judgment for this candidate test. Use empty evidence arrays when the candidate does not verify the requirement."
      }}
    ],
    "evidence_inventory": {{
      "verified_by_tests": [
        {{
          "test_id": "string",
          "file": "string or null",
          "verdict": "covered | partially_covered | not_covered",
          "line": 0,
          "matching_requirement_quotes": ["exact phrase from requirement"],
          "assertion_evidence_lines": ["exact assertion/code line from test"],
          "verification_confidence": "full | partial | weak",
          "reasoning": "How the quoted assertion logically satisfies the quoted requirement phrase."
        }}
      ],
      "implemented_by": [
        {{
          "function": "string",
          "file": "string or null",
          "implementation_confidence": "full | partial | weak",
          "reasoning": "Grounded explanation of how this code implements the requirement logic."
        }}
      ]
    }},
    "gap_analysis": {{
      "gap_identified": true,
      "missing_scenarios": [
        {{
          "behaviour": "string",
          "scenario": "string",
          "type": "boundary | negative | error_handling | state_transition | happy_path",
          "priority": "high | medium | low",
          "priority_rationale": "string"
        }}
      ],
      "gap_rationale": "Logical proof of why evidence in the inventory is insufficient."
    }},
    "final_verdict": "covered | partially_covered | not_covered",
  }}
}}"""

# ── OpenAI client ─────────────────────────────────────────────────────────────


def _get_client() -> openai.OpenAI:
    base_url = os.environ.get("OPENAI_BASE_URL") or None
    return openai.OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=base_url,
    )

# ── Synchronous retrieval ─────────────────────────────────────────────────────


def _retrieve_sync(req_text: str) -> dict[str, list[dict]]:
    """
    Full dense retrieval pipeline executed synchronously.

    Mirrors retrieve_for_requirement() from services/retriever.py but
    without async — safe to call from sync context inside an async server.

    Returns {"tests": [...], "sources": [...]} each sorted by rerank_score desc.
    """
    top_k = RETRIEVAL_PARAMS["top_k_recall"]
    pre_diverse_n = RETRIEVAL_PARAMS["pre_diverse_n"]
    pre_max_per_file = RETRIEVAL_PARAMS["pre_max_per_file"]
    top_k_final = RETRIEVAL_PARAMS["top_k_final"]

    store = get_store()

    # Stage 1 — dense recall (single embedding call, sync)
    vec: list[float] = embed_texts([req_text])[0]
    test_dense = store.search(vec, top_k=top_k, category="test")
    source_dense = store.search(vec, top_k=top_k, category="source")

    # Stage 1.5 — pre-diversify before reranking
    tests_pool = greedy_diversify(
        test_dense,   top_n=pre_diverse_n, max_per_file=pre_max_per_file)
    sources_pool = greedy_diversify(
        source_dense, top_n=pre_diverse_n, max_per_file=pre_max_per_file)

    # Stage 2 — FlashRank reranking (sync CPU call)
    reranker = _get_flashrank_reranker()

    def _rerank(pool: list[dict]) -> list[dict]:
        if not pool:
            return []
        docs = [
            Document(
                page_content=c["text"],
                metadata={k: v for k, v in c.items() if k != "text"},
            )
            for c in pool
        ]
        with _rerank_sem:
            ranked_docs = reranker.compress_documents(docs, query=req_text)

        score_key = f"{FLASHRANK_META_PREFIX}relevance_score"
        id_key = f"{FLASHRANK_META_PREFIX}id"
        ranked: list[dict] = []

        for doc in ranked_docs:
            meta = dict(doc.metadata)
            rerank_score = round(float(meta.pop(score_key, 0.0)), 6)
            meta.pop(id_key, None)
            ranked.append({
                **meta,
                "text": doc.page_content,
                "rerank_score": rerank_score,
            })

        return ranked

    tests_all = _rerank(tests_pool)
    sources_all = _rerank(sources_pool)
    effective_test_final = resolve_top_k_final(tests_all, top_k_final)
    effective_source_final = resolve_top_k_final(sources_all, top_k_final)
    tests_final, _ = apply_test_safeguard(
        test_dense,
        tests_all,
        top_n=effective_test_final,
    )
    sources_final = sources_all[:effective_source_final]

    return {
        "tests": tests_final,
        "sources": sources_final,
    }


def _json_block(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _requirement_id(meta: dict) -> str:
    return str(meta.get("atu_id") or meta.get("file_id") or "unknown")


def _requirement_file_id(meta: dict) -> str:
    return str(meta.get("file_id") or meta.get("file_name") or "")


def _requirement_chunk_id(meta: dict) -> str:
    if meta.get("chunk_index") is not None:
        return str(meta.get("chunk_index"))
    if meta.get("chunk_id") is not None:
        return str(meta.get("chunk_id"))
    return ""


def _candidate_test_id(candidate: dict) -> str:
    if candidate.get("atu_id"):
        return str(candidate["atu_id"])
    if candidate.get("file_name"):
        return f"{candidate.get('file_name', '')}::chunk{candidate.get('chunk_index', '')}"
    return str(candidate.get("file_id", ""))


def _candidate_source_id(candidate: dict) -> str:
    if candidate.get("atu_id"):
        return str(candidate["atu_id"])
    if candidate.get("file_name"):
        return f"{candidate.get('file_name', '')}::chunk{candidate.get('chunk_index', '')}"
    return str(candidate.get("file_id", ""))


def _candidate_test_prompt_rows(candidates: list[dict]) -> list[dict]:
    return [
        {
            "test_id": _candidate_test_id(candidate),
            "file": candidate.get("file_name") or None,
            "file_id": candidate.get("file_id") or None,
            "chunk_id": candidate.get("chunk_index", ""),
            "test_chunk_text": candidate.get("text", ""),
        }
        for candidate in candidates
    ]


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _candidate_test_ref(item: dict) -> tuple[str, str | None]:
    return (
        str(item.get("test_id", "")).strip(),
        _normalize_optional_str(item.get("file")),
    )


def _normalize_candidate_test_verdict(value: Any) -> str:
    verdict = str(value or "").strip().lower().replace(
        "-", "_").replace(" ", "_")
    if verdict in {"covered", "partially_covered", "not_covered"}:
        return verdict
    return {
        "full": "covered",
        "partial": "partially_covered",
        "weak": "not_covered",
        "partiallycovered": "partially_covered",
        "notcovered": "not_covered",
    }.get(verdict, verdict)


def _normalize_candidate_test_confidence(value: Any) -> str:
    confidence = str(value or "").strip().lower().replace(
        "-", "_").replace(" ", "_")
    if confidence in {"full", "partial", "weak"}:
        return confidence
    return {
        "covered": "full",
        "partially_covered": "partial",
        "partiallycovered": "partial",
        "not_covered": "weak",
        "notcovered": "weak",
    }.get(confidence, confidence)


def _default_candidate_test_judgment(candidate_test: dict) -> dict:
    return {
        "test_id": str(candidate_test.get("test_id", "")).strip(),
        "file": _normalize_optional_str(candidate_test.get("file")),
        "verdict": "not_covered",
        "line": 0,
        "matching_requirement_quotes": [],
        "assertion_evidence_lines": [],
        "verification_confidence": "weak",
        "reasoning": (
            "No valid per-candidate judgment was returned for this test in the "
            "LLM response, so it was conservatively defaulted to not_covered."
        ),
    }


def _repair_candidate_test_judgments(report: dict, candidate_tests: list[dict]) -> dict:
    if not isinstance(report, dict):
        return report

    judgments = report.get("candidate_test_judgments", [])
    if not isinstance(judgments, list):
        judgments = []

    buckets: dict[tuple[str, str | None], list[dict]] = {}
    for item in judgments:
        if not isinstance(item, dict):
            continue
        ref = _candidate_test_ref(item)
        if not ref[0]:
            continue
        buckets.setdefault(ref, []).append(dict(item))

    repaired_judgments: list[dict] = []
    expected_refs = [_candidate_test_ref(item) for item in candidate_tests]
    for candidate_test, ref in zip(candidate_tests, expected_refs):
        bucket = buckets.get(ref, [])
        repaired = bucket.pop(
            0) if bucket else _default_candidate_test_judgment(candidate_test)
        repaired["test_id"] = ref[0]
        repaired["file"] = ref[1]
        repaired["verdict"] = _normalize_candidate_test_verdict(
            repaired.get("verdict", "")
        )
        repaired["verification_confidence"] = _normalize_candidate_test_confidence(
            repaired.get("verification_confidence", "")
        )
        repaired_judgments.append(repaired)
    report["candidate_test_judgments"] = repaired_judgments

    evidence_inventory = report.get("evidence_inventory")
    if not isinstance(evidence_inventory, dict):
        evidence_inventory = {}
        report["evidence_inventory"] = evidence_inventory

    verified_by_tests = evidence_inventory.get("verified_by_tests", [])
    repaired_verified: list[dict] = []
    if isinstance(verified_by_tests, list):
        remaining_by_ref: dict[tuple[str, str | None], int] = {}
        for ref in expected_refs:
            remaining_by_ref[ref] = remaining_by_ref.get(ref, 0) + 1

        for item in verified_by_tests:
            if not isinstance(item, dict):
                continue
            ref = _candidate_test_ref(item)
            remaining = remaining_by_ref.get(ref, 0)
            if remaining <= 0:
                continue
            repaired_item = dict(item)
            repaired_item["test_id"] = ref[0]
            repaired_item["file"] = ref[1]
            repaired_item["verdict"] = _normalize_candidate_test_verdict(
                repaired_item.get("verdict", "")
            )
            repaired_item["verification_confidence"] = _normalize_candidate_test_confidence(
                repaired_item.get("verification_confidence", "")
            )
            repaired_verified.append(repaired_item)
            remaining_by_ref[ref] = remaining - 1
    evidence_inventory["verified_by_tests"] = repaired_verified

    implemented_by = evidence_inventory.get("implemented_by", [])
    if not isinstance(implemented_by, list):
        evidence_inventory["implemented_by"] = []

    return report


def _validate_candidate_test_judgments(report: dict, candidate_tests: list[dict]) -> None:
    judgments = report.get("candidate_test_judgments")
    if not isinstance(judgments, list):
        raise ValueError(
            "Missing candidate_test_judgments list in LLM response")

    expected_refs = [
        _candidate_test_ref(item)
        for item in candidate_tests
    ]
    actual_refs: list[tuple[str, str | None]] = []
    for item in judgments:
        if not isinstance(item, dict):
            raise ValueError(
                "candidate_test_judgments must contain only objects")
        test_id = str(item.get("test_id", "")).strip()
        verdict = str(item.get("verdict", "")).strip().lower()
        confidence = str(
            item.get("verification_confidence", "")).strip().lower()
        if not test_id:
            raise ValueError(
                "candidate_test_judgments contains an item with empty test_id")
        if verdict not in {"covered", "partially_covered", "not_covered"}:
            raise ValueError(f"Invalid candidate test verdict: {verdict!r}")
        if confidence not in {"full", "partial", "weak"}:
            raise ValueError(
                f"Invalid candidate test verification_confidence: {confidence!r}")
        actual_refs.append(
            (test_id, _normalize_optional_str(item.get("file"))))

    if actual_refs != expected_refs:
        raise ValueError(
            "candidate_test_judgments must exactly match the sent candidate_tests "
            f"in order and membership. expected={expected_refs!r} actual={actual_refs!r}"
        )

    evidence_inventory = report.get("evidence_inventory", {})
    if not isinstance(evidence_inventory, dict):
        raise ValueError("Missing evidence_inventory object in LLM response")
    verified_by_tests = evidence_inventory.get("verified_by_tests", [])
    if isinstance(verified_by_tests, list):
        valid_refs = set(actual_refs)
        for item in verified_by_tests:
            if not isinstance(item, dict):
                raise ValueError("verified_by_tests must contain only objects")
            ref = (
                str(item.get("test_id", "")).strip(),
                _normalize_optional_str(item.get("file")),
            )
            if ref not in valid_refs:
                raise ValueError(
                    "verified_by_tests item was not present in candidate_test_judgments: "
                    f"{ref!r}"
                )


def _build_traceability_prompt(req_text: str, req_meta: dict, candidates: dict[str, list[dict]]) -> str:
    candidate_tests = _candidate_test_prompt_rows(candidates.get("tests", []))
    supporting_code = [
        {
            "source_id": _candidate_source_id(candidate),
            "file": candidate.get("file_name") or None,
            "file_id": candidate.get("file_id") or None,
            "chunk_id": candidate.get("chunk_index", ""),
            "source_chunk_text": candidate.get("text", ""),
        }
        for rank, candidate in enumerate(candidates.get("sources", []), start=1)
    ]

    return _AUDIT_USER_TEMPLATE.format(
        requirement_id=_requirement_id(req_meta),
        requirement_file_id=_requirement_file_id(req_meta),
        requirement_chunk_id=_requirement_chunk_id(req_meta),
        requirement_text=req_text,
        candidate_tests_block=_json_block(candidate_tests),
        supporting_code_block=_json_block(supporting_code),
    )


def _run_requirement_audit(
    req_text: str,
    req_meta: dict,
    candidates: dict[str, list[dict]],
    client: openai.OpenAI,
) -> dict:
    req_id = _requirement_id(req_meta)
    candidate_tests = _candidate_test_prompt_rows(candidates.get("tests", []))
    prompt = _build_traceability_prompt(req_text, req_meta, candidates)

    print(
        f"[LLM →] {LLM_MODEL} | requirement={req_id} | "
        f"tests={len(candidates.get('tests', []))} | sources={len(candidates.get('sources', []))}"
    )

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                response_format={"type": "json_object"},
                temperature=1,
                messages=[
                    {"role": "system", "content": _AUDIT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            payload = json.loads(resp.choices[0].message.content)
            report = payload.get("traceability_report")
            if not isinstance(report, dict):
                raise ValueError(
                    "Missing traceability_report object in LLM response")
            report = _repair_candidate_test_judgments(report, candidate_tests)
            _validate_candidate_test_judgments(report, candidate_tests)

            print(
                f"[LLM ←] requirement={req_id} | "
                f"verdict={report.get('final_verdict', '')}"
            )
            return report
        except Exception as exc:
            last_error = exc
            print(f"[LLM ✗] requirement={req_id} | error={exc}")
            if attempt == 0:
                continue
            raise RuntimeError(
                f"Traceability audit returned an invalid response after retry: {exc}"
            ) from exc

    raise RuntimeError(
        f"Traceability audit failed without a valid response: {last_error}"
    )


# ── LLM judgment ──────────────────────────────────────────────────────────────

def _build_single_candidate_audit_prompt(
    req_text: str,
    cand_text: str,
    cand_type: str,
) -> tuple[str, list[dict]]:
    req_meta = {
        "atu_id": "adhoc_requirement",
        "file_id": "adhoc_requirement",
        "chunk_index": 0,
    }
    candidate = {
        "text": cand_text,
        "file_name": f"{cand_type}_candidate",
        "file_id": f"{cand_type}_candidate",
        "chunk_index": 0,
    }
    candidates = {
        "tests": [candidate] if cand_type == "test" else [],
        "sources": [candidate] if cand_type != "test" else [],
    }
    prompt = _build_traceability_prompt(req_text, req_meta, candidates)
    return prompt, _candidate_test_prompt_rows(candidates["tests"])


def _judge_link(
    req_text:  str,
    cand_text: str,
    cand_type: str,
    client:    openai.OpenAI,
    _log=None,
    log_label=None,
) -> dict:
    """
    Call GPT to judge a single (requirement, candidate) pair.

    Returns:
        {
            "verdict":          "covered" | "partially_covered" | "not_covered",
            "confidence":       direct LLM confidence label,
            "reasoning":        str,

            "status":           "accepted" | "rejected",  # legacy compatibility
            "confidence_label": direct LLM confidence label,  # legacy compatibility
        }
    Invalid/missing responses trigger a retry and then fail the run.
    """
    # Log the outgoing request to the LLM
    req_preview = req_text[:60].replace("\n", " ")
    cand_preview = cand_text[:60].replace("\n", " ")
    print(
        f"[LLM →] {LLM_MODEL} | type={cand_type} | req='{req_preview}…' | cand='{cand_preview}…'")
    if _log and log_label:
        _log(f"LLM →  {log_label}  ({cand_type})")

    prompt, candidate_tests = _build_single_candidate_audit_prompt(
        req_text, cand_text, cand_type
    )
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                response_format={"type": "json_object"},
                temperature=1,  # gpt-5-mini only supports temperature=1
                messages=[
                    {"role": "system", "content": _AUDIT_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            payload = json.loads(resp.choices[0].message.content)
            report = payload.get("traceability_report")
            if not isinstance(report, dict):
                raise ValueError(
                    "Missing traceability_report object in LLM response")

            if candidate_tests:
                _validate_candidate_test_judgments(report, candidate_tests)
                judgments = report.get("candidate_test_judgments", [])
                if not isinstance(judgments, list) or not judgments:
                    raise ValueError(
                        "Missing candidate_test_judgments in LLM response")
                result = judgments[0]
                verdict = str(result.get("verdict", "")).strip().lower()
                confidence = str(result.get(
                    "verification_confidence", "")).strip().lower()
                reasoning = str(result.get("reasoning", "")).strip()
            else:
                evidence_inventory = report.get("evidence_inventory", {})
                if not isinstance(evidence_inventory, dict):
                    evidence_inventory = {}
                implemented_by = evidence_inventory.get("implemented_by", [])
                if not isinstance(implemented_by, list):
                    implemented_by = []
                result = implemented_by[0] if implemented_by else {}
                confidence = str(result.get(
                    "implementation_confidence", "weak")).strip().lower() or "weak"
                verdict = {
                    "full": "covered",
                    "partial": "partially_covered",
                    "weak": "not_covered",
                }.get(confidence, "not_covered")
                reasoning = str(result.get("reasoning", "")).strip() or str(
                    report.get("reasoning_preamble", "")
                ).strip()

            confidence_label = confidence
            status = "accepted" if confidence in {
                "full", "partial"} else "rejected"
            try:
                confidence_score = float(report.get(
                    "global_confidence_score", 0.0))
            except (TypeError, ValueError):
                confidence_score = {
                    "full": 1.0,
                    "partial": 0.5,
                    "weak": 0.0,
                }.get(confidence, 0.0)

            if verdict not in {"covered", "partially_covered", "not_covered"}:
                raise ValueError(f"Invalid or missing verdict: {verdict!r}")
            if confidence not in {"full", "partial", "weak"}:
                raise ValueError(
                    f"Invalid or missing confidence: {confidence!r}")
            if confidence_label not in {"full", "partial", "weak"}:
                raise ValueError(
                    f"Invalid or missing confidence_label: {confidence_label!r}")
            if status not in {"accepted", "rejected"}:
                raise ValueError(f"Invalid or missing status: {status!r}")
            if not reasoning:
                raise ValueError("Missing reasoning in LLM response")

            print(
                f"[LLM ←] verdict={verdict} | confidence={confidence} | reasoning='{reasoning[:80]}…'")
            if _log and log_label:
                _log(
                    f"LLM ←  {log_label}  ({cand_type})  "
                    f"verdict={verdict}  confidence={confidence}"
                )

            return {
                "verdict": verdict,
                "confidence": confidence,
                "reasoning": reasoning,
                "status": status,
                "confidence_label": confidence_label,
            }

        except Exception as exc:
            last_error = exc
            print(f"[LLM ✗] call failed: {exc}")
            if _log and log_label:
                _log(f"LLM ✗  {log_label}  ({cand_type})  error={exc}")
            if attempt == 0:
                continue
            raise RuntimeError(
                f"Traceability judge returned an invalid response after retry: {exc}"
            ) from exc

    raise RuntimeError(
        f"Traceability judge failed without a valid response: {last_error}"
    )

# ── Main entry point ──────────────────────────────────────────────────────────


def run_reasoning_audit(project_id: str) -> dict:
    """
    Run the full Phase 3 traceability mapping for *project_id*.

    Reads requirement ATUs from the vector store (filtered by project_id),
    retrieves candidates, requests a requirement-level traceability report
    from GPT, and writes
    traceability/{project_id}/traceability_matrix.json.

    Returns a summary dict matching the shape expected by pipeline.run_phase3().
    """
    store = get_store()

    # ── Requirement ATUs for this project only ────────────────────────────────
    req_chunks: list[tuple[str, dict]] = [
        (text, meta)
        for text, meta in store.get_chunks_by_category("requirement")
        if meta.get("project_id") == project_id
    ]

    if not req_chunks:
        print(
            f"[Phase3] {project_id}: no requirement ATUs in index — skipping")
        return {
            "traceability_reports": [],
        }

    client = _get_client()
    reports: list[dict] = []

    print(
        f"[Phase3] {project_id}: auditing {len(req_chunks)} requirement ATUs…")

    for req_text, req_meta in req_chunks:
        req_id = req_meta.get("atu_id") or req_meta.get("file_id", "unknown")

        # ── Retrieve candidates ───────────────────────────────────────────────
        try:
            candidates = _retrieve_sync(req_text)
        except Exception as exc:
            print(f"[Phase3] retrieval failed for {req_id}: {exc}")
            continue

        try:
            report = _run_requirement_audit(
                req_text, req_meta, candidates, client)
        except Exception as exc:
            print(f"[Phase3] audit failed for {req_id}: {exc}")
            continue

        reports.append(report)

    # ── Write traceability_matrix.json ────────────────────────────────────────
    out_dir: Path = TRACEABILITY_ROOT / project_id
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "traceability_matrix.json").write_text(
        json.dumps(
            {
                "traceability_reports": reports,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"[Phase3] {project_id}: done — raw traceability reports saved")

    return {
        "traceability_reports": reports,
    }
