"""
Vector store for memory retrieval (RAG).

Embeddings: sentence-transformers (all-MiniLM-L6-v2 - small, fast, good
enough for short memory snippets; upgrade later if retrieval quality
is the bottleneck, not before).

Index: FAISS, flat L2 index. Flat is O(n) per search but exact and
trivial to reason about -- fine until the memory count gets into the
tens of thousands, which an individual user's assistant is unlikely to
hit. Don't reach for IVF/HNSW indexes prematurely.

This module is intentionally storage-agnostic about *what* gets
embedded -- Stage 3 (memory extraction) decides what text goes in.
This file only knows how to embed, add, search, and remove vectors.

IMPORTANT: this in-memory index is NOT persisted across process
restarts yet. That's fine for Day 1-2 development; wire it to disk
(faiss index file, or move the whole thing into pgvector per the
original plan) before this needs to survive a restart with real data.
"""
import logging
import threading
from functools import lru_cache

import numpy as np

logger = logging.getLogger("memora.vectorstore")

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  # matches all-MiniLM-L6-v2's output size


class VectorStoreError(RuntimeError):
    """Raised when embedding or index operations fail."""


@lru_cache(maxsize=1)
def _get_embedder():
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model (%s) - first call only", EMBEDDING_MODEL_NAME)
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_text(text: str) -> np.ndarray:
    try:
        embedder = _get_embedder()
        vec = embedder.encode([text], normalize_embeddings=True)[0]
    except Exception as exc:
        logger.exception("Embedding failed")
        raise VectorStoreError(str(exc)) from exc
    return vec.astype("float32")


class MemoryVectorStore:
    """
    Per-process FAISS index mapping memory_id -> embedding, with a
    parallel id list for lookup. Not thread-safe by default in FAISS,
    so writes/reads are serialized with a lock.
    """

    def __init__(self, dim: int = EMBEDDING_DIM):
        import faiss

        self._dim = dim
        self._index = faiss.IndexFlatIP(dim)  # inner product == cosine, since vectors are normalized
        self._ids: list[str] = []  # positional index -> memory_id
        self._lock = threading.Lock()

    def add(self, memory_id: str, text: str) -> None:
        vec = embed_text(text).reshape(1, -1)
        with self._lock:
            self._index.add(vec)
            self._ids.append(memory_id)

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Returns [(memory_id, similarity_score), ...] sorted by relevance."""
        if not self._ids:
            return []
        vec = embed_text(query).reshape(1, -1)
        with self._lock:
            scores, indices = self._index.search(vec, min(top_k, len(self._ids)))
            results = [
                (self._ids[idx], float(score))
                for score, idx in zip(scores[0], indices[0])
                if idx != -1
            ]
        return results

    def remove(self, memory_id: str) -> None:
        """
        FAISS flat indexes don't support in-place deletion cheaply.
        Rebuild the index without the removed id -- fine at MVP scale,
        revisit (e.g. IndexIDMap + remove_ids) if deletes get frequent.
        """
        with self._lock:
            if memory_id not in self._ids:
                return
            keep = [(mid) for mid in self._ids if mid != memory_id]
            # Rebuilding requires re-embedding is NOT needed here since
            # callers that need true removal should keep a text cache;
            # for Day 1-3 scope, prefer marking memories inactive at the
            # DB layer over physically removing from the index.
            raise NotImplementedError(
                "Vector removal by id requires a text cache to rebuild from. "
                "Prefer soft-delete at the DB layer (status=inactive) and "
                "filter results after search, per the temporal-memory plan."
            )

    def size(self) -> int:
        return len(self._ids)


# Single process-wide store instance. Swap for a persisted / DB-backed
# store before this needs to survive restarts with real user data.
memory_store = MemoryVectorStore()
