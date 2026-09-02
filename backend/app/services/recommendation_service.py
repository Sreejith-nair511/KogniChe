"""
Main Recommendation Service.
Orchestrates the full pipeline: query → retrieval → ranking → explanation → response.
"""
import uuid
import json
import logging
import time
from typing import Optional
from decimal import Decimal

from app.schemas.recommendation import (
    SearchRequest, SearchResponse, RecommendationItem, Price,
    ProfileSummary, SessionSummary, ProfileDNA, DNADimension,
    QueryIntent, QueryConstraints, RankChange,
)
from app.services.query_understanding import (
    detect_language, extract_constraints, detect_intent, build_semantic_text,
)
from app.retrieval.hybrid_retriever import build_candidate_pool
from app.personalization.user_profile import get_or_build_profile, UserProfile
from app.session.session_engine import (
    create_or_load_session, update_session_query, get_session_score, SessionProfile
)
from app.ranking.personalized_ranker import rank_candidates
from app.explanations.explanation_engine import (
    generate_reasons, generate_why_this, generate_why_now,
    compute_confidence, compute_match_percentage,
)

logger = logging.getLogger(__name__)


# ── Image placeholder helpers ────────────────────────────────────────────────────

# Curated Unsplash placeholders by entity type / category
POI_CATEGORY_IMAGES = {
    "heritage": "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=800&q=80",
    "nature": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&w=800&q=80",
    "beach": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
    "adventure": "https://images.unsplash.com/photo-1551632811-561732d1e306?auto=format&fit=crop&w=800&q=80",
    "museum": "https://images.unsplash.com/photo-1565060169194-19fababbbb3b?auto=format&fit=crop&w=800&q=80",
    "food": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?auto=format&fit=crop&w=800&q=80",
    "religious": "https://images.unsplash.com/photo-1603569283847-aa295f0d016a?auto=format&fit=crop&w=800&q=80",
    "wildlife": "https://images.unsplash.com/photo-1516426122078-c23e76319801?auto=format&fit=crop&w=800&q=80",
    "wellness": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?auto=format&fit=crop&w=800&q=80",
    "shopping": "https://images.unsplash.com/photo-1555529669-e69e7aa0ba9a?auto=format&fit=crop&w=800&q=80",
    "nightlife": "https://images.unsplash.com/photo-1566737236500-c8ac43014a8b?auto=format&fit=crop&w=800&q=80",
    "viewpoint": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80",
}

HOTEL_TYPE_IMAGES = {
    "resort": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
    "boutique": "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?auto=format&fit=crop&w=800&q=80",
    "heritage": "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?auto=format&fit=crop&w=800&q=80",
    "hostel": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=800&q=80",
    "homestay": "https://images.unsplash.com/photo-1449844908441-8829872d2607?auto=format&fit=crop&w=800&q=80",
    "hotel": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
    "apartment": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80",
    "guesthouse": "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=800&q=80",
}

PACKAGE_THEME_IMAGES = {
    "adventure": "https://images.unsplash.com/photo-1551632811-561732d1e306?auto=format&fit=crop&w=800&q=80",
    "honeymoon": "https://images.unsplash.com/photo-1530789253388-582c481c54b0?auto=format&fit=crop&w=800&q=80",
    "pilgrimage": "https://images.unsplash.com/photo-1603569283847-aa295f0d016a?auto=format&fit=crop&w=800&q=80",
    "family": "https://images.unsplash.com/photo-1484712401471-05c7215830eb?auto=format&fit=crop&w=800&q=80",
    "heritage": "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=800&q=80",
    "wellness": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?auto=format&fit=crop&w=800&q=80",
    "wildlife": "https://images.unsplash.com/photo-1516426122078-c23e76319801?auto=format&fit=crop&w=800&q=80",
    "food_trail": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?auto=format&fit=crop&w=800&q=80",
}


def _get_image(etype: str, item: dict) -> str:
    """Get a contextually appropriate placeholder image URL."""
    if etype == "poi":
        cat = item.get("poi_category", "nature")
        return POI_CATEGORY_IMAGES.get(cat, POI_CATEGORY_IMAGES["nature"])
    elif etype == "hotel":
        prop = item.get("property_type", "hotel")
        return HOTEL_TYPE_IMAGES.get(prop, HOTEL_TYPE_IMAGES["hotel"])
    elif etype == "package":
        theme = item.get("theme", "adventure")
        return PACKAGE_THEME_IMAGES.get(theme, PACKAGE_THEME_IMAGES["adventure"])
    return "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=800&q=80"


