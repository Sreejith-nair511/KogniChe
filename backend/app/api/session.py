"""Session API endpoint."""
import logging
from fastapi import APIRouter, HTTPException
from app.schemas.recommendation import SessionSummary
from app.session.session_engine import create_or_load_session
from app.services.recommendation_service import _build_session_summary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/session/{session_id}", response_model=SessionSummary)
async def get_session(session_id: str):
    """Get current session state including constraints, interactions, and ranking changes."""
    try:
        session = create_or_load_session(session_id, user_id=None)
        summary = _build_session_summary(session)
        if not summary:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session error for {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
