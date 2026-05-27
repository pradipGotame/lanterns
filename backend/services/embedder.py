"""
services/embedder.py
====================
Text embedding via langchain-openai's OpenAIEmbeddings.

- Uses OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_EMBEDDING_MODEL from env.
- Supports a custom openai_api_base (e.g. the Chalmers proxy).
- OpenAIEmbeddings handles batching internally; embed_texts() is a thin wrapper
  that keeps the rest of the codebase decoupled from LangChain internals.
"""

from __future__ import annotations

import os
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

DEFAULT_MODEL = "text-embedding-3-small"


# ── Client factory (cached — one instance per process) ────────────────────────

@lru_cache(maxsize=1)
def _embeddings() -> OpenAIEmbeddings:
    """
    Build and cache an OpenAIEmbeddings instance.

    langchain-openai reads OPENAI_API_KEY automatically; we pass
    openai_api_base only when OPENAI_BASE_URL is set (custom proxy).
    """
    model    = os.environ.get("OPENAI_EMBEDDING_MODEL", DEFAULT_MODEL)
    base_url = os.environ.get("OPENAI_BASE_URL") or None

    kwargs: dict = dict(model=model)
    if base_url:
        kwargs["openai_api_base"] = base_url

    return OpenAIEmbeddings(**kwargs)


# ── Public API ────────────────────────────────────────────────────────────────

def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of strings using langchain-openai's OpenAIEmbeddings.

    OpenAIEmbeddings handles batching and retries internally.
    Empty strings are replaced with a single space (the API rejects them).

    Args:
        texts: Strings to embed.

    Returns:
        List of float vectors in the same order as *texts*.
    """
    if not texts:
        return []

    safe = [t if t.strip() else " " for t in texts]
    return _embeddings().embed_documents(safe)


def embed_single(text: str) -> list[float]:
    """Embed a single query string (uses embed_query for query-optimised models)."""
    safe = text if text.strip() else " "
    return _embeddings().embed_query(safe)
