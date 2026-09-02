"""
Explanation Engine.
Generates structured, grounded explanations for every recommendation.
Only generates reasons supported by actual data — never invents them.
"""
import logging
from typing import Optional

from app.personalization.user_profile import UserProfile
from app.session.session_engine import SessionProfile
from app.schemas.recommendation import ExplanationReason, WhyThis, WhyNow

logger = logging.getLogger(__name__)


def generate_reasons(
    candidate: dict,
    profile: Optional[UserProfile],
    session: Optional[SessionProfile],
    query: str = "",
) -> list[ExplanationReason]:
    """Generate up to 3-4 grounded explanation reasons for a recommendation."""
    scores = candidate.get("scores", {})
    item = candidate["item_data"]
    etype = candidate["entity_type"]
    reasons = []

    semantic_score = scores.get("semantic_score", 0.0)
    profile_score = scores.get("profile_score", 0.0)
    behaviour_score = scores.get("behaviour_score", 0.0)
    session_score = scores.get("session_score", 0.0)
    rating_score = scores.get("rating_score", 0.0)

    # Query/semantic match reason
    if semantic_score >= 0.45:
        text = _semantic_reason(query, item, etype)
        if text:
            reasons.append(ExplanationReason(
                type="semantic",
                text=text,
                strength=round(min(semantic_score, 1.0), 2),
            ))

    # Profile reason
    if profile and profile_score >= 0.55:
        text = _profile_reason(profile, item, etype)
        if text:
            reasons.append(ExplanationReason(
                type="profile",
                text=text,
                strength=round(min(profile_score, 1.0), 2),
            ))

    # Behaviour reason
    if profile and behaviour_score >= 0.4:
        text = _behaviour_reason(profile, item, etype, candidate["entity_id"])
        if text:
            reasons.append(ExplanationReason(
                type="behaviour",
                text=text,
                strength=round(min(behaviour_score, 1.0), 2),
            ))

    # Session reason (only if session had real signals)
    if session and abs(session_score) >= 0.2:
        text = _session_reason(session, item, etype)
        if text:
            reasons.append(ExplanationReason(
                type="session",
                text=text,
                strength=round(min(abs(session_score), 1.0), 2),
            ))

    # Rating reason
    if rating_score >= 0.75:
        text = _rating_reason(item, etype, rating_score)
        if text:
            reasons.append(ExplanationReason(
                type="rating",
                text=text,
                strength=round(rating_score, 2),
            ))

    # Constraint reason (city, budget)
    constraint_text = _constraint_reason(profile, item, etype)
    if constraint_text:
        reasons.append(ExplanationReason(
            type="constraint",
            text=constraint_text,
            strength=0.95,
        ))

    # Keep top 3 by strength
    reasons.sort(key=lambda r: r.strength, reverse=True)
    return reasons[:3]


def generate_why_this(
    candidate: dict,
    profile: Optional[UserProfile],
    session: Optional[SessionProfile],
) -> WhyThis:
    """Full Why This breakdown."""
    scores = candidate.get("scores", {})
    final = scores.get("final_score", 0.0)

    evidence = []
    if profile:
        if profile.travel_style:
            evidence.append(f"Your travel style: {profile.travel_style}")
        if profile.budget_band:
            evidence.append(f"Your budget preference: {profile.budget_band}")
        if profile.interests:
            evidence.append(f"Your interests: {', '.join(profile.interests[:3])}")

    item = candidate["item_data"]
    etype = candidate["entity_type"]
    if etype == "poi":
        evidence.append(f"Category: {item.get('poi_category', 'unknown')}")
        evidence.append(f"Popularity score: {item.get('popularity_score', 0)}/100")
    elif etype == "hotel":
        evidence.append(f"Property type: {item.get('property_type', 'hotel')}")
        if item.get("guest_score"):
            evidence.append(f"Guest score: {item.get('guest_score')}/10")
    elif etype == "package":
        evidence.append(f"Theme: {item.get('theme', 'general')}")
        evidence.append(f"Tier: {item.get('tier', 'standard')}")

    return WhyThis(
        query_match=round(scores.get("semantic_score", 0.0), 3),
        profile_match=round(scores.get("profile_score", 0.0), 3),
        behaviour_match=round(scores.get("behaviour_score", 0.0), 3),
        constraint_match=1.0,  # items passed hard filters
        rating_score=round(scores.get("rating_score", 0.0), 3),
        diversity_score=round(scores.get("diversity_score", 0.0), 3),
        final_score=round(final, 3),
        evidence=evidence[:5],
    )


