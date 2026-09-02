"""
Embedding Generation Script — APS-04
Generates multilingual sentence embeddings for all active hotels, POIs, and packages.
Stores them in a FAISS flat-IP index (cosine similarity via normalized vectors).
Only needs to be run once (or after dataset changes).
"""
import os
import sys
import pickle
import logging
import time
from pathlib import Path

import numpy as np

# Fix Windows file-lock issue with HuggingFace cache
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.database.connection import get_source_db
from app.embeddings.engine import get_index_path, save_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def load_model():
    """Load the sentence transformer model with Windows-safe settings."""
    from sentence_transformers import SentenceTransformer
    import huggingface_hub
    # Disable symlinks globally on Windows
    try:
        import huggingface_hub.constants as hf_const
        hf_const.HF_HUB_DISABLE_SYMLINKS_WARNING = True
    except Exception:
        pass
    logger.info(f"Loading model: {settings.EMBEDDING_MODEL}")
    model = SentenceTransformer(settings.EMBEDDING_MODEL, local_files_only=False)
    logger.info("Model loaded.")
    return model


def build_hotel_text(row: dict) -> str:
    parts = [
        row.get("name", ""),
        row.get("property_type", ""),
        f"{'*' * int(row.get('star_rating', 3) or 3)} star",
        row.get("description", "")[:300] if row.get("description") else "",
        f"in {row.get('city_name', '')}",
        row.get("country_name", ""),
    ]
    return " ".join(p for p in parts if p).strip()


def build_poi_text(row: dict) -> str:
    tags = row.get("tags", "")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    parts = [
        row.get("name", ""),
        row.get("poi_category", ""),
        row.get("description", "")[:300] if row.get("description") else "",
        f"in {row.get('city_name', '')}",
        row.get("country_name", ""),
        " ".join(tag_list[:6]),
    ]
    return " ".join(p for p in parts if p).strip()


def build_package_text(row: dict) -> str:
    parts = [
        row.get("name", ""),
        row.get("theme", ""),
        row.get("tier", ""),
        row.get("difficulty", ""),
        f"{row.get('duration_days', '')} days",
        row.get("description", "")[:300] if row.get("description") else "",
        f"in {row.get('city_name', '')}",
        row.get("country_name", ""),
        row.get("inclusions", "")[:150] if row.get("inclusions") else "",
    ]
    return " ".join(p for p in parts if p).strip()


def load_all_items() -> tuple[list[dict], list[str]]:
    metadata = []
    texts = []

    with get_source_db() as conn:
        cur = conn.cursor()

        logger.info("Loading hotels...")
        cur.execute("""
            SELECT h.hotel_id, h.name, h.property_type, h.star_rating,
                   h.description, h.status,
                   c.name AS city_name, cy.name AS country_name
            FROM hotels h
            JOIN cities c ON h.city_id = c.city_id
            JOIN countries cy ON c.country_id = cy.country_id
            WHERE h.status = 'active'
        """)
        for row in cur.fetchall():
            r = dict(row)
            text = build_hotel_text(r)
            metadata.append({"entity_type": "hotel", "entity_id": r["hotel_id"], "text": text})
            texts.append(text)
        logger.info(f"  {sum(1 for m in metadata if m['entity_type']=='hotel')} hotels loaded")

        logger.info("Loading activities/POIs...")
        cur.execute("""
            SELECT p.poi_id, p.name, p.poi_category, p.tags, p.description, p.status,
                   c.name AS city_name, cy.name AS country_name
            FROM activities_poi p
            JOIN cities c ON p.city_id = c.city_id
            JOIN countries cy ON c.country_id = cy.country_id
            WHERE p.status = 'active'
        """)
        poi_start = len(metadata)
        for row in cur.fetchall():
            r = dict(row)
            text = build_poi_text(r)
            metadata.append({"entity_type": "poi", "entity_id": r["poi_id"], "text": text})
            texts.append(text)
        logger.info(f"  {len(metadata)-poi_start} POIs loaded")

        logger.info("Loading tour packages...")
        cur.execute("""
            SELECT tp.package_id, tp.name, tp.theme, tp.tier, tp.difficulty,
                   tp.duration_days, tp.description, tp.inclusions, tp.status,
                   c.name AS city_name, cy.name AS country_name
            FROM tour_packages tp
            JOIN cities c ON tp.city_id = c.city_id
            JOIN countries cy ON c.country_id = cy.country_id
            WHERE tp.status = 'active'
        """)
        pkg_start = len(metadata)
        for row in cur.fetchall():
            r = dict(row)
            text = build_package_text(r)
            metadata.append({"entity_type": "package", "entity_id": r["package_id"], "text": text})
            texts.append(text)
        logger.info(f"  {len(metadata)-pkg_start} packages loaded")

    logger.info(f"Total items: {len(texts)}")
    return metadata, texts


def generate_embeddings():
    logger.info("=" * 60)
    logger.info("NEXORA Embedding Generation")
    logger.info(f"Model: {settings.EMBEDDING_MODEL}")
    logger.info("=" * 60)

    model = load_model()
    metadata, texts = load_all_items()

    if not texts:
        logger.error("No items found.")
        sys.exit(1)

    logger.info(f"Embedding {len(texts)} items (batch_size={settings.EMBEDDING_BATCH_SIZE})...")
    t_start = time.perf_counter()

    embeddings = model.encode(
        texts,
        batch_size=settings.EMBEDDING_BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    embeddings = embeddings.astype(np.float32)
    t_embed = time.perf_counter() - t_start
    logger.info(f"Done in {t_embed:.1f}s. Shape: {embeddings.shape}")

    logger.info("Building FAISS index...")
    import faiss
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    logger.info(f"Index: {index.ntotal} vectors, dim={dim}")

    save_index(index, metadata)

    # Verify
    test_query = model.encode(["beach adventure activities"], normalize_embeddings=True).astype(np.float32)
    distances, indices = index.search(test_query, 5)
    logger.info("\n--- Verification: 'beach adventure activities' top 5 ---")
    for d, i in zip(distances[0], indices[0]):
        m = metadata[i]
        logger.info(f"  [{m['entity_type']}] {m['entity_id']} sim={d:.4f} | {m['text'][:70]}")

    logger.info("\n" + "=" * 60)
    logger.info(f"SUCCESS — {index.ntotal} vectors saved to {get_index_path()}")
    logger.info("Next step: start the backend with: uvicorn app.main:app --reload")
    logger.info("=" * 60)


if __name__ == "__main__":
    generate_embeddings()
