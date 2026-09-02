"""
Evaluation API endpoints.
Runs against the real APS-04 eval_queries and eval_relevance_labels.
Returns honest, unmanipulated metrics.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from app.schemas.recommendation import (
    EvaluationSummary, EvaluationComparison, QueryEvalResult, EvalMetrics
)
from app.evaluation.evaluator import (
    run_evaluation, run_full_comparison, get_failure_cases
)
from app.evaluation.metrics import load_eval_data, compute_query_metrics

logger = logging.getLogger(__name__)
router = APIRouter()

# Cached results so we don't re-run on every request
_cached_summary: Optional[EvaluationSummary] = None
_cached_comparison: Optional[EvaluationComparison] = None
_cached_per_query: Optional[list] = None


@router.get("/evaluation/summary", response_model=EvaluationSummary)
async def get_evaluation_summary(
    force_refresh: bool = Query(False, description="Re-run evaluation instead of using cache"),
    max_queries: Optional[int] = Query(None, description="Limit number of eval queries (for speed)")
):
    """
    Get NEXORA evaluation summary metrics.
    Uses real APS-04 eval_queries and eval_relevance_labels as ground truth.
    """
    global _cached_summary, _cached_per_query
    if _cached_summary and not force_refresh:
        return _cached_summary
    try:
        metrics, per_query = run_evaluation("nexora", max_queries=max_queries)
        _cached_per_query = per_query
        _cached_summary = EvaluationSummary(
            number_of_queries=metrics.num_queries,
            precision_at_5=metrics.precision_at_5,
            precision_at_10=metrics.precision_at_10,
            ndcg_at_5=metrics.ndcg_at_5,
            ndcg_at_10=metrics.ndcg_at_10,
            recall_at_10=metrics.recall_at_10,
            mrr=metrics.mrr,
        )
        return _cached_summary
    except Exception as e:
        logger.error(f"Evaluation summary error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.get("/evaluation/comparison", response_model=EvaluationComparison)
async def get_evaluation_comparison(
    force_refresh: bool = Query(False),
    max_queries: Optional[int] = Query(20, description="Queries per model (default 20 for speed)")
):
    """
    Compare all four models: Popularity, Semantic, Hybrid, NEXORA.
    Returns honest metrics — no manipulation.
    """
    global _cached_comparison
    if _cached_comparison and not force_refresh:
        return _cached_comparison
    try:
        comparison = run_full_comparison(max_queries=max_queries)
        _cached_comparison = comparison
        return comparison
    except Exception as e:
        logger.error(f"Comparison error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/evaluation/query/{query_id}", response_model=QueryEvalResult)
async def get_query_eval(query_id: str):
    """
    Get per-query evaluation result: ground truth, retrieved items, ranks, grades, metrics.
    """
    try:
        # Load labels for this query
        eval_data = load_eval_data()
        query_data = next((q for q in eval_data if q["query_id"] == query_id), None)
        if not query_data:
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")

        # Run NEXORA retrieval for this query
        from app.evaluation.evaluator import nexora_retrieve
        retrieved = nexora_retrieve(
            query_text=query_data["query_text"],
            target_entity_type=query_data["target_entity_type"],
            city_id=query_data.get("city_id"),
            persona_user_id=query_data.get("persona_user_id"),
            filters_json=query_data.get("filters_json", "{}"),
            k=query_data["k"] or 10,
        )

        labels = query_data["labels"]
        ranks = {eid: i + 1 for i, eid in enumerate(retrieved)}
        metrics = compute_query_metrics(retrieved, labels)

        ground_truth = [
            {"entity_id": eid, "grade": grade}
            for eid, grade in sorted(labels.items(), key=lambda x: -x[1])
            if grade >= 2
        ]

        return QueryEvalResult(
            query_id=query_id,
            query_text=query_data["query_text"],
            language=query_data["language"],
            intent=query_data["intent"],
            ground_truth=ground_truth,
            retrieved_items=retrieved,
            ranks=ranks,
            relevance={eid: labels.get(eid, 0) for eid in retrieved},
            metrics=metrics,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query eval error for {query_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluation/queries")
async def list_eval_queries(limit: int = Query(20)):
    """List available evaluation queries."""
    try:
        eval_data = load_eval_data()
        return {
            "total": len(eval_data),
            "queries": [
                {
                    "query_id": q["query_id"],
                    "query_text": q["query_text"],
                    "language": q["language"],
                    "intent": q["intent"],
                    "target_entity_type": q["target_entity_type"],
                    "k": q["k"],
                }
                for q in eval_data[:limit]
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluation/failures")
async def get_failure_analysis(
    model: str = Query("nexora"),
    max_queries: Optional[int] = Query(30),
    n: int = Query(10),
):
    """Return worst-performing queries with failure analysis."""
    try:
        failures = get_failure_cases(model=model, max_queries=max_queries, n=n)
        return {"model": model, "failures": failures}
    except Exception as e:
        logger.error(f"Failure analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
