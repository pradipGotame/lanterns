"""
services/retriever.py
=====================
Three-stage traceability retrieval pipeline.

Stage 1 — Dense recall
  Embeds the requirement query with OpenAI (one API call).
  Searches the vector index for top-K candidates per category using
  cosine similarity over L2-normalised vectors.
  Returns candidates with "score" (higher = more similar).

Stage 2 — FlashRank reranking
  Scores every (query, candidate_text) pair through LangChain's FlashRank
  wrapper using the ms-marco-MiniLM-L-12-v2 reranker.
  Keeps only top-5 per category.
  Runs on CPU, is loaded once and cached.
  Returns candidates with "rerank_score" (higher = more relevant).

Full pipeline:
  query (str)
    ──► embed_single()                              [OpenAI API, ~200 ms]
    ──► store.search(vec, category="test")          [Vector search, < 1 ms]
    ──► rerank_candidates(query, dense hits)        [FlashRank reranker]
    ──► top-5 test results

  (same in parallel for category="source")
"""

from __future__ import annotations

import asyncio
import os
import threading
from functools import lru_cache

from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
from langchain_core.documents import Document

from services.embedder import embed_single, embed_texts
from services.vector_store import get_store

# The FlashRank model is CPU-bound and shared across requests. Serialising
# inference keeps concurrent rerank calls from contending over the same
# cached model instance while preserving the async API.
_rerank_sem = threading.Semaphore(1)

# ── Config ────────────────────────────────────────────────────────────────────

RERANK_MODEL = "ms-marco-MiniLM-L-12-v2"
FLASHRANK_TOP_N_MAX = 256
FLASHRANK_META_PREFIX = "flashrank_"
CROSS_ENCODER_MODEL = RERANK_MODEL
DEFAULT_TOP_K_RECALL = 40   # dense candidates per category (Stage 1)
DEFAULT_TOP_K_FINAL = 10   # results kept after reranking (Stage 2)
SAFEGUARD_STAGE1_RANK_MAX = 5
SAFEGUARD_MAX_EXTRA = 3
SAFEGUARD_PREFER_UNIQUE_FILES = True
TRACE_DYNAMIC_TOP_K_FINAL_ENV = "TRACE_DYNAMIC_TOP_K_FINAL"
# TRACE_DYNAMIC_TOP_K_FINAL_MIN = 12
# TRACE_DYNAMIC_TOP_K_FINAL_EXTRA = 8
# TRACE_DYNAMIC_TOP_K_FINAL_RELATIVE_FLOOR = 0.80
# TRACE_DYNAMIC_TOP_K_FINAL_MAX_DROP = 0.05

# RETRIEVAL_PARAMS = {
#     "top_k_recall": 100,
#     "pre_diverse_n": 45,
#     "pre_max_per_file": 8,
#     "top_k_final": 35,
# }

TRACE_DYNAMIC_TOP_K_FINAL_MIN = 3
TRACE_DYNAMIC_TOP_K_FINAL_EXTRA = 1
TRACE_DYNAMIC_TOP_K_FINAL_RELATIVE_FLOOR = 0.84
TRACE_DYNAMIC_TOP_K_FINAL_MAX_DROP = 0.04

RETRIEVAL_PARAMS = {
    "top_k_recall": 100,
    "pre_diverse_n": 45,
    "pre_max_per_file": 8,
    "top_k_final": 32,
}

# ── Requirement classifier ────────────────────────────────────────────────────


def classify_requirement(text: str) -> str:
    """
    Classify a requirement chunk as 'narrow', 'medium', or 'broad' by word count.

    Thresholds are calibrated for 500-character RecursiveCharacterTextSplitter
    chunks, where:
      < 30 words  → narrow  (single short clause, e.g. one-sentence sub-requirement)
      < 70 words  → medium  (a few sentences covering one concern)
      ≥ 70 words  → broad   (full paragraph, header + multiple sub-clauses)

    Retained for report metadata and debugging labels.
    """
    words = len(text.split())
    if words < 30:
        return "narrow"
    elif words < 70:
        return "medium"
    return "broad"


