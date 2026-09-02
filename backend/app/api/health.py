"""Health check API."""
import logging
from fastapi import APIRouter
from app.schemas.recommendation import HealthResponse
from app.database.connection import check_source_db, check_runtime_db
from app.embeddings.engine import index_status

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    System health check.
    Verifies: API, source DB, runtime DB, vector index, embedding model.
    """
    details = {}

    # Source DB
    src = check_source_db()
    db_status = src["status"]
    if src["status"] == "ok":
        counts = src.get("counts", {})
        details["source_db_tables"] = len(src.get("tables", []))
        details["users"] = counts.get("users", 0)
        details["hotels"] = counts.get("hotels", 0)
        details["activities_poi"] = counts.get("activities_poi", 0)
        details["tour_packages"] = counts.get("tour_packages", 0)
        details["interactions"] = counts.get("user_interactions", 0)
        details["eval_queries"] = counts.get("eval_queries", 0)

    # Runtime DB
    rt = check_runtime_db()
    details["runtime_db"] = rt["status"]

    # Vector index
    vi = index_status()
    vi_status = vi["status"]
    details["vector_index_vectors"] = vi.get("total_vectors", 0)

    # Embedding model — just check if importable
    embedding_status = "ok"
    try:
        from sentence_transformers import SentenceTransformer
        from app.core.config import settings
        details["embedding_model_name"] = settings.EMBEDDING_MODEL
    except ImportError:
        embedding_status = "unavailable"

    overall = "ok" if all(s == "ok" for s in [db_status, rt["status"], embedding_status]) else "degraded"
    if vi_status != "ok":
        overall = "degraded"
        details["warning"] = "Vector index not loaded. Run scripts/generate_embeddings.py"

    return HealthResponse(
        status=overall,
        api="ok",
        database=db_status,
        vector_index=vi_status,
        embedding_model=embedding_status,
        dataset=db_status,
        details=details,
    )


@router.get("/recommendation/{entity_id}/trace")
async def recommendation_trace(
    entity_id: str,
    query: str = "",
    user_id: str = None,
):
    """
    Debug endpoint: trace why a specific entity scored the way it did.
    Returns full scoring breakdown for developer inspection.
    """
    from app.services.query_understanding import extract_constraints, build_semantic_text
    from app.retrieval.hybrid_retriever import build_candidate_pool
    from app.personalization.user_profile import get_or_build_profile
    from app.ranking.personalized_ranker import compute_raw_score, get_dynamic_weights
    from app.session.session_engine import create_or_load_session
    from app.schemas.recommendation import QueryConstraints

    if not query:
        query = "travel recommendation"

    constraints = extract_constraints(query)
    semantic_text = build_semantic_text(query, constraints)
    candidates, telemetry = build_candidate_pool(
        query=query,
        constraints=constraints,
        semantic_text=semantic_text,
        top_k=200,
    )

    target = next((c for c in candidates if c["entity_id"] == entity_id), None)
    if not target:
        return {"error": f"Entity {entity_id} not found in candidate pool for this query", "telemetry": telemetry.model_dump()}

    profile = get_or_build_profile(user_id) if user_id else None
    session = create_or_load_session(None, user_id)
    weights = get_dynamic_weights(profile)
    scores = compute_raw_score(target, profile, session, weights)

    return {
        "entity_id": entity_id,
        "entity_type": target["entity_type"],
        "title": target["item_data"].get("name", ""),
        "query": query,
        "weights": weights,
        "scores": scores,
        "candidate_generation": {
            "in_candidate_pool": True,
            "semantic_score": target.get("semantic_score", 0),
        },
        "filtering": {"passed_hard_filters": True},
        "telemetry": telemetry.model_dump(),
    }
