"""
Personalized Reranker.
Combines semantic, profile, behaviour, collaborative, rating, popularity, and diversity scores
into a final ranking. Weights are configurable. Profile maturity dynamically adjusts weights.
"""
import logging
import math
from typing import Optional
import numpy as np

from app.core.config import settings
from app.personalization.user_profile import UserProfile
from app.session.session_engine import SessionProfile, get_session_score
from app.database.connection import get_source_db

logger = logging.getLogger(__name__)


def compute_profile_score(candidate: dict, profile: Optional[UserProfile]) -> float:
    """Score how well a candidate matches a user's explicit preferences and travel style."""
    if not profile:
        return 0.5

    item = candidate["item_data"]
    etype = candidate["entity_type"]
    score = 0.5  # base

    # Budget match
    if profile.max_daily_budget:
        try:
            budget = float(profile.max_daily_budget)
            if etype == "hotel":
                # Hotel star_rating as proxy if no room type data
                star = item.get("star_rating", 3)
                band_map = {"shoestring": 1, "value": 2, "mid": 3, "premium": 4, "luxury": 5}
                expected_star = band_map.get(profile.budget_band, 3)
                if abs(star - expected_star) <= 1:
                    score += 0.15
            elif etype == "poi":
                entry_cost = float(item.get("entry_cost", 0) or 0)
                if entry_cost == 0 or entry_cost <= budget:
                    score += 0.10
            elif etype == "package":
                base_price = float(item.get("base_price", 0) or 0)
                if base_price <= budget * 5:  # rough multi-day comparison
                    score += 0.10
        except (ValueError, TypeError):
            pass

    # Travel style match
    travel_style = profile.travel_style
    if etype == "hotel":
        prop_type = item.get("property_type", "")
        style_hotel_match = {
            "luxury": ["resort", "boutique", "heritage"],
            "budget": ["hostel", "guesthouse", "homestay"],
            "comfort": ["hotel", "apartment"],
            "adventure": ["guesthouse", "hostel", "homestay"],
            "wellness": ["resort", "boutique"],
            "cultural": ["heritage", "boutique"],
        }
        preferred_types = style_hotel_match.get(travel_style, [])
        if prop_type in preferred_types:
            score += 0.20

    elif etype == "poi":
        poi_cat = item.get("poi_category", "")
        style_poi_match = {
            "adventure": ["adventure", "nature", "wildlife"],
            "cultural": ["heritage", "museum", "religious"],
            "wellness": ["wellness", "beach", "nature"],
            "budget": ["heritage", "nature", "viewpoint"],
            "luxury": ["beach", "wellness"],
        }
        preferred_cats = style_poi_match.get(travel_style, [])
        if poi_cat in preferred_cats:
            score += 0.25
        # Category affinity from profile
        cat_score = profile.category_affinity.get(poi_cat, 0.0)
        score += cat_score * 0.20

    elif etype == "package":
        theme = item.get("theme", "")
        style_theme_match = {
            "adventure": ["adventure", "wildlife"],
            "cultural": ["heritage", "pilgrimage"],
            "wellness": ["wellness", "honeymoon"],
            "luxury": ["honeymoon", "wellness"],
            "budget": ["family", "pilgrimage"],
        }
        preferred_themes = style_theme_match.get(travel_style, [])
        if theme in preferred_themes:
            score += 0.25

    # Language preference match
    if etype == "package" and profile.preferred_languages:
        langs_offered = item.get("languages_offered", "")
        if langs_offered:
            offered = [l.strip() for l in langs_offered.split(",")]
            if any(pl in offered for pl in profile.preferred_languages):
                score += 0.15

    # Traveller type match for packages
    if etype == "package" and profile.traveller_type:
        theme = item.get("theme", "")
        type_theme = {
            "family": ["family"],
            "couple": ["honeymoon"],
            "solo": ["adventure", "wellness"],
            "friends": ["adventure", "food_trail"],
            "senior": ["heritage", "pilgrimage", "wellness"],
        }
        preferred = type_theme.get(profile.traveller_type, [])
        if theme in preferred:
            score += 0.10

    # Pace match
    if etype == "poi":
        duration = item.get("typical_duration_minutes", 60)
        if profile.pace == "relaxed" and duration <= 60:
            score += 0.10
        elif profile.pace == "packed" and duration >= 90:
            score += 0.10

    return min(score, 1.0)