def greedy_diversify(
    candidates:   list[dict],
    top_n:        int,
    max_per_file: int = 2,
) -> list[dict]:
    """
    Deterministic Greedy Re-ranking (Group-By) for result diversification.

    Algorithm:
      1. Receive candidates already sorted by descending relevance
         (for example Stage 1 cosine `score` or Stage 2 `rerank_score`).
      2. Walk them in order, maintaining a per-file chunk count.
      3. Skip a candidate if its file_name already has max_per_file chunks
         in the result list.
      4. Stop as soon as top_n results are collected.

    This guarantees:
      - Relevance order is preserved (no score recomputation).
      - No single file dominates the final list.
      - Deterministic — same input always produces the same output.

    Args:
        candidates:   Candidate pool sorted by descending relevance.
        top_n:        Maximum results to return.
        max_per_file: Maximum chunks allowed from any single file_name.

    Returns:
        Up to top_n diverse candidates in relevance order.
    """
    seen:   dict[str, int] = {}   # file_name → chunk count in result
    result: list[dict] = []

    for c in candidates:
        fname = c.get("file_name", "")
        if seen.get(fname, 0) >= max_per_file:
            continue
        seen[fname] = seen.get(fname, 0) + 1
        result.append(c)
        if len(result) >= top_n:
            break

    return result


def _candidate_key(candidate: dict) -> tuple[str, str]:
    file_id = str(candidate.get("file_id", "")).strip()
    chunk_index = str(candidate.get("chunk_index", "")).strip()
    if file_id:
        return (file_id, chunk_index)
    return (str(candidate.get("file_name", "")).strip(), chunk_index)


def _candidate_file(candidate: dict) -> str:
    return str(candidate.get("file_name", "")).strip()


def dynamic_top_k_final_enabled() -> bool:
    raw = str(os.environ.get(TRACE_DYNAMIC_TOP_K_FINAL_ENV, "1")).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _candidate_rerank_score(candidate: dict) -> float | None:
    try:
        return float(candidate.get("rerank_score"))
    except (TypeError, ValueError):
        return None


def resolve_top_k_final(reranked_candidates: list[dict], base_final: int) -> int:
    """
    Resolve the final post-rerank slice size.

    By default this uses a score-aware dynamic window that keeps a minimum
    stable prefix and expands only while rerank quality stays close to the
    leading results. Set TRACE_DYNAMIC_TOP_K_FINAL=0 to revert instantly to
    the static base_final behavior.
    """
    if not reranked_candidates:
        return 0

    capped_base = max(1, min(int(base_final), len(reranked_candidates)))
    if not dynamic_top_k_final_enabled():
        return capped_base

    top_score = _candidate_rerank_score(reranked_candidates[0])
    if top_score is None:
        return capped_base

    min_final = min(
        len(reranked_candidates),
        max(TRACE_DYNAMIC_TOP_K_FINAL_MIN, capped_base - 4),
    )
    max_final = min(
        len(reranked_candidates),
        capped_base + TRACE_DYNAMIC_TOP_K_FINAL_EXTRA,
    )
    if max_final < min_final:
        max_final = min_final

    resolved = min_final
    previous_score = _candidate_rerank_score(reranked_candidates[resolved - 1])
    if previous_score is None:
        return capped_base

    for idx in range(resolved, max_final):
        current_score = _candidate_rerank_score(reranked_candidates[idx])
        if current_score is None:
            break
        if current_score < (TRACE_DYNAMIC_TOP_K_FINAL_RELATIVE_FLOOR * top_score):
            break
        if (previous_score - current_score) > TRACE_DYNAMIC_TOP_K_FINAL_MAX_DROP:
            break
        resolved += 1
        previous_score = current_score

    return max(1, resolved)