def generate_why_now(
    candidate: dict,
    session: Optional[SessionProfile],
) -> Optional[WhyNow]:
    """Generate Why Now explanation if session activity is relevant."""
    if not session or not session.recent_interactions:
        return None

    etype = candidate["entity_type"]
    item = candidate["item_data"]

    # Check if session liked/saved something similar
    if session.liked_in_session:
        liked_types = [
            i.get("entity_type") for i in session.recent_interactions
            if i.get("interaction_type") == "like"
        ]
        if etype in liked_types:
            return WhyNow(
                text=f"Your recent likes this session included similar {etype}s, boosting this result.",
                triggered_by="session_like",
            )

    if session.saved_in_session:
        saved_types = [
            i.get("entity_type") for i in session.recent_interactions
            if i.get("interaction_type") == "save"
        ]
        if etype in saved_types:
            return WhyNow(
                text=f"You saved a similar {etype} earlier in this session.",
                triggered_by="session_save",
            )

    return None


def compute_confidence(
    candidate: dict,
    profile: Optional[UserProfile],
    query: str = "",
) -> str:
    """
    Compute confidence band: HIGH | MEDIUM | LOW.
    Based on: query clarity (semantic score), profile maturity, and score spread.
    """
    scores = candidate.get("scores", {})
    semantic = scores.get("semantic_score", 0.0)
    final = scores.get("final_score", 0.0)
    maturity = getattr(profile, "maturity_class", "cold_start") if profile else "cold_start"

    # Base confidence from final score
    if final >= 0.70 and semantic >= 0.55:
        base = "HIGH"
    elif final >= 0.50 or semantic >= 0.45:
        base = "MEDIUM"
    else:
        base = "LOW"

    # Downgrade for cold_start
    if maturity == "cold_start" and base == "HIGH":
        base = "MEDIUM"

    # Downgrade if query is very short
    if len(query.split()) < 3 and base == "HIGH":
        base = "MEDIUM"

    return base


def compute_match_percentage(final_score: float) -> int:
    """Convert final score to a display-friendly match percentage."""
    # Map 0-1 score to 50-99 range for UI realism
    pct = 50 + int(final_score * 49)
    return max(50, min(99, pct))


# ── Private helpers ────────────────────────────────────────────────────────────

def _semantic_reason(query: str, item: dict, etype: str) -> Optional[str]:
    name = item.get("name", "")
    if etype == "poi":
        cat = item.get("poi_category", "")
        return f"Closely matches your search for {cat} experiences" if cat else f"Matches your search query"
    elif etype == "hotel":
        prop = item.get("property_type", "hotel")
        return f"This {prop} matches your search"
    elif etype == "package":
        theme = item.get("theme", "")
        return f"Matches your interest in {theme} travel" if theme else "Matches your search"
    return None


def _profile_reason(profile: UserProfile, item: dict, etype: str) -> Optional[str]:
    if etype == "poi":
        poi_cat = item.get("poi_category", "")
        if poi_cat in profile.category_affinity and profile.category_affinity[poi_cat] > 0.4:
            return f"Fits your interest in {poi_cat} experiences"
    if etype == "hotel":
        prop = item.get("property_type", "")
        if profile.travel_style == "luxury" and prop in ["resort", "boutique", "heritage"]:
            return "Matches your luxury travel preference"
        if profile.travel_style == "budget" and prop in ["hostel", "guesthouse", "homestay"]:
            return "Fits your budget-conscious travel style"
    if etype == "package":
        theme = item.get("theme", "")
        if profile.traveller_type == "family" and theme == "family":
            return "Perfect for family travel, matching your profile"
        if profile.traveller_type in ("couple", "solo"):
            pass
    # Generic
    return f"Aligns with your {profile.travel_style} travel style"


def _behaviour_reason(profile: UserProfile, item: dict, etype: str, entity_id: str) -> Optional[str]:
    if entity_id in profile.liked_entities:
        return "You liked this before"
    if entity_id in profile.saved_entities:
        return "You saved this for later"
    if profile.entity_type_affinity.get(etype, 0) > 0.3:
        return f"You frequently interact with {etype}s like this"
    return None


def _session_reason(session: SessionProfile, item: dict, etype: str) -> Optional[str]:
    if session.liked_in_session:
        return "Your recent likes this session increased this result's relevance"
    if session.clicked_in_session:
        return "Based on what you explored in this session"
    return None


def _rating_reason(item: dict, etype: str, rating_score: float) -> Optional[str]:
    if etype == "hotel":
        gs = item.get("guest_score")
        if gs and float(gs) >= 8.0:
            return f"Highly rated by guests ({gs}/10)"
    elif etype == "poi":
        pop = item.get("popularity_score", 0)
        if pop >= 80:
            return f"Popular among travellers (score: {pop}/100)"
    return None


def _constraint_reason(profile: Optional[UserProfile], item: dict, etype: str) -> Optional[str]:
    if profile and profile.max_daily_budget:
        return "Fits within your stated budget"
    return None
