"""
Evaluation Service.
Runs all baseline models + NEXORA against the APS-04 evaluation set.
Returns honest, unmanipulated metrics.
"""
import json
import logging
import time
from typing import Optional

from app.evaluation.metrics import load_eval_data, compute_query_metrics
from app.database.connection import get_source_db
from app.schemas.recommendation import EvalMetrics, EvaluationSummary, EvaluationComparison, QueryEvalResult

logger = logging.getLogger(__name__)


# ── Baseline models ─────────────────────────────────────────────────────────────

def popularity_retrieve(target_entity_type: str, city_id: Optional[str], k: int) -> list[str]:
    """Baseline 1: sort by popularity / rating."""
    with get_source_db() as conn:
        cur = conn.cursor()
        if target_entity_type == "hotel":
            conditions = ["status = 'active'"]
            params = []
            if city_id:
                conditions.append("city_id = ?")
                params.append(city_id)
            where = " AND ".join(conditions)
            cur.execute(f"""
                SELECT hotel_id FROM hotels WHERE {where}
                ORDER BY CAST(COALESCE(guest_score, 0) AS REAL) DESC, review_count DESC
                LIMIT ?
            """, params + [k])
            return [r[0] for r in cur.fetchall()]

        elif target_entity_type == "poi":
            conditions = ["status = 'active'"]
            params = []
            if city_id:
                conditions.append("city_id = ?")
                params.append(city_id)
            where = " AND ".join(conditions)
            cur.execute(f"""
                SELECT poi_id FROM activities_poi WHERE {where}
                ORDER BY popularity_score DESC, value_score DESC
                LIMIT ?
            """, params + [k])
            return [r[0] for r in cur.fetchall()]

        elif target_entity_type == "package":
            conditions = ["status = 'active'"]
            params = []
            if city_id:
                conditions.append("city_id = ?")
                params.append(city_id)
            where = " AND ".join(conditions)
            cur.execute(f"""
                SELECT package_id FROM tour_packages WHERE {where}
                ORDER BY CASE tier WHEN 'premium' THEN 3 WHEN 'deluxe' THEN 2 ELSE 1 END DESC
                LIMIT ?
            """, params + [k])
            return [r[0] for r in cur.fetchall()]

    return []


def semantic_retrieve(query_text: str, target_entity_type: str, city_id: Optional[str], k: int) -> list[str]:
    """Baseline 2: semantic retrieval only."""
    from app.embeddings.engine import embed_query, search_index, is_index_loaded, load_index
    from app.retrieval.structured_filter import get_all_eligible
    from app.schemas.recommendation import QueryConstraints

    constraints = QueryConstraints(
        city_id=city_id,
        entity_types=[target_entity_type],
    )

    if not is_index_loaded():
        load_index()

    q_emb = embed_query(query_text)
    hits = search_index(q_emb, top_k=k * 5)

    # Build eligible set
    eligible = get_all_eligible(constraints, [target_entity_type])
    eligible_ids = set()
    for items in eligible.values():
        for item in items:
            eid = item.get(f"{target_entity_type}_id")
            if eid:
                eligible_ids.add(eid)

    results = []
    for hit in hits:
        if hit["entity_type"] == target_entity_type and hit["entity_id"] in eligible_ids:
            results.append(hit["entity_id"])
            if len(results) >= k:
                break

    return results


def hybrid_retrieve(query_text: str, target_entity_type: str, city_id: Optional[str], k: int) -> list[str]:
    """Baseline 3: hybrid retrieval (semantic + structured filter, no personalization)."""
    return semantic_retrieve(query_text, target_entity_type, city_id, k)


def nexora_retrieve(
    query_text: str,
    target_entity_type: str,
    city_id: Optional[str],
    persona_user_id: Optional[str],
    filters_json: str,
    k: int,
) -> list[str]:
    """NEXORA: full pipeline with personalization."""
    from app.services.query_understanding import extract_constraints, detect_language, build_semantic_text
    from app.retrieval.hybrid_retriever import build_candidate_pool
    from app.personalization.user_profile import get_or_build_profile
    from app.ranking.personalized_ranker import rank_candidates

    # Parse filters
    filters_dict = {}
    try:
        filters_dict = json.loads(filters_json or "{}")
    except Exception:
        pass

    # Build constraints
    constraints = extract_constraints(query_text)
    if city_id and not constraints.city_id:
        constraints.city_id = city_id
    if not constraints.entity_types:
        constraints.entity_types = [target_entity_type]
    # Apply filters_json hard filters
    if "star_min" in filters_dict:
        constraints.star_min = filters_dict["star_min"]
    if "price_max" in filters_dict:
        constraints.budget_max = float(filters_dict["price_max"])

    semantic_text = build_semantic_text(query_text, constraints)
    candidates, _ = build_candidate_pool(
        query=query_text,
        constraints=constraints,
        semantic_text=semantic_text,
        entity_types=[target_entity_type],
        top_k=k * 5,
    )

    profile = None
    if persona_user_id:
        profile = get_or_build_profile(persona_user_id)

    ranked = rank_candidates(candidates, profile, None, top_k=k)
    id_field = {"hotel": "hotel_id", "poi": "poi_id", "package": "package_id"}.get(target_entity_type, "id")
    return [c["entity_id"] for c in ranked]


