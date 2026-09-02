"""
User Profile Engine.
Builds rich user profiles from APS-04 explicit preferences + interaction history.
Profiles are cached in the runtime DB and invalidated on new interactions.
"""
import json
import logging
from typing import Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from app.core.config import settings
from app.database.connection import get_source_db, get_runtime_db

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    user_id: str
    display_name: str = ""
    locale: str = "en-IN"
    budget_band: str = "mid"
    travel_style: str = "comfort"
    traveller_type: str = "solo"
    segment: str = "cold_start"
    home_city_id: Optional[str] = None
    home_currency: str = "INR"

    # Explicit preferences (from user_preferences table)
    preferred_languages: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    dietary_flags: Optional[str] = None
    accessibility_needs: Optional[str] = None
    preferred_currency: str = "INR"
    max_daily_budget: Optional[str] = None
    max_daily_budget_currency: Optional[str] = None
    pace: str = "balanced"

    # Behavioural signals (derived from interactions)
    category_affinity: dict[str, float] = field(default_factory=dict)
    city_affinity: dict[str, float] = field(default_factory=dict)
    entity_type_affinity: dict[str, float] = field(default_factory=dict)
    theme_affinity: dict[str, float] = field(default_factory=dict)
    liked_entities: list[str] = field(default_factory=list)
    saved_entities: list[str] = field(default_factory=list)
    disliked_entities: list[str] = field(default_factory=list)

    # Profile maturity
    maturity_score: float = 0.0
    maturity_class: str = "cold_start"
    interaction_count: int = 0
    recent_interaction_count: int = 0  # last 30 days

    # DNA dimensions (derived)
    dna: dict[str, float] = field(default_factory=dict)


SIGNAL_WEIGHTS = {
    "view": 0.05,
    "click": 0.25,
    "like": 0.60,
    "save": 0.80,
    "book": 1.00,
    "share": 0.40,
    "dismiss": -0.20,
    "dislike": -0.70,
    "search": 0.10,
}


def _compute_maturity(count: int) -> tuple[float, str]:
    """Return (maturity_score 0-1, maturity_class)."""
    if count == 0:
        return 0.0, "cold_start"
    elif count < settings.MATURITY_EARLY:
        return count / settings.MATURITY_EARLY * 0.2, "early"
    elif count < settings.MATURITY_LEARNING:
        score = 0.2 + (count - settings.MATURITY_EARLY) / (settings.MATURITY_LEARNING - settings.MATURITY_EARLY) * 0.4
        return score, "learning"
    elif count < settings.MATURITY_MATURE:
        score = 0.6 + (count - settings.MATURITY_LEARNING) / (settings.MATURITY_MATURE - settings.MATURITY_LEARNING) * 0.3
        return score, "learning"
    else:
        score = min(0.9 + (count - settings.MATURITY_MATURE) / 200 * 0.1, 1.0)
        return score, "mature"