def compute_behaviour_score(candidate: dict, profile: Optional[UserProfile]) -> float:
    """Score based on past interaction behaviour."""
    if not profile or profile.interaction_count == 0:
        return 0.0

    eid = candidate["entity_id"]
    etype = candidate["entity_type"]

    # Liked/saved = strong positive
    if eid in profile.liked_entities:
        return 0.9
    if eid in profile.saved_entities:
        return 0.8
    # Disliked = strong negative
    if eid in profile.disliked_entities:
        return -0.5

    # Entity type affinity
    type_score = profile.entity_type_affinity.get(etype, 0.0)
    return max(0.0, min(type_score, 0.6))


def compute_rating_score(candidate: dict) -> float:
    """Normalize rating to 0-1."""
    item = candidate["item_data"]
    etype = candidate["entity_type"]
    if etype == "hotel":
        score = item.get("guest_score")
        if score is not None:
            return float(score) / 10.0
        # Fallback to star rating
        stars = item.get("star_rating", 3)
        return stars / 5.0
    elif etype == "poi":
        pop = item.get("popularity_score", 50)
        return float(pop) / 100.0
    elif etype == "package":
        # No direct rating — use tier proxy
        tier_map = {"standard": 0.5, "deluxe": 0.7, "premium": 0.9}
        return tier_map.get(item.get("tier", "standard"), 0.5)
    return 0.5


def compute_popularity_score(candidate: dict) -> float:
    """Normalize popularity to 0-1."""
    item = candidate["item_data"]
    etype = candidate["entity_type"]
    if etype == "poi":
        return float(item.get("popularity_score", 50)) / 100.0
    elif etype == "hotel":
        rc = item.get("review_count", 0)
        return min(float(rc) / 500.0, 1.0)
    elif etype == "package":
        # Approximate from group size capacity
        max_group = item.get("max_group_size", 10)
        return min(float(max_group) / 20.0, 1.0)
    return 0.5


def compute_collaborative_score(candidate: dict, profile: Optional[UserProfile]) -> float:
    """
    Lightweight collaborative signal using APS-04 interaction data.
    Finds users with similar travel_style + budget_band and checks their interactions.
    """
    if not profile or profile.maturity_class == "cold_start":
        return 0.0

    eid = candidate["entity_id"]
    etype = candidate["entity_type"]

    try:
        with get_source_db() as conn:
            cur = conn.cursor()
            # Find similar users by travel_style + budget_band
            cur.execute("""
                SELECT COUNT(DISTINCT i.user_id) as cnt
                FROM user_interactions i
                JOIN users u ON i.user_id = u.user_id
                WHERE u.travel_style = ?
                  AND u.budget_band = ?
                  AND i.entity_id = ?
                  AND i.entity_type = ?
                  AND i.interaction_type IN ('like', 'save', 'book')
                  AND i.user_id != ?
            """, (profile.travel_style, profile.budget_band, eid, etype, profile.user_id))
            row = cur.fetchone()
            if row and row["cnt"] > 0:
                return min(float(row["cnt"]) / 10.0, 0.5)
    except Exception as e:
        logger.debug(f"Collaborative score error: {e}")

    return 0.0


def get_dynamic_weights(profile: Optional[UserProfile]) -> dict[str, float]:
    """
    Adjust ranking weights based on profile maturity.
    Cold-start: emphasize semantic + rating + popularity.
    Mature: emphasize behaviour + profile.
    """
    if not profile or profile.maturity_class == "cold_start":
        return {
            "semantic": 0.55,
            "profile": 0.20,
            "behaviour": 0.0,
            "collaborative": 0.0,
            "rating": 0.10,
            "popularity": 0.08,
            "diversity": 0.07,
        }
    elif profile.maturity_class == "early":
        return {
            "semantic": 0.48,
            "profile": 0.22,
            "behaviour": 0.05,
            "collaborative": 0.02,
            "rating": 0.08,
            "popularity": 0.07,
            "diversity": 0.08,
        }
    elif profile.maturity_class == "learning":
        return {
            "semantic": 0.40,
            "profile": 0.25,
            "behaviour": 0.12,
            "collaborative": 0.04,
            "rating": 0.06,
            "popularity": 0.05,
            "diversity": 0.08,
        }
    else:  # mature
        return {
            "semantic": settings.WEIGHT_SEMANTIC,
            "profile": settings.WEIGHT_PROFILE,
            "behaviour": settings.WEIGHT_BEHAVIOUR,
            "collaborative": settings.WEIGHT_COLLABORATIVE,
            "rating": settings.WEIGHT_RATING,
            "popularity": settings.WEIGHT_POPULARITY,
            "diversity": settings.WEIGHT_DIVERSITY,
        }


