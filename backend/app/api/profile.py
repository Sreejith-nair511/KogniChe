"""Profile API endpoint."""
import logging
from fastapi import APIRouter, HTTPException
from app.schemas.recommendation import ProfileSummary
from app.personalization.user_profile import get_or_build_profile
from app.services.recommendation_service import _build_profile_summary
from app.database.connection import get_source_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/profile/{user_id}", response_model=ProfileSummary)
async def get_profile(user_id: str):
    """
    Get full user profile including DNA, preferences, maturity, and interaction summary.
    """
    try:
        profile = get_or_build_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        summary = _build_profile_summary(profile)
        if not summary:
            raise HTTPException(status_code=404, detail=f"Profile not available for {user_id}")
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile error for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
async def list_users(segment: str = None, limit: int = 20):
    """List users from APS-04, optionally filtered by segment."""
    try:
        with get_source_db() as conn:
            cur = conn.cursor()
            if segment:
                cur.execute(
                    "SELECT user_id, display_name, locale, budget_band, travel_style, traveller_type, segment FROM users WHERE segment = ? AND status = 'active' LIMIT ?",
                    (segment, limit)
                )
            else:
                cur.execute(
                    "SELECT user_id, display_name, locale, budget_band, travel_style, traveller_type, segment FROM users WHERE status = 'active' LIMIT ?",
                    (limit,)
                )
            return {"users": [dict(r) for r in cur.fetchall()]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
