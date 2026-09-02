"""Interaction recording API endpoint."""
import logging
from fastapi import APIRouter, HTTPException
from app.schemas.recommendation import InteractionRequest, InteractionResponse
from app.services.interaction_service import record_interaction

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/interactions", response_model=InteractionResponse)
async def record_interaction_endpoint(request: InteractionRequest):
    """
    Record a user interaction (like, save, dislike, click, view, etc.).
    Updates user profile + session, re-ranks recommendations, returns rank movements.
    """
    try:
        return record_interaction(request)
    except Exception as e:
        logger.error(f"Interaction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Interaction recording failed: {str(e)}")
