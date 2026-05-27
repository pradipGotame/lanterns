"""
services/vector_store.py
========================
Dense vector store backed by persistent Chroma storage.

Uses a persistent ChromaDB collection configured for cosine distance.

Storage layout  (backend/vector_store/):
  chroma/       — Chroma persistence directory
  raw_data.pkl  — list of (text, vector, metadata) triples for Chroma hydration,
                  stats, and category iteration

Design:
  - add()          writes pre-computed embeddings directly to Chroma via collection.add().
                   The same entries are mirrored into _raw_data for local persistence.
  - delete_file()  deletes from Chroma by metadata filter, then persists _raw_data.
  - delete_project() same as delete_file() but filters by project_id metadata field.
  - reset()        recreates the Chroma collection and clears in-memory state.
  - Thread safety via a single threading.Lock.
"""

from __future__ import annotations

import threading
from typing import Any, Optional
import pickle

import chromadb

from config import BACKEND_ROOT

# ── Paths ─────────────────────────────────────────────────────────────────────

VS_DIR        = BACKEND_ROOT / "vector_store"
CHROMA_DIR    = VS_DIR / "chroma"
RAW_DATA_PATH = VS_DIR / "raw_data.pkl"
COLLECTION_NAME = "lanterns_vectors"
LEGACY_INDEX_FILES = (VS_DIR / "index.faiss", VS_DIR / "index.pkl")
VS_DIR.mkdir(parents=True, exist_ok=True)


def _chunk_id(meta: dict) -> str:
    """Stable Chroma ID for a chunk."""
    project_prefix = f"{meta.get('project_id')}:" if meta.get("project_id") else ""
    return f"{project_prefix}{meta.get('file_id', '')}:{meta.get('chunk_index', 0)}"


# ── VectorStore ───────────────────────────────────────────────────────────────