def _candidate_to_item(candidate: dict, rank: int, profile: Optional[UserProfile], session: Optional[SessionProfile], query: str = "") -> RecommendationItem:
    """Convert a ranked candidate dict to a RecommendationItem schema."""
    item = candidate["item_data"]
    etype = candidate["entity_type"]
    eid = candidate["entity_id"]
    scores = candidate.get("scores", {})

    # Extract price
    price = None
    if etype == "hotel":
        # Get minimum room rate
        price = Price(amount=None, currency=item.get("base_currency"), display="Rates vary")
    elif etype == "poi":
        cost = item.get("entry_cost", "0.00")
        currency = item.get("currency", "INR")
        price = Price(
            amount=str(cost),
            currency=currency,
            display=f"₹{cost}" if currency == "INR" else f"{currency} {cost}"
        )
    elif etype == "package":
        amount = item.get("base_price", "0.00")
        currency = item.get("currency", "INR")
        price = Price(
            amount=str(amount),
            currency=currency,
            display=f"₹{amount}" if currency == "INR" else f"{currency} {amount}"
        )

    # Tags
    tags = []
    if etype == "poi":
        raw_tags = item.get("tags", "")
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()][:4]
    elif etype == "hotel":
        tags = [item.get("property_type", "hotel"), f"{item.get('star_rating', 3)} star"]
        if item.get("has_xr_scene"):
            tags.append("XR preview")
    elif etype == "package":
        tags = [item.get("theme", ""), item.get("tier", ""), item.get("difficulty", "")]
        tags = [t for t in tags if t]

    # Duration
    duration = None
    if etype == "poi":
        mins = item.get("typical_duration_minutes", 60)
        duration = f"{mins // 60}h {mins % 60}m" if mins >= 60 else f"{mins}m"
    elif etype == "package":
        days = item.get("duration_days", 1)
        nights = item.get("duration_nights", 0)
        duration = f"{days}D/{nights}N"

    # Rating
    rating = None
    if etype == "hotel":
        gs = item.get("guest_score")
        rating = float(gs) if gs else None
    elif etype == "poi":
        pop = item.get("popularity_score", 50)
        rating = round(float(pop) / 20.0, 1)  # Convert 0-100 to 0-5 scale

    # Build explanation
    reasons = generate_reasons(candidate, profile, session, query)
    why_this = generate_why_this(candidate, profile, session)
    why_now = generate_why_now(candidate, session)
    confidence = compute_confidence(candidate, profile, query)
    final_score = scores.get("final_score", 0.0)
    match_pct = compute_match_percentage(final_score)

    # Category
    category = None
    if etype == "poi":
        category = item.get("poi_category", "")
    elif etype == "hotel":
        category = item.get("property_type", "")
    elif etype == "package":
        category = item.get("theme", "")

    return RecommendationItem(
        entity_id=eid,
        entity_type=etype,
        rank=rank,
        title=item.get("name", "Unknown"),
        description=item.get("description", "")[:200] if item.get("description") else "",
        image=_get_image(etype, item),
        location=item.get("address_line", "") or f"{item.get('city_name', '')}, {item.get('country_name', '')}",
        city=item.get("city_name", ""),
        country=item.get("country_name", ""),
        category=category,
        tags=tags,
        price=price,
        rating=rating,
        star_rating=item.get("star_rating"),
        duration=duration,
        language=item.get("languages_offered", "").split(",")[0] if etype == "package" else None,
        semantic_score=round(scores.get("semantic_score", 0.0), 4),
        profile_score=round(scores.get("profile_score", 0.0), 4),
        behaviour_score=round(scores.get("behaviour_score", 0.0), 4),
        collaborative_score=round(scores.get("collaborative_score", 0.0), 4),
        diversity_score=round(scores.get("diversity_score", 0.0), 4),
        rating_score=round(scores.get("rating_score", 0.0), 4),
        popularity_score=round(scores.get("popularity_score", 0.0), 4),
        final_score=round(final_score, 4),
        match_percentage=match_pct,
        confidence=confidence,
        reasons=reasons,
        why_this=why_this,
        why_now=why_now,
        rank_change=None,  # Set by interaction service after reranking
        metadata={
            "has_xr_scene": bool(item.get("has_xr_scene", 0)),
            "city_id": item.get("city_id", ""),
            "carbon_kg": item.get("carbon_kg"),
            "value_score": item.get("value_score"),
        },
    )


