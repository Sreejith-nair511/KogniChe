"""
Hybrid Retrieval Pipeline:
1. Structured eligibility (hard filters)
2. Semantic vector search
3. Candidate intersection / union
4. Returns merged candidate pool with scores
"""
import logging
import time
from typing import Optional
import numpy as np

from app.schemas.recommendation import QueryConstraints, RetrievalTelemetry
from app.retrieval.structured_filter import get_all_eligible
from app.embeddings.engine import search_index, embed_query, is_index_loaded, load_index

logger = logging.getLogger(__name__)


def build_candidate_pool(
    query: str,
    constraints: QueryConstraints,
    semantic_text: str,
    entity_types: Optional[list[str]] = None,
    top_k: int = 50,
) -> tuple[list[dict], RetrievalTelemetry]:
    """
    Build the personalization candidate pool using hybrid retrieval.

    Returns:
        candidates: list of dicts with entity_type, entity_id, semantic_score, item_data
        telemetry: RetrievalTelemetry with counts and timing
    """
    t_start = time.perf_counter()

    # Step 1: structured eligibility
    t_filter_start = time.perf_counter()
    eligible_map = get_all_eligible(constraints, entity_types)
    catalogue_count = sum(len(v) for v in eligible_map.values())

    # Build lookup from (entity_type, entity_id) → item_data
    eligible_lookup: dict[tuple[str, str], dict] = {}
    for etype, items in eligible_map.items():
        for item in items:
            eid = item.get(f"{_entity_id_field(etype)}")
            if eid:
                eligible_lookup[(etype, eid)] = item
    eligible_count = len(eligible_lookup)
    t_filter_end = time.perf_counter()

    # Step 2: semantic search
    t_embed_start = time.perf_counter()
    query_emb = embed_query(semantic_text)
    t_embed_end = time.perf_counter()

    t_retrieval_start = time.perf_counter()
    if not is_index_loaded():
        load_index()
    semantic_hits = search_index(query_emb, top_k=top_k * 3)  # over-retrieve then filter
    t_retrieval_end = time.perf_counter()

    # Step 3: filter semantic hits to only eligible items
    candidates: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for hit in semantic_hits:
        etype = hit["entity_type"]
        eid = hit["entity_id"]
        key = (etype, eid)
        if key in eligible_lookup and key not in seen:
            seen.add(key)
            candidates.append({
                "entity_type": etype,
                "entity_id": eid,
                "semantic_score": hit["similarity"],
                "item_data": eligible_lookup[key],
                "embedding_text": hit.get("text", ""),
            })
            if len(candidates) >= top_k:
                break

    semantic_candidate_count = len(candidates)

    # If semantic retrieval yields too few candidates (index empty or cold), fall back to popularity
    if semantic_candidate_count < 5:
        logger.info("Semantic results sparse — augmenting with popularity-ranked eligible items")
        added = 0
        # Sort eligible by popularity (POIs have popularity_score, hotels by guest_score, packages by duration)
        all_eligible = [
            (etype, eid, item) for (etype, eid), item in eligible_lookup.items()
        ]
        # Sort by a fallback score
        def fallback_score(row):
            _, _, item = row
            if "popularity_score" in item and item["popularity_score"]:
                return float(item["popularity_score"]) / 100.0
            if "guest_score" in item and item["guest_score"]:
                return float(item["guest_score"]) / 10.0
            return 0.5

        all_eligible.sort(key=fallback_score, reverse=True)
        for etype, eid, item in all_eligible:
            key = (etype, eid)
            if key not in seen:
                seen.add(key)
                candidates.append({
                    "entity_type": etype,
                    "entity_id": eid,
                    "semantic_score": 0.3,  # baseline for popularity fallback
                    "item_data": item,
                    "embedding_text": "",
                })
                added += 1
                if len(candidates) >= top_k:
                    break
        logger.info(f"Added {added} popularity-fallback candidates")

    t_end = time.perf_counter()

    telemetry = RetrievalTelemetry(
        catalogue_count=catalogue_count,
        eligible_count=eligible_count,
        filtered_count=eligible_count,
        semantic_candidate_count=semantic_candidate_count,
        personalized_candidate_count=len(candidates),
        final_count=len(candidates),
        query_parse_ms=0.0,
        embedding_ms=(t_embed_end - t_embed_start) * 1000,
        retrieval_ms=(t_retrieval_end - t_retrieval_start) * 1000,
        reranking_ms=0.0,
        total_ms=(t_end - t_start) * 1000,
    )

    return candidates, telemetry


def _entity_id_field(entity_type: str) -> str:
    """Return the primary key field name for an entity type."""
    mapping = {
        "hotel": "hotel_id",
        "poi": "poi_id",
        "package": "package_id",
    }
    return mapping.get(entity_type, f"{entity_type}_id")