class VectorStore:
    """
    Singleton Chroma-backed store. Obtain via get_store().
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._client: Optional[Any] = None
        self._collection: Optional[Any] = None
        # Raw (text, vector, metadata) triples provide a local persistence layer
        # for Chroma hydration and support local stats/category iteration.
        self._raw_data: list[tuple[str, list[float], dict]] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _init_collection(self) -> None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _recreate_collection(self) -> None:
        if self._client is None:
            self._init_collection()
            return

        try:
            self._client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _clear_legacy_files(self) -> None:
        for path in LEGACY_INDEX_FILES:
            path.unlink(missing_ok=True)

    def _collection_count(self) -> int:
        return self._collection.count() if self._collection is not None else 0

    def _collection_payload(self) -> tuple[list[str], list[list[float]], list[dict], list[str]]:
        documents = [text for text, _, _ in self._raw_data]
        embeddings = [list(map(float, vec)) for _, vec, _ in self._raw_data]
        metadatas = [dict(meta) for _, _, meta in self._raw_data]
        ids = [_chunk_id(meta) for meta in metadatas]
        return documents, embeddings, metadatas, ids

    def _hydrate_collection_from_raw(self) -> None:
        self._recreate_collection()
        if not self._raw_data or self._collection is None:
            return

        documents, embeddings, metadatas, ids = self._collection_payload()
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def _hydrate_raw_from_collection(self) -> list[tuple[str, list[float], dict]]:
        if self._collection is None or self._collection_count() == 0:
            return []

        payload = self._collection.get(include=["documents", "embeddings", "metadatas"])
        documents = payload.get("documents") or []
        embeddings = payload.get("embeddings") or []
        metadatas = payload.get("metadatas") or []

        return [
            (str(doc or ""), list(map(float, emb or [])), dict(meta or {}))
            for doc, emb, meta in zip(documents, embeddings, metadatas)
        ]

    def _load(self) -> None:
        self._init_collection()

        if RAW_DATA_PATH.exists():
            try:
                with open(RAW_DATA_PATH, "rb") as fh:
                    self._raw_data = pickle.load(fh)
            except Exception as exc:
                print(f"[vector_store] raw_data load failed: {exc}")
                self._raw_data = []

        collection_count = self._collection_count()
        if self._raw_data and collection_count == 0:
            self._hydrate_collection_from_raw()
            collection_count = self._collection_count()
            print(f"[vector_store] Migrated raw_data → Chroma ({collection_count} vectors)")
        elif not self._raw_data and collection_count > 0:
            self._raw_data = self._hydrate_raw_from_collection()
            self._save()
            print(f"[vector_store] Hydrated raw_data from Chroma ({len(self._raw_data)} vectors)")
        elif self._raw_data and collection_count != len(self._raw_data):
            print(
                "[vector_store] Chroma/raw_data mismatch detected; "
                "rebuilding Chroma from raw_data"
            )
            self._hydrate_collection_from_raw()
            collection_count = self._collection_count()
        else:
            print(f"[vector_store] Loaded — {collection_count} vectors")

        self._clear_legacy_files()

    def _save(self) -> None:
        VS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = RAW_DATA_PATH.with_suffix(".tmp")
        with open(tmp, "wb") as fh:
            pickle.dump(self._raw_data, fh)
        tmp.replace(RAW_DATA_PATH)

    # ── Write ──────────────────────────────────────────────────────────────────

    def add(
        self,
        embeddings:   list[list[float]],
        meta_entries: list[dict],
    ) -> int:
        """
        Add pre-computed embedding vectors to the store.

        Args:
            embeddings:   Raw float vectors from embedder.py (not yet normalised).
            meta_entries: Metadata dicts — must contain at least: file_id, category,
                          chunk_index, text.
        Returns:
            Number of vectors added.
        """
        if not embeddings:
            return 0
        if len(embeddings) != len(meta_entries):
            raise ValueError("embeddings and meta_entries must be the same length")

        with self._lock:
            metas = list(meta_entries)
            documents = [meta["text"] for meta in metas]
            ids = [_chunk_id(meta) for meta in metas]
            dense_vectors = [list(map(float, vec)) for vec in embeddings]

            if self._collection is None:
                self._init_collection()

            self._collection.add(
                ids=ids,
                embeddings=dense_vectors,
                documents=documents,
                metadatas=metas,
            )

            for text, vec, meta in zip(documents, dense_vectors, metas):
                self._raw_data.append((text, vec, meta))

            self._save()
            self._clear_legacy_files()
            return len(embeddings)

    def delete_file(self, file_id: str) -> int:
        """
        Remove all vectors for *file_id* and refresh derived state.
        Returns the number of vectors removed.
        """
        with self._lock:
            before = sum(1 for _, _, m in self._raw_data if m.get("file_id") == file_id)
            if before == 0:
                return 0

            if self._collection is not None:
                self._collection.delete(where={"file_id": file_id})
            self._raw_data = [
                (t, v, m) for t, v, m in self._raw_data
                if m.get("file_id") != file_id
            ]
            self._save()
            print(f"[vector_store] Deleted {before} vectors for {file_id}")
            return before

    def delete_project(self, project_id: str) -> int:
        """
        Remove all vectors for *project_id* and refresh derived state.
        Used by Phase 2 to avoid duplicate ATUs on re-run.
        Returns the number of vectors removed.
        """
        with self._lock:
            before = sum(1 for _, _, m in self._raw_data if m.get("project_id") == project_id)
            if before == 0:
                return 0
            if self._collection is not None:
                self._collection.delete(where={"project_id": project_id})
            self._raw_data = [
                (t, v, m) for t, v, m in self._raw_data
                if m.get("project_id") != project_id
            ]
            self._save()
            print(f"[vector_store] Deleted {before} vectors for project {project_id}")
            return before

    def reset(self) -> int:
        """Wipe the entire index.  Returns the number of vectors removed."""
        with self._lock:
            count = len(self._raw_data)
            self._recreate_collection()
            self._raw_data = []
            RAW_DATA_PATH.unlink(missing_ok=True)
            self._clear_legacy_files()
            print(f"[vector_store] Reset — removed {count} vectors")
            return count

    # ── Read ───────────────────────────────────────────────────────────────────

    def search(
        self,
        query_embedding: list[float],
        *,
        top_k:    int = 10,
        category: Optional[str] = None,
    ) -> list[dict]:
        """
        Semantic nearest-neighbour search (used by /api/embed/search).
        """
        with self._lock:
            if self._collection is None or not self._raw_data:
                return []

            filter_dict = {"category": category} if category else None
            query_kwargs: dict[str, Any] = {
                "query_embeddings": [list(map(float, query_embedding))],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if filter_dict is not None:
                query_kwargs["where"] = filter_dict

            results = self._collection.query(**query_kwargs)
            documents = (results.get("documents") or [[]])[0]
            metadatas = (results.get("metadatas") or [[]])[0]
            distances = (results.get("distances") or [[]])[0]

            hits: list[dict] = []
            for doc, meta, distance in zip(documents, metadatas, distances):
                score = 1.0 - float(distance)
                hits.append({
                    **dict(meta or {}),
                    "text": str(doc or ""),
                    "score": round(score, 4),
                })
            return hits

    def get_stats(self) -> dict:
        """Return summary statistics about the current index."""
        with self._lock:
            by_cat: dict = {}
            for _, _, m in self._raw_data:
                cat   = m.get("category", "unknown")
                entry = by_cat.setdefault(cat, {"vectors": 0, "files": set()})
                entry["vectors"] += 1
                entry["files"].add(m.get("file_id", ""))

            dim = len(self._raw_data[0][1]) if self._raw_data else None
            return {
                "total_vectors": len(self._raw_data),
                "dimension":     dim,
                "by_category": {
                    cat: {"vectors": d["vectors"], "unique_files": len(d["files"])}
                    for cat, d in by_cat.items()
                },
            }

    def is_file_indexed(self, file_id: str) -> bool:
        """Return True if at least one vector exists for *file_id*."""
        return any(m.get("file_id") == file_id for _, _, m in self._raw_data)

    def get_chunks_by_category(self, category: str) -> list[tuple[str, dict]]:
        """Return (text, metadata) pairs for every chunk of a given category."""
        return [
            (text, meta)
            for text, _, meta in self._raw_data
            if meta.get("category") == category
        ]

    # ── LangChain retriever ────────────────────────────────────────────────────

    def as_langchain_retriever(
        self,
        category:     str,
        top_k_recall: int = 20,
    ):
        """
        Return a small retriever adapter filtered to *category*.
        """
        if self._collection is None:
            raise ValueError("Vector store is empty — run /api/embed first.")

        store = self

        class _Retriever:
            def invoke(self, query: str):
                from langchain_core.documents import Document

                from services.embedder import embed_single

                hits = store.search(
                    embed_single(query),
                    top_k=top_k_recall,
                    category=category,
                )
                return [
                    Document(
                        page_content=hit["text"],
                        metadata={k: v for k, v in hit.items() if k not in {"text", "score"}},
                    )
                    for hit in hits
                ]

            def get_relevant_documents(self, query: str):
                return self.invoke(query)

        return _Retriever()


# ── Singleton ─────────────────────────────────────────────────────────────────

_store: Optional[VectorStore] = None


def get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
