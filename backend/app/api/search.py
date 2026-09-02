"""Search API endpoint."""
import logging
from fastapi import APIRouter, HTTPException
from app.schemas.recommendation import SearchRequest, SearchResponse
from app.services.recommendation_service import search

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest):
    """
    Main recommendation search endpoint.
    Accepts a natural language query + optional filters + user/session IDs.
    Returns ranked, personalized, explained recommendations from APS-04 data.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty")
    try:
        return search(request)
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