def apply_test_safeguard(
    stage1_candidates: list[dict],
    reranked_candidates: list[dict],
    top_n: int,
    *,
    stage1_rank_max: int = SAFEGUARD_STAGE1_RANK_MAX,
    max_extra: int = SAFEGUARD_MAX_EXTRA,
    prefer_unique_files: bool = SAFEGUARD_PREFER_UNIQUE_FILES,
) -> tuple[list[dict], list[dict]]:
    """
    Preserve a small number of strong Stage 1 hits that would otherwise be lost
    before the final judged test set.

    The normal reranked top-N remains the primary path. We only append up to
    ``max_extra`` promoted candidates from the Stage 1 fused list when they rank
    highly there and are absent from the current final set.
    """
    base_final = [
        {
            **item,
            "safeguard_promoted": bool(item.get("safeguard_promoted", False)),
        }
        for item in reranked_candidates[:top_n]
    ]
    if not stage1_candidates or max_extra <= 0 or stage1_rank_max <= 0:
        return base_final, []

    base_keys = {_candidate_key(item) for item in base_final}
    base_files = {
        _candidate_file(item)
        for item in base_final
        if _candidate_file(item)
    }
    reranked_by_key = {
        _candidate_key(item): item
        for item in reranked_candidates
    }

    eligible: list[dict] = []
    for stage1_rank, item in enumerate(stage1_candidates[:stage1_rank_max], start=1):
        key = _candidate_key(item)
        if key in base_keys:
            continue

        reranked_match = reranked_by_key.get(key, {})
        eligible.append({
            **item,
            "score": reranked_match.get("score", item.get("score", "")),
            "rerank_score": reranked_match.get("rerank_score", item.get("rerank_score", "")),
            "safeguard_promoted": True,
            "safeguard_reason": "high_stage1_rank_not_in_final",
            "stage1_rank": stage1_rank,
        })

    promoted: list[dict] = []
    promoted_keys: set[tuple[str, str]] = set()

    def _try_promote(candidate: dict) -> None:
        key = _candidate_key(candidate)
        if key in promoted_keys or key in base_keys or len(promoted) >= max_extra:
            return
        promoted.append(candidate)
        promoted_keys.add(key)

    if prefer_unique_files:
        for candidate in eligible:
            file_name = _candidate_file(candidate)
            if file_name and file_name in base_files:
                continue
            _try_promote(candidate)
            if len(promoted) >= max_extra:
                break

    if len(promoted) < max_extra:
        for candidate in eligible:
            _try_promote(candidate)
            if len(promoted) >= max_extra:
                break

    return base_final + promoted, promoted

# ── Stage 1 — Dense recall ────────────────────────────────────────────────────


async def recall_for_requirement(
    query: str,
    top_k: int = DEFAULT_TOP_K_RECALL,
) -> dict:
    """
    Stage 1 — Dense vector recall.

    Embeds *query* with OpenAI (single API call, offloaded to thread pool),
    then runs vector search in parallel for the "test" and "source"
    categories.

    Args:
        query: Requirement text used as the search query.
        top_k: Candidates to retrieve per category.

    Returns:
        {
            "query":   str,
            "top_k":   int,
            "tests":   [{ text, file_name, file_id, category,
                          chunk_index, chunk_size, score }, ...],
            "sources": [{ same fields }],
        }
        Results are ordered by descending cosine-similarity score.
    """
    loop = asyncio.get_event_loop()
    store = get_store()

    # One OpenAI embedding call for the query
    query_vec: list[float] = await loop.run_in_executor(None, embed_single, query)

    # Vector search in parallel for both categories.
    test_dense, source_dense = await asyncio.gather(
        loop.run_in_executor(
            None, lambda: store.search(query_vec, top_k=top_k, category="test")
        ),
        loop.run_in_executor(
            None, lambda: store.search(
                query_vec, top_k=top_k, category="source")
        ),
    )

    return {
        "query":   query,
        "top_k":   top_k,
        "tests":   test_dense,
        "sources": source_dense,
    }