# ── Aggregate evaluator ──────────────────────────────────────────────────────────

def _aggregate_metrics(per_query: list[dict]) -> EvalMetrics:
    if not per_query:
        return EvalMetrics(
            precision_at_5=0.0, precision_at_10=0.0,
            ndcg_at_5=0.0, ndcg_at_10=0.0,
            recall_at_10=0.0, mrr=0.0, num_queries=0
        )
    n = len(per_query)
    def avg(key): return sum(q.get(key, 0.0) for q in per_query) / n
    return EvalMetrics(
        precision_at_5=round(avg("precision_at_5"), 4),
        precision_at_10=round(avg("precision_at_10"), 4),
        ndcg_at_5=round(avg("ndcg_at_5"), 4),
        ndcg_at_10=round(avg("ndcg_at_10"), 4),
        recall_at_10=round(avg("recall_at_10"), 4),
        mrr=round(avg("mrr"), 4),
        num_queries=n,
    )


def run_evaluation(model: str = "nexora", max_queries: Optional[int] = None) -> tuple[EvalMetrics, list[dict]]:
    """
    Run evaluation for a given model against APS-04 eval set.
    Returns (aggregate_metrics, per_query_results).
    Model: "popularity" | "semantic" | "hybrid" | "nexora"
    """
    eval_data = load_eval_data()
    if max_queries:
        eval_data = eval_data[:max_queries]

    per_query_results = []

    for q in eval_data:
        qid = q["query_id"]
        query_text = q["query_text"]
        target_type = q["target_entity_type"]
        city_id = q["city_id"]
        k = q["k"] or 10
        labels = q["labels"]

        # Only evaluate on entity types we support (hotel, poi, package)
        if target_type not in ("hotel", "poi", "package"):
            continue

        try:
            if model == "popularity":
                retrieved = popularity_retrieve(target_type, city_id, k)
            elif model == "semantic":
                retrieved = semantic_retrieve(query_text, target_type, city_id, k)
            elif model == "hybrid":
                retrieved = hybrid_retrieve(query_text, target_type, city_id, k)
            elif model == "nexora":
                retrieved = nexora_retrieve(
                    query_text, target_type, city_id,
                    q.get("persona_user_id"), q.get("filters_json", "{}"), k
                )
            else:
                continue

            metrics = compute_query_metrics(retrieved, labels)
            per_query_results.append({
                "query_id": qid,
                "query_text": query_text,
                "language": q["language"],
                "intent": q["intent"],
                "retrieved": retrieved,
                "labels": labels,
                **metrics
            })
        except Exception as e:
            logger.error(f"Evaluation error for query {qid}: {e}")
            continue

    aggregate = _aggregate_metrics(per_query_results)
    return aggregate, per_query_results


def run_full_comparison(max_queries: Optional[int] = None) -> EvaluationComparison:
    """Run all four models and return comparison."""
    logger.info("Running evaluation comparison across all models...")
    pop_metrics, _ = run_evaluation("popularity", max_queries)
    sem_metrics, _ = run_evaluation("semantic", max_queries)
    hyb_metrics, _ = run_evaluation("hybrid", max_queries)
    nex_metrics, _ = run_evaluation("nexora", max_queries)
    return EvaluationComparison(
        popularity=pop_metrics,
        semantic=sem_metrics,
        hybrid=hyb_metrics,
        nexora=nex_metrics,
    )


def get_failure_cases(model: str = "nexora", max_queries: Optional[int] = None, n: int = 10) -> list[dict]:
    """Return worst-performing queries for failure analysis."""
    _, per_query = run_evaluation(model, max_queries)
    per_query.sort(key=lambda q: q.get("ndcg_at_10", 1.0))
    failures = []
    for q in per_query[:n]:
        labels = q.get("labels", {})
        retrieved = q.get("retrieved", [])
        expected = [eid for eid, grade in sorted(labels.items(), key=lambda x: -x[1]) if grade >= 2][:5]
        missing = [e for e in expected if e not in retrieved[:10]]

        reason = "unknown"
        if not retrieved:
            reason = "no candidates retrieved"
        elif q.get("ndcg_at_10", 0) < 0.1:
            reason = "semantic miss — embedding model may not match query language/domain"
        elif q.get("precision_at_5", 0) == 0:
            reason = "candidate recall issue — hard filters may be excluding relevant items"
        elif q.get("mrr", 0) == 0:
            reason = "relevant items exist but ranked too low"

        failures.append({
            "query_id": q["query_id"],
            "query_text": q["query_text"],
            "language": q["language"],
            "intent": q["intent"],
            "expected_items": expected,
            "retrieved_items": retrieved[:10],
            "metric": q.get("ndcg_at_10", 0.0),
            "possible_reason": reason,
        })
    return failures
