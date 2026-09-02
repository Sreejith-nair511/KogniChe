"""
Evaluation metrics for offline evaluation.
Uses actual APS-04 eval_queries and eval_relevance_labels.
Implements: Precision@K, NDCG@K, Recall@K, MRR.
"""
import math
import logging
from typing import Optional
from app.database.connection import get_source_db

logger = logging.getLogger(__name__)


def dcg_at_k(relevances: list[int], k: int) -> float:
    """Compute DCG@K."""
    total = 0.0
    for i, rel in enumerate(relevances[:k]):
        total += (2 ** rel - 1) / math.log2(i + 2)
    return total


def ideal_dcg_at_k(relevances: list[int], k: int) -> float:
    """Compute ideal DCG@K (IDCG@K) from sorted descending relevances."""
    sorted_rels = sorted(relevances, reverse=True)
    return dcg_at_k(sorted_rels, k)


def ndcg_at_k(retrieved_ids: list[str], labels: dict[str, int], k: int) -> float:
    """
    Compute NDCG@K.
    retrieved_ids: ordered list of entity IDs returned by system
    labels: dict of entity_id → grade (0-3)
    """
    if not retrieved_ids:
        return 0.0
    all_rels = list(labels.values())
    idcg = ideal_dcg_at_k(all_rels, k)
    if idcg == 0:
        return 0.0
    actual_rels = [labels.get(eid, 0) for eid in retrieved_ids]
    dcg = dcg_at_k(actual_rels, k)
    return dcg / idcg


def precision_at_k(retrieved_ids: list[str], labels: dict[str, int], k: int, threshold: int = 2) -> float:
    """
    Compute Precision@K.
    threshold: minimum grade to be considered relevant (default 2 = relevant or ideal).
    """
    if not retrieved_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    relevant = sum(1 for eid in top_k if labels.get(eid, 0) >= threshold)
    return relevant / k


def recall_at_k(retrieved_ids: list[str], labels: dict[str, int], k: int, threshold: int = 2) -> float:
    """Compute Recall@K."""
    if not retrieved_ids:
        return 0.0
    total_relevant = sum(1 for grade in labels.values() if grade >= threshold)
    if total_relevant == 0:
        return 0.0
    top_k = retrieved_ids[:k]
    retrieved_relevant = sum(1 for eid in top_k if labels.get(eid, 0) >= threshold)
    return retrieved_relevant / total_relevant


def mrr(retrieved_ids: list[str], labels: dict[str, int], threshold: int = 2) -> float:
    """Compute MRR (Mean Reciprocal Rank)."""
    for i, eid in enumerate(retrieved_ids):
        if labels.get(eid, 0) >= threshold:
            return 1.0 / (i + 1)
    return 0.0


def compute_query_metrics(
    retrieved_ids: list[str],
    labels: dict[str, int],
    k_values: list[int] = [5, 10],
) -> dict[str, float]:
    """Compute all metrics for a single query."""
    result = {}
    for k in k_values:
        result[f"precision_at_{k}"] = precision_at_k(retrieved_ids, labels, k)
        result[f"ndcg_at_{k}"] = ndcg_at_k(retrieved_ids, labels, k)
    result[f"recall_at_{max(k_values)}"] = recall_at_k(retrieved_ids, labels, max(k_values))
    result["mrr"] = mrr(retrieved_ids, labels)
    return result


def load_eval_data() -> list[dict]:
    """Load all evaluation queries with their relevance labels from source DB."""
    queries = []
    with get_source_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT q.query_id, q.query_text, q.language, q.intent,
                   q.target_entity_type, q.city_id, q.persona_user_id,
                   q.filters_json, q.k, q.notes
            FROM eval_queries q
            ORDER BY q.query_id
        """)
        raw_queries = cur.fetchall()

        for q in raw_queries:
            cur.execute("""
                SELECT entity_type, entity_id, grade
                FROM eval_relevance_labels
                WHERE query_id = ?
            """, (q["query_id"],))
            labels_raw = cur.fetchall()
            labels = {r["entity_id"]: r["grade"] for r in labels_raw}
            queries.append({
                "query_id": q["query_id"],
                "query_text": q["query_text"],
                "language": q["language"],
                "intent": q["intent"],
                "target_entity_type": q["target_entity_type"],
                "city_id": q["city_id"],
                "persona_user_id": q["persona_user_id"],
                "filters_json": q["filters_json"],
                "k": q["k"],
                "notes": q["notes"],
                "labels": labels,
            })

    logger.info(f"Loaded {len(queries)} evaluation queries")
    return queries
