"""
Embedding engine using a multilingual sentence transformer.
Supports English, Hindi (hi), Tamil (ta), Malayalam (ml), Bengali (bn), etc.
Embeddings are computed once and stored in a FAISS index.
"""
import os
import json
import logging
import pickle
import time
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_model = None
_index = None
_index_metadata: list[dict] = []  # [{entity_type, entity_id, text}, ...]
_index_path: Optional[Path] = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from app.core.config import settings
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded.")
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of texts. Returns float32 ndarray of shape (N, dim)."""
    model = _get_model()
    from app.core.config import settings
    embeddings = model.encode(
        texts,
        batch_size=settings.EMBEDDING_BATCH_SIZE,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.astype(np.float32)


def embed_query(text: str) -> np.ndarray:
    """Embed a single query. Returns float32 ndarray of shape (dim,)."""
    return embed_texts([text])[0]


def get_index_path() -> Path:
    from app.core.config import settings
    p = Path(settings.VECTOR_INDEX_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_index() -> bool:
    """Load FAISS index from disk. Returns True if successful."""
    global _index, _index_metadata
    import faiss
    idx_path = get_index_path() / "nexora.index"
    meta_path = get_index_path() / "nexora_meta.pkl"
    if not idx_path.exists() or not meta_path.exists():
        logger.warning("Vector index not found. Run scripts/generate_embeddings.py first.")
        return False
    _index = faiss.read_index(str(idx_path))
    with open(meta_path, "rb") as f:
        _index_metadata = pickle.load(f)
    logger.info(f"Loaded FAISS index: {_index.ntotal} vectors, {len(_index_metadata)} metadata entries.")
    return True


def save_index(index, metadata: list[dict]):
    """Save FAISS index and metadata to disk."""
    import faiss
    idx_path = get_index_path() / "nexora.index"
    meta_path = get_index_path() / "nexora_meta.pkl"
    faiss.write_index(index, str(idx_path))
    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)
    logger.info(f"Saved FAISS index with {index.ntotal} vectors.")


def search_index(query_embedding: np.ndarray, top_k: int = 50) -> list[dict]:
    """
    Search FAISS index for nearest neighbours.
    Returns list of {entity_type, entity_id, similarity, text} sorted by similarity desc.
    """
    global _index, _index_metadata
    if _index is None:
        if not load_index():
            return []

    q = query_embedding.reshape(1, -1).astype(np.float32)
    distances, indices = _index.search(q, min(top_k, _index.ntotal))

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(_index_metadata):
            continue
        meta = _index_metadata[idx]
        results.append({
            "entity_type": meta["entity_type"],
            "entity_id": meta["entity_id"],
            "similarity": float(dist),  # cosine similarity (normalized vectors)
            "text": meta.get("text", ""),
        })
    return results


def is_index_loaded() -> bool:
    return _index is not None


def index_status() -> dict:
    global _index, _index_metadata
    if _index is None:
        loaded = load_index()
        if not loaded:
            return {"status": "unavailable", "total_vectors": 0}
    return {
        "status": "ok",
        "total_vectors": _index.ntotal if _index else 0,
        "metadata_entries": len(_index_metadata),
    }