def compute_raw_score(
    candidate: dict,
    profile: Optional[UserProfile],
    session: Optional[SessionProfile],
    weights: dict[str, float],
) -> dict[str, float]:
    """Compute all component scores and weighted final score."""
    semantic = candidate.get("semantic_score", 0.5)
    profile_s = compute_profile_score(candidate, profile)
    behaviour_s = compute_behaviour_score(candidate, profile)
    collab_s = compute_collaborative_score(candidate, profile)
    rating_s = compute_rating_score(candidate)
    popularity_s = compute_popularity_score(candidate)

    # Session boost
    session_s = 0.0
    if session:
        session_s = get_session_score(session, candidate["entity_id"], candidate["entity_type"])

    # Weighted combination (session is additive bonus, not a weighted component)
    final = (
        weights["semantic"] * semantic
        + weights["profile"] * profile_s
        + weights["behaviour"] * behaviour_s
        + weights["collaborative"] * collab_s
        + weights["rating"] * rating_s
        + weights["popularity"] * popularity_s
        + 0.15 * session_s  # session always contributes
    )

    # Hard penalty for disliked items
    if profile and candidate["entity_id"] in profile.disliked_entities:
        final = min(final * 0.2, 0.1)

    if session and candidate["entity_id"] in session.disliked_in_session:
        final = min(final * 0.1, 0.05)

    return {
        "semantic_score": semantic,
        "profile_score": profile_s,
        "behaviour_score": behaviour_s,
        "collaborative_score": collab_s,
        "rating_score": rating_s,
        "popularity_score": popularity_s,
        "session_score": session_s,
        "final_score": max(0.0, min(final, 1.0)),
    }


def mmr_diversify(
    scored_candidates: list[dict],
    lambda_param: float = 0.7,
    top_k: int = 10,
) -> list[dict]:
    """
    Maximal Marginal Relevance diversification.
    Balances relevance (final_score) with diversity across entity types + categories.
    lambda = 1.0 → pure relevance; lambda = 0.0 → pure diversity.
    """
    if len(scored_candidates) <= top_k:
        return scored_candidates

    selected = []
    remaining = list(scored_candidates)

    def category_of(c: dict) -> str:
        item = c["item_data"]
        return (
            item.get("poi_category") or
            item.get("property_type") or
            item.get("theme") or
            c["entity_type"]
        )

    while len(selected) < top_k and remaining:
        if not selected:
            # First: pick highest relevance
            best = max(remaining, key=lambda c: c["scores"]["final_score"])
        else:
            # MMR: relevance minus similarity to already selected
            selected_cats = [category_of(s) for s in selected]
            selected_etypes = [s["entity_type"] for s in selected]

            def mmr_score(c: dict) -> float:
                rel = c["scores"]["final_score"]
                cat = category_of(c)
                etype = c["entity_type"]
                # Simple diversity penalty: fraction of selected with same category/type
                cat_sim = selected_cats.count(cat) / len(selected_cats)
                type_sim = selected_etypes.count(etype) / len(selected_etypes)
                diversity_penalty = (cat_sim + type_sim) / 2.0
                return lambda_param * rel - (1 - lambda_param) * diversity_penalty

            best = max(remaining, key=mmr_score)

        selected.append(best)
        remaining.remove(best)

    return selected


def rank_candidates(
    candidates: list[dict],
    profile: Optional[UserProfile],
    session: Optional[SessionProfile],
    top_k: int = 10,
) -> list[dict]:
    """
    Full reranking pipeline:
    1. Compute all scores
    2. Apply MMR diversification
    3. Return top_k ranked candidates
    """
    weights = get_dynamic_weights(profile)

    # Score all candidates
    scored = []
    for c in candidates:
        scores = compute_raw_score(c, profile, session, weights)
        c["scores"] = scores
        scored.append(c)

    # Sort by final_score descending
    scored.sort(key=lambda c: c["scores"]["final_score"], reverse=True)

    # MMR diversification
    diversified = mmr_diversify(scored, lambda_param=settings.DIVERSITY_LAMBDA, top_k=top_k)

    # Assign final ranks
    for i, c in enumerate(diversified):
        c["rank"] = i + 1

    return diversified