async def recall_with_vector(
    query:     str,
    query_vec: list[float],
    top_k:     int = DEFAULT_TOP_K_RECALL,
) -> dict:
    """
    Stage 1 — Dense recall using a *pre-computed* embedding vector.

    Same as recall_for_requirement() but skips the OpenAI API call.
    Used by the batch report pipeline where all embeddings are computed
    upfront in a single API call.
    """
    loop = asyncio.get_event_loop()
    store = get_store()

    test_dense, source_dense = await asyncio.gather(
        loop.run_in_executor(
            None, lambda: store.search(query_vec, top_k=top_k, category="test")
        ),
        loop.run_in_executor(
            None, lambda: store.search(
                query_vec, top_k=top_k, category="source")
        ),
    )

    return {
        "query":   query,
        "top_k":   top_k,
        "tests":   test_dense,
        "sources": source_dense,
    }


async def batch_embed_requirements(
    texts: list[str],
) -> list[list[float]]:
    """
    Embed all requirement texts in a single OpenAI API call.
    Returns vectors in the same order as *texts*.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, embed_texts, texts)


async def recall_all_requirements(
    top_k: int = DEFAULT_TOP_K_RECALL,
) -> list[dict]:
    """
    Run Stage 1 recall for every requirement chunk in the vector store.

    Processed sequentially to stay within OpenAI embedding rate limits.
    Returns records sorted by (req_file, chunk_index).
    """
    store = get_store()
    req_chunks = store.get_chunks_by_category("requirement")

    if not req_chunks:
        return []

    results: list[dict] = []
    for text, meta in req_chunks:
        record = await recall_for_requirement(text, top_k=top_k)
        record["req_file"] = meta.get("file_name", "")
        record["chunk_index"] = meta.get("chunk_index", 0)
        results.append(record)

    return sorted(
        results,
        key=lambda r: (r.get("req_file", ""), r.get("chunk_index", 0)),
    )


# ── Stage 2 — FlashRank reranking ────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_flashrank_reranker() -> FlashrankRerank:
    """
    Load and cache the LangChain FlashRank reranker.
    """
    print(
        f"[retriever] Loading FlashRank reranker: {RERANK_MODEL}  (once per process)")
    return FlashrankRerank(
        model=RERANK_MODEL,
        top_n=FLASHRANK_TOP_N_MAX,
        score_threshold=0.0,
        prefix_metadata=FLASHRANK_META_PREFIX,
    )


def _get_cross_encoder() -> FlashrankRerank:
    """Backward-compatible alias for older internal imports."""
    return _get_flashrank_reranker()


async def rerank_candidates(
    query:      str,
    candidates: list[dict],
    top_n:      int = DEFAULT_TOP_K_FINAL,
) -> list[dict]:
    """
    Stage 2 — FlashRank reranking.

    Takes a flat list of candidate dicts (output of store.search / Stage 1)
    and re-scores every candidate using LangChain's FlashRank wrapper.

    Like a cross-encoder, FlashRank reads the query and candidate together
    during reranking, which makes it much more precise than Stage 1 recall.

    Scoring runs in a thread-pool executor because it is CPU-bound.

    Args:
        query:      The original requirement query string.
        candidates: List of dicts, each with at least a "text" field.
                    The existing "score" (cosine) is preserved.
        top_n:      Number of top results to keep after reranking (default 5).

    Returns:
        Top-*top_n* candidates sorted by descending "rerank_score".
        Each dict keeps all original fields and gains:
          "rerank_score": float   — FlashRank relevance score (higher = more relevant)
    """

    if not candidates:
        return []

    reranker = _get_flashrank_reranker()
    loop = asyncio.get_event_loop()

    docs = [
        Document(
            page_content=candidate["text"],
            metadata={k: v for k, v in candidate.items() if k != "text"},
        )
        for candidate in candidates
    ]

    def _rerank_guarded() -> list[dict]:
        with _rerank_sem:
            ranked_docs = reranker.compress_documents(
                docs, query=query)[:top_n]

        scored: list[dict] = []
        score_key = f"{FLASHRANK_META_PREFIX}relevance_score"
        id_key = f"{FLASHRANK_META_PREFIX}id"

        for doc in ranked_docs:
            meta = dict(doc.metadata)
            rerank_score = round(float(meta.pop(score_key, 0.0)), 6)
            meta.pop(id_key, None)
            scored.append({
                **meta,
                "text": doc.page_content,
                "rerank_score": rerank_score,
            })
        return scored

    return await loop.run_in_executor(None, _rerank_guarded)


# ── Full pipeline (Stage 1 + Stage 2) ────────────────────────────────────────

async def retrieve_for_requirement(
    query:            str,
    top_k_recall:     int = RETRIEVAL_PARAMS["top_k_recall"],
    top_k_final:      int = RETRIEVAL_PARAMS["top_k_final"],
    requirement_type: str | None = None,
) -> dict:
    """
    Full two-stage retrieval for a single requirement query.

    Uses one fixed retrieval configuration for every requirement chunk.
    `requirement_type` is retained only as an optional metadata label.

    Stage 1: embed query once, dense vector recall (fixed top_k) per category.
    Stage 2: FlashRank reranks both category lists concurrently.
    Stage 3: diversity enforcement — fills up to min_test_files unique
             test-file names from the Stage 1 pool if reranking left gaps.

    Returns:
        {
            "query":            str,
            "requirement_type": "narrow" | "medium" | "broad",
            "tests":   [{ text, file_name, file_id, category, chunk_index,
                          score (cosine), rerank_score, diversity_fill? }, ...],
            "sources": [{ same fields }],
        }
    """
    req_type = requirement_type or classify_requirement(query)
    eff_recall = top_k_recall
    pre_diverse_n = RETRIEVAL_PARAMS["pre_diverse_n"]
    pre_max_per_file = RETRIEVAL_PARAMS["pre_max_per_file"]
    eff_final = top_k_final

    # Stage 1 — dense over-fetch (large pool, cosine similarity, no neural cost)
    recall = await recall_for_requirement(query, top_k=eff_recall)

    # Stage 1.5 — pre-diversify BEFORE reranking
    # Dense recall results are already sorted by cosine score descending.
    # greedy_diversify walks them in order and caps at pre_max_per_file per file,
    # producing a diverse candidate set of pre_diverse_n for the reranker.
    tests_pool = greedy_diversify(
        recall["tests"],   top_n=pre_diverse_n, max_per_file=pre_max_per_file)
    sources_pool = greedy_diversify(
        recall["sources"], top_n=pre_diverse_n, max_per_file=pre_max_per_file)

    # Stage 2 — FlashRank reranks the diverse pool (no post-rerank diversify needed)
    tests_all, sources_all = await asyncio.gather(
        rerank_candidates(query, tests_pool,   top_n=len(tests_pool)),
        rerank_candidates(query, sources_pool, top_n=len(sources_pool)),
    )

    effective_test_final = resolve_top_k_final(tests_all, eff_final)
    effective_source_final = resolve_top_k_final(sources_all, eff_final)

    # Return top-N, with a small recall safeguard for strong Stage 1 test hits.
    tests, _ = apply_test_safeguard(
        recall["tests"],
        tests_all,
        top_n=effective_test_final,
    )
    sources = sources_all[:effective_source_final]

    return {
        "query":            query,
        "requirement_type": req_type,
        "tests":            tests,
        "sources":          sources,
    }


async def generate_trace_report() -> dict:
    """
    Generate a full traceability report for every requirement chunk.

    Uses one fixed retrieval configuration plus greedy diversification per chunk.
    Matches the background report job pipeline.

    Returns a structured dict ready for JSON serialisation.
    """
    from datetime import datetime, timezone
    import os

    store = get_store()
    req_chunks = store.get_chunks_by_category("requirement")

    traceability: list[dict] = []

    for idx, (text, meta) in enumerate(req_chunks):
        req_type = classify_requirement(text)
        eff_recall = RETRIEVAL_PARAMS["top_k_recall"]
        pre_diverse_n = RETRIEVAL_PARAMS["pre_diverse_n"]
        pre_max_per_file = RETRIEVAL_PARAMS["pre_max_per_file"]
        eff_final = RETRIEVAL_PARAMS["top_k_final"]

        # Stage 1 — dense over-fetch
        recall = await recall_for_requirement(text, top_k=eff_recall)

        # Stage 1.5 — pre-diversify before reranking
        tests_pool = greedy_diversify(
            recall["tests"],   top_n=pre_diverse_n, max_per_file=pre_max_per_file)
        sources_pool = greedy_diversify(
            recall["sources"], top_n=pre_diverse_n, max_per_file=pre_max_per_file)

        # Stage 2 — rerank the diverse pool
        tests_all, sources_all = await asyncio.gather(
            rerank_candidates(text, tests_pool,   top_n=len(tests_pool)),
            rerank_candidates(text, sources_pool, top_n=len(sources_pool)),
        )

        effective_test_final = resolve_top_k_final(tests_all, eff_final)
        effective_source_final = resolve_top_k_final(sources_all, eff_final)
        tests_reranked, promoted_tests = apply_test_safeguard(
            recall["tests"],
            tests_all,
            top_n=effective_test_final,
        )
        sources_reranked = sources_all[:effective_source_final]

        def _ranked(items: list[dict]) -> list[dict]:
            return [{**item, "rank": i + 1} for i, item in enumerate(items)]

        traceability.append({
            "requirement": {
                "file":             meta.get("file_name", ""),
                "chunk_index":      meta.get("chunk_index", 0),
                "text":             text,
                "requirement_type": req_type,
            },
            "candidate_pool": {
                "stage":  1,
                "method": "dense recall (cosine similarity vector search)",
                "top_k":  eff_recall,
                "tests":  _ranked(recall["tests"]),
                "sources": _ranked(recall["sources"]),
            },
            "final_candidates": {
                "stage":        2,
                "method":       f"FlashRank ({RERANK_MODEL}) + greedy diversify",
                "top_n":        eff_final,
                "effective_test_top_n": effective_test_final,
                "effective_source_top_n": effective_source_final,
                "pre_max_per_file": pre_max_per_file,
                "tests":        _ranked(tests_reranked),
                "sources":      _ranked(sources_reranked),
            },
            "stage2_debug": {
                "dynamic_top_k_final_enabled": dynamic_top_k_final_enabled(),
                "base_final_count": eff_final,
                "effective_test_top_n": effective_test_final,
                "effective_source_top_n": effective_source_final,
                "rerank_input_tests": len(tests_pool),
                "reranked_tests": len(tests_all),
                "safeguard_promoted_tests": [
                    {
                        "test_id": f"{item.get('file_name', '')}::chunk{item.get('chunk_index', '')}",
                        "stage1_rank": item.get("stage1_rank", ""),
                        "score": item.get("score", ""),
                        "rerank_score": item.get("rerank_score", ""),
                        "safeguard_reason": item.get("safeguard_reason", ""),
                    }
                    for item in promoted_tests
                ],
                "final_test_count": len(tests_reranked),
            },
        })

    traceability.sort(
        key=lambda r: (r["requirement"]["file"],
                       r["requirement"]["chunk_index"])
    )

    return {
        "meta": {
            "generated_at":       datetime.now(timezone.utc).isoformat(),
            "model_embedding":    os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            "model_reranker":     RERANK_MODEL,
            "retrieval_params":   RETRIEVAL_PARAMS,
            "total_requirements": len(traceability),
        },
        "traceability": traceability,
    }


async def retrieve_all_requirements() -> list[dict]:
    """
    Run the full pipeline (fixed retrieval params + greedy diversify) for every
    requirement chunk in the store.

    One OpenAI embedding call per requirement chunk (no batching).
    Returns records sorted by (req_file, chunk_index).
    """
    store = get_store()
    req_chunks = store.get_chunks_by_category("requirement")

    if not req_chunks:
        return []

    results: list[dict] = []
    for text, meta in req_chunks:
        record = await retrieve_for_requirement(text)
        record["req_file"] = meta.get("file_name", "")
        record["chunk_index"] = meta.get("chunk_index", 0)
        results.append(record)

    return sorted(
        results,
        key=lambda r: (r.get("req_file", ""), r.get("chunk_index", 0)),
    )