def build_profile(user_id: str) -> Optional[UserProfile]:
    """
    Build a full UserProfile for a user from source + runtime data.
    Returns None if user does not exist.
    """
    try:
        with get_source_db() as src:
            cur = src.cursor()

            # Base user data
            cur.execute("""
                SELECT u.*, p.preferred_languages, p.interests, p.dietary_flags,
                       p.accessibility_needs, p.preferred_currency,
                       p.max_daily_budget, p.max_daily_budget_currency, p.pace, p.guide_language
                FROM users u
                LEFT JOIN user_preferences p ON p.user_id = u.user_id
                WHERE u.user_id = ?
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                return None

            profile = UserProfile(
                user_id=user_id,
                display_name=row["display_name"],
                locale=row["locale"],
                budget_band=row["budget_band"],
                travel_style=row["travel_style"],
                traveller_type=row["traveller_type"],
                segment=row["segment"],
                home_city_id=row["home_city_id"],
                home_currency=row["home_currency"],
                preferred_languages=[l.strip() for l in (row["preferred_languages"] or "en-IN").split(",") if l.strip()],
                interests=[i.strip() for i in (row["interests"] or "").split(",") if i.strip()],
                dietary_flags=row["dietary_flags"],
                accessibility_needs=row["accessibility_needs"],
                preferred_currency=row["preferred_currency"] or "INR",
                max_daily_budget=row["max_daily_budget"],
                max_daily_budget_currency=row["max_daily_budget_currency"],
                pace=row["pace"] or "balanced",
            )

            # Historical interactions from source DB
            cur.execute("""
                SELECT entity_type, entity_id, interaction_type, implicit_rating,
                       occurred_at
                FROM user_interactions
                WHERE user_id = ?
                ORDER BY occurred_at DESC
            """, (user_id,))
            interactions = cur.fetchall()

    except Exception as e:
        logger.error(f"Error building profile for {user_id}: {e}")
        return None

    # Also load runtime interactions
    runtime_interactions = []
    try:
        with get_runtime_db() as rt:
            rt_cur = rt.cursor()
            rt_cur.execute("""
                SELECT entity_type, entity_id, interaction_type, occurred_at, 0.5 as implicit_rating
                FROM runtime_interactions
                WHERE user_id = ?
                ORDER BY occurred_at DESC
            """, (user_id,))
            runtime_interactions = rt_cur.fetchall()
    except Exception as e:
        logger.warning(f"Runtime interactions unavailable for {user_id}: {e}")

    all_interactions = list(interactions) + list(runtime_interactions)
    profile.interaction_count = len(all_interactions)
    profile.maturity_score, profile.maturity_class = _compute_maturity(profile.interaction_count)

    # Compute behavioural signals
    cat_scores: dict[str, float] = {}
    city_scores: dict[str, float] = {}
    etype_scores: dict[str, float] = {}

    for interaction in all_interactions:
        itype = interaction["interaction_type"]
        weight = SIGNAL_WEIGHTS.get(itype, 0.0)
        etype = interaction["entity_type"]
        eid = interaction["entity_id"]

        # Use implicit_rating if present and positive, else use signal weight
        rating = interaction["implicit_rating"]
        if rating is not None:
            effective = float(rating) * abs(weight) * (1 if weight >= 0 else -1)
        else:
            effective = weight

        etype_scores[etype] = etype_scores.get(etype, 0.0) + effective

        if itype == "like":
            if eid not in profile.liked_entities:
                profile.liked_entities.append(eid)
        elif itype == "save":
            if eid not in profile.saved_entities:
                profile.saved_entities.append(eid)
        elif itype in ("dislike", "dismiss"):
            if eid not in profile.disliked_entities:
                profile.disliked_entities.append(eid)

    # Normalise entity type affinity
    if etype_scores:
        max_score = max(abs(v) for v in etype_scores.values()) or 1.0
        profile.entity_type_affinity = {k: v / max_score for k, v in etype_scores.items()}

    # Build category affinity from interests (explicit) + behavioural (implicit)
    for interest in profile.interests:
        # Interests are category codes like "adventure_trek", "beach_quiet"
        top_level = interest.split("_")[0] if "_" in interest else interest
        cat_scores[top_level] = cat_scores.get(top_level, 0.0) + 0.5

    # Map travel_style to category affinities
    style_cat_map = {
        "adventure": ["adventure", "nature"],
        "cultural": ["heritage", "museum", "religious"],
        "wellness": ["wellness"],
        "budget": [],
        "luxury": [],
        "slow": [],
        "comfort": [],
    }
    for cat in style_cat_map.get(profile.travel_style, []):
        cat_scores[cat] = cat_scores.get(cat, 0.0) + 0.3

    if cat_scores:
        max_score = max(abs(v) for v in cat_scores.values()) or 1.0
        profile.category_affinity = {k: min(v / max_score, 1.0) for k, v in cat_scores.items()}

    # DNA dimensions
    profile.dna = _build_dna(profile)

    return profile


def _build_dna(profile: UserProfile) -> dict[str, float]:
    """Build profile DNA dimensions from user data."""
    dna = {
        "Adventure": 0.0,
        "Culture": 0.0,
        "Nature": 0.0,
        "Relaxation": 0.0,
        "Food": 0.0,
        "Luxury": 0.0,
        "Budget": 0.0,
        "Family": 0.0,
    }

    # From travel_style
    style_map = {
        "adventure": {"Adventure": 0.8},
        "cultural": {"Culture": 0.8},
        "wellness": {"Relaxation": 0.8, "Nature": 0.3},
        "budget": {"Budget": 0.8},
        "luxury": {"Luxury": 0.8},
        "slow": {"Relaxation": 0.7, "Culture": 0.3},
        "comfort": {"Relaxation": 0.5},
    }
    for dim, val in style_map.get(profile.travel_style, {}).items():
        dna[dim] = max(dna[dim], val)

    # From budget_band
    band_map = {
        "shoestring": {"Budget": 0.9},
        "value": {"Budget": 0.6},
        "mid": {},
        "premium": {"Luxury": 0.5},
        "luxury": {"Luxury": 0.9},
    }
    for dim, val in band_map.get(profile.budget_band, {}).items():
        dna[dim] = max(dna[dim], val)

    # From traveller_type
    if profile.traveller_type == "family":
        dna["Family"] = max(dna["Family"], 0.8)

    # From category affinity
    cat_to_dna = {
        "adventure": "Adventure",
        "nature": "Nature",
        "heritage": "Culture",
        "museum": "Culture",
        "religious": "Culture",
        "beach": "Nature",
        "food": "Food",
        "wellness": "Relaxation",
    }
    for cat, dim in cat_to_dna.items():
        if cat in profile.category_affinity:
            dna[dim] = max(dna[dim], profile.category_affinity[cat])

    # From interests
    for interest in profile.interests:
        for cat, dim in cat_to_dna.items():
            if cat in interest.lower():
                dna[dim] = max(dna[dim], 0.6)

    return dna


def get_cached_profile(user_id: str) -> Optional[UserProfile]:
    """Load profile from cache if available."""
    try:
        with get_runtime_db() as rt:
            cur = rt.cursor()
            cur.execute(
                "SELECT profile_json FROM user_profile_cache WHERE user_id = ?",
                (user_id,)
            )
            row = cur.fetchone()
            if row:
                data = json.loads(row["profile_json"])
                return UserProfile(**data)
    except Exception as e:
        logger.debug(f"Cache miss for {user_id}: {e}")
    return None


def cache_profile(profile: UserProfile):
    """Store computed profile in runtime cache."""
    try:
        with get_runtime_db() as rt:
            rt.execute("""
                INSERT OR REPLACE INTO user_profile_cache
                    (user_id, profile_json, maturity_score, maturity_class, interaction_count, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                profile.user_id,
                json.dumps(asdict(profile)),
                profile.maturity_score,
                profile.maturity_class,
                profile.interaction_count,
            ))
    except Exception as e:
        logger.warning(f"Could not cache profile for {profile.user_id}: {e}")


def get_or_build_profile(user_id: str, force_rebuild: bool = False) -> Optional[UserProfile]:
    """Get profile from cache, or build and cache it."""
    if not force_rebuild:
        cached = get_cached_profile(user_id)
        if cached:
            return cached
    profile = build_profile(user_id)
    if profile:
        cache_profile(profile)
    return profile


def invalidate_profile_cache(user_id: str):
    """Force profile rebuild on next request."""
    try:
        with get_runtime_db() as rt:
            rt.execute("DELETE FROM user_profile_cache WHERE user_id = ?", (user_id,))
    except Exception as e:
        logger.warning(f"Could not invalidate cache for {user_id}: {e}")
