# Traceability Mapping — Implementation Flow

## Overview

Phase 3 takes every requirement ATU, pairs it with top candidates from Phase 2 retrieval, and asks GPT-5-mini to judge each pair as a valid traceability link. Output is `traceability_matrix.json`, consumed by the existing report builder.

---

## Pipeline (inside `run_reasoning_audit`)

### Step 1 — Fetch all requirement chunks and their candidates
- Call `retrieve_all_requirements()` from `services/retriever.py`
- Returns every requirement ATU with top-N tests and sources after dense recall + cross-encoder reranking
- No new retrieval logic needed

### Step 2 — Build (requirement, candidate) pairs
- For each requirement, flatten `tests` and `sources` lists into individual pairs
- Each pair carries: requirement text, candidate text, file name, candidate type, retrieval rank, rerank_score

### Step 3 — LLM judgment per pair
- Call GPT-5-mini via OpenAI API with JSON mode (`response_format=json_object`)
- Pre-filter: skip pairs where `rerank_score` is below a configurable threshold to avoid unnecessary LLM calls
- Prompt asks for three fields per pair:
  - `status` — `accepted` or `rejected`
  - `confidence` — float 0.0–1.0
  - `reasoning` — one sentence

### Step 4 — Write `traceability_matrix.json`
- Output path: `traceability/{project_id}/traceability_matrix.json`
- Schema (fixed by `_build_report()` in `routers/projects.py`):

```json
{
  "links": [
    {
      "requirement_id":  "string",
      "candidate_id":    "string",
      "candidate_type":  "test | source",
      "status":          "accepted | rejected",
      "confidence":      0.0,
      "source_file":     "string",
      "retrieval_rank":  0,
      "reasoning":       "string"
    }
  ]
}
```

- Only `status=accepted` links are persisted; rejected links are counted in the summary only

### Step 5 — Return summary dict
Shape defined by existing stub in `run_reasoning_audit.py`:
```python
{
    "total_requirements":   int,
    "covered_requirements": int,
    "evaluated_candidates": int,
    "accepted_links":       int,
    "rejected_candidates":  int,
    "suppressed_links":     int,   # pairs skipped by rerank_score threshold
}
```

---

## Integration Map

| Existing piece | Role in Phase 3 | Change needed |
|---|---|---|
| `services/retriever.py` → `retrieve_all_requirements()` | Provides all (requirement, candidates) pairs | None |
| `config.py` → `LLM_MODEL` | Model name for OpenAI call | Fix typo: `gpt-5-mini` → `gpt-4o-mini` |
| `routers/projects.py` → `_build_report()` | Reads `traceability_matrix.json`, renders report | None |
| `services/pipeline.py` → `run_phase3()` | Calls `run_reasoning_audit(project_id)`, handles errors | None |
| `config.py` → `TRACEABILITY_ROOT` | Output path for `traceability_matrix.json` | None |

**Only file to write:** `scripts/run_reasoning_audit.py`

---

## Retrieval Settings (at time of design)

| Parameter | Narrow | Medium | Broad |
|---|---|---|---|
| `top_k_recall` (per signal) | 60 | 100 | 150 |
| `pre_diverse_n` | 30 | 45 | 60 |
| `pre_max_per_file` | 2 | 2 | 3 |
| `top_k_final` | 12 | 18 | 25 |
| `DEFAULT_TOP_K_RECALL` | 40 | — | — |
| `DEFAULT_TOP_K_FINAL` | 10 | — | — |

---

## Open Decision

**Batching strategy** — one LLM call per pair (simple, slower) vs. multiple pairs per call (faster, harder to parse). One call per pair recommended for thesis scale.