def _build_profile_summary(profile: Optional[UserProfile]) -> Optional[ProfileSummary]:
    if not profile:
        return None
    dna = ProfileDNA(
        dimensions=[
            DNADimension(
                dimension=dim,
                score=round(score, 3),
                previous_score=None,
                change=0.0,
            )
            for dim, score in sorted(profile.dna.items(), key=lambda x: -x[1])
        ],
        confidence=round(profile.maturity_score, 3),
        profile_maturity=profile.maturity_class,
    )
    return ProfileSummary(
        user_id=profile.user_id,
        display_name=profile.display_name,
        locale=profile.locale,
        budget_band=profile.budget_band,
        travel_style=profile.travel_style,
        traveller_type=profile.traveller_type,
        segment=profile.segment,
        profile_maturity=profile.maturity_class,
        maturity_score=round(profile.maturity_score, 3),
        interaction_count=profile.interaction_count,
        dna=dna,
        category_affinities={k: round(v, 3) for k, v in profile.category_affinity.items()},
        preferred_languages=profile.preferred_languages,
        preferred_currency=profile.preferred_currency,
        max_daily_budget=profile.max_daily_budget,
        max_daily_budget_currency=profile.max_daily_budget_currency,
        pace=profile.pace,
    )


def _build_session_summary(session: Optional[SessionProfile]) -> Optional[SessionSummary]:
    if not session:
        return None
    return SessionSummary(
        session_id=session.session_id,
        user_id=session.user_id,
        current_query=session.current_query,
        current_constraints=session.current_constraints,
        recent_interactions=session.recent_interactions[:10],
        session_preferences={k: round(v, 3) for k, v in session.session_preferences.items()},
        ranking_changes=[],
    )


def search(request: SearchRequest) -> SearchResponse:
    """Full search pipeline."""
    t_start = time.perf_counter()

    # 1. Language detection
    detected_language = detect_language(request.query)

    # 2. Query understanding
    t_parse_start = time.perf_counter()
    constraints = extract_constraints(request.query, request.filters)
    intent = detect_intent(request.query, constraints)
    semantic_text = build_semantic_text(request.query, constraints)
    t_parse_end = time.perf_counter()

    # 3. Load session
    session = create_or_load_session(request.session_id, request.user_id)
    update_session_query(session, request.query, constraints.model_dump())

    # 4. Load user profile
    profile = None
    if request.user_id:
        profile = get_or_build_profile(request.user_id)

    # 5. Hybrid retrieval
    entity_types = constraints.entity_types or ["hotel", "poi", "package"]
    candidates, telemetry = build_candidate_pool(
        query=request.query,
        constraints=constraints,
        semantic_text=semantic_text,
        entity_types=entity_types,
        top_k=50,
    )
    telemetry.query_parse_ms = (t_parse_end - t_parse_start) * 1000

    # 6. Personalized reranking
    t_rerank_start = time.perf_counter()
    ranked = rank_candidates(candidates, profile, session, top_k=request.limit)
    t_rerank_end = time.perf_counter()
    telemetry.reranking_ms = (t_rerank_end - t_rerank_start) * 1000
    telemetry.final_count = len(ranked)

    # 7. Convert to response items
    items = [
        _candidate_to_item(c, c["rank"], profile, session, request.query)
        for c in ranked
    ]

    telemetry.total_ms = (time.perf_counter() - t_start) * 1000

    return SearchResponse(
        query=request.query,
        detected_language=detected_language,
        intent=intent,
        constraints=constraints,
        retrieval=telemetry,
        results=items,
        profile=_build_profile_summary(profile),
        session=_build_session_summary(session),
    )
