"""
Query Understanding Service.
Parses natural language queries into structured constraints + intent.
Works without an LLM — uses deterministic keyword/pattern matching.
Falls back to pure semantic embedding when patterns don't match.
"""
import re
import logging
from typing import Optional
from langdetect import detect, LangDetectException

from app.schemas.recommendation import QueryConstraints, QueryIntent

logger = logging.getLogger(__name__)

# City name → city_id mapping (populated from DB on first use)
_city_lookup: dict[str, str] = {}
_city_name_lookup: dict[str, str] = {}  # city_id → name

# Known category keywords
HOTEL_KEYWORDS = {"hotel", "stay", "room", "homestay", "resort", "hostel", "boutique", "guesthouse", "heritage hotel", "apartment"}
POI_KEYWORDS = {"activity", "activities", "visit", "place", "attraction", "heritage", "museum", "temple", "beach", "nature", "adventure", "food", "shopping", "nightlife", "wellness", "wildlife", "viewpoint"}
PACKAGE_KEYWORDS = {"package", "tour", "trip", "itinerary", "holiday", "vacation", "travel package", "guided tour"}

THEME_KEYWORDS = {
    "adventure": ["adventure", "trek", "trekking", "zipline", "rafting", "hiking", "climbing"],
    "honeymoon": ["honeymoon", "romantic", "couple", "anniversary"],
    "pilgrimage": ["pilgrimage", "temple", "religious", "spiritual", "shrine", "mandir", "masjid"],
    "family": ["family", "kids", "children", "child", "parents"],
    "heritage": ["heritage", "historical", "history", "fort", "palace", "monument", "ancient"],
    "wellness": ["wellness", "spa", "yoga", "meditation", "ayurveda", "relaxation"],
    "wildlife": ["wildlife", "safari", "tiger", "jungle", "forest", "birds", "birding"],
    "food_trail": ["food", "cuisine", "culinary", "street food", "foodie", "taste"],
}

POI_CATEGORY_KEYWORDS = {
    "heritage": ["heritage", "fort", "palace", "historical", "ancient", "monument"],
    "nature": ["nature", "lake", "garden", "waterfall", "hill", "mountain"],
    "museum": ["museum", "gallery", "art"],
    "religious": ["temple", "church", "mosque", "shrine", "religious"],
    "adventure": ["adventure", "zipline", "trekking", "rafting"],
    "food": ["food", "restaurant", "street food", "market", "cuisine"],
    "shopping": ["shopping", "market", "bazaar", "mall"],
    "nightlife": ["nightlife", "bar", "club", "evening"],
    "beach": ["beach", "sea", "ocean", "coast"],
    "wildlife": ["wildlife", "safari", "zoo", "sanctuary"],
    "wellness": ["wellness", "spa", "yoga"],
    "viewpoint": ["viewpoint", "view", "lookout", "scenic"],
}

BUDGET_PATTERNS = [
    (r"under\s+(?:rs\.?\s*|₹\s*|inr\s*)?(\d[\d,]*)", "INR"),
    (r"below\s+(?:rs\.?\s*|₹\s*|inr\s*)?(\d[\d,]*)", "INR"),
    (r"(?:rs\.?\s*|₹\s*|inr\s*)?(\d[\d,]*)\s*(?:or less|max|maximum|budget)", "INR"),
    (r"budget.*?(?:rs\.?\s*|₹\s*|inr\s*)?(\d[\d,]*)", "INR"),
    (r"(\d[\d,]*)\s*(?:rs|inr|₹)", "INR"),
]

DURATION_PATTERNS = [
    r"(\d+)\s*(?:days?|nights?|day trip|night)",
    r"(?:for|in)\s+(\d+)\s*(?:days?|nights?)",
]

STAR_PATTERNS = [
    r"(\d)\s*star",
    r"(\d)\s*-\s*star",
]

TRAVEL_STYLE_MAP = {
    "budget": ["budget", "cheap", "affordable", "economical", "backpacker", "shoestring"],
    "comfort": ["comfort", "comfortable", "mid-range", "standard"],
    "luxury": ["luxury", "luxurious", "5-star", "premium", "deluxe", "opulent", "lavish"],
    "adventure": ["adventure", "adventurous", "extreme", "thrilling"],
    "slow": ["slow travel", "leisurely", "relaxed", "unhurried", "peaceful"],
    "cultural": ["culture", "cultural", "local", "authentic", "traditional"],
    "wellness": ["wellness", "spa", "relaxation", "retreat"],
}

INTENT_MAP = {
    "budget_stay": ["budget hotel", "cheap stay", "affordable room", "budget accommodation", "budget homestay"],
    "luxury_stay": ["luxury hotel", "5-star hotel", "premium stay", "luxury resort", "high-end hotel"],
    "family_stay": ["family hotel", "family room", "family-friendly", "kids friendly", "family accommodation"],
    "heritage_poi": ["heritage site", "historical place", "fort", "palace", "ancient", "heritage tour"],
    "nature_poi": ["nature", "garden", "lake", "waterfall", "wildlife", "national park"],
    "food_poi": ["food", "restaurant", "street food", "culinary", "foodie tour"],
    "adventure_package": ["adventure package", "trek", "adventure tour", "outdoor adventure"],
    "honeymoon_package": ["honeymoon", "romantic package", "couple tour", "anniversary trip"],
    "accessibility": ["accessible", "wheelchair", "step-free", "disabled", "mobility"],
    "pet_friendly": ["pet", "dog", "pet-friendly"],
}


def _load_city_lookup():
    """Lazy-load city name → ID mapping from source DB."""
    global _city_lookup, _city_name_lookup
    if _city_lookup:
        return
    try:
        from app.database.connection import get_source_db
        with get_source_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT city_id, name, state FROM cities WHERE status='active'")
            for row in cur.fetchall():
                name_lower = row["name"].lower()
                _city_lookup[name_lower] = row["city_id"]
                _city_name_lookup[row["city_id"]] = row["name"]
                if row["state"]:
                    _city_lookup[row["state"].lower()] = row["city_id"]
    except Exception as e:
        logger.warning(f"Could not load city lookup: {e}")


def detect_language(text: str) -> str:
    """Detect BCP-47 language tag from query text."""
    try:
        lang = detect(text)
        # Map langdetect codes to BCP-47 used in APS-04
        mapping = {
            "hi": "hi",
            "ta": "ta",
            "ml": "ml",
            "bn": "bn",
            "mr": "mr",
            "te": "te",
            "kn": "kn",
            "en": "en-IN",
        }
        return mapping.get(lang, "en-IN")
    except LangDetectException:
        return "en-IN"


def extract_constraints(query: str, filters: Optional[object] = None) -> QueryConstraints:
    """
    Extract structured constraints from a natural language query.
    Hard filters take precedence; text parsing supplements.
    """
    _load_city_lookup()
    q_lower = query.lower()
    constraints = QueryConstraints()

    # Apply explicit filters first (from API request)
    if filters:
        if hasattr(filters, "city_id") and filters.city_id:
            constraints.city_id = filters.city_id
        if hasattr(filters, "city_name") and filters.city_name:
            constraints.city = filters.city_name
            # Try to resolve city_id
            cid = _city_lookup.get(filters.city_name.lower())
            if cid:
                constraints.city_id = cid
        if hasattr(filters, "budget_max") and filters.budget_max:
            constraints.budget_max = filters.budget_max
            constraints.budget_currency = getattr(filters, "budget_currency", "INR") or "INR"
        if hasattr(filters, "star_min") and filters.star_min:
            constraints.star_min = filters.star_min
        if hasattr(filters, "duration_max_days") and filters.duration_max_days:
            constraints.duration_max_days = filters.duration_max_days
        if hasattr(filters, "entity_types") and filters.entity_types:
            constraints.entity_types = filters.entity_types
        if hasattr(filters, "themes") and filters.themes:
            constraints.themes = filters.themes
        if hasattr(filters, "poi_categories") and filters.poi_categories:
            constraints.poi_categories = filters.poi_categories
        if hasattr(filters, "language") and filters.language:
            constraints.language = filters.language
        if hasattr(filters, "accessibility") and filters.accessibility:
            constraints.accessibility = filters.accessibility

    # City name detection from query text
    if not constraints.city_id:
        for city_name, city_id in sorted(_city_lookup.items(), key=lambda x: -len(x[0])):
            if city_name in q_lower and len(city_name) > 3:
                constraints.city = city_name.title()
                constraints.city_id = city_id
                break

    # Budget extraction
    if not constraints.budget_max:
        for pattern, currency in BUDGET_PATTERNS:
            m = re.search(pattern, q_lower)
            if m:
                val_str = m.group(1).replace(",", "")
                try:
                    constraints.budget_max = float(val_str)
                    constraints.budget_currency = currency
                    break
                except ValueError:
                    pass

    # Duration extraction
    if not constraints.duration_max_days:
        for pattern in DURATION_PATTERNS:
            m = re.search(pattern, q_lower)
            if m:
                try:
                    constraints.duration_max_days = int(m.group(1))
                    break
                except ValueError:
                    pass

    # Star rating extraction
    if not constraints.star_min:
        for pattern in STAR_PATTERNS:
            m = re.search(pattern, q_lower)
            if m:
                try:
                    constraints.star_min = int(m.group(1))
                    break
                except ValueError:
                    pass

    # Entity type inference
    if not constraints.entity_types:
        detected = []
        if any(kw in q_lower for kw in HOTEL_KEYWORDS):
            detected.append("hotel")
        if any(kw in q_lower for kw in POI_KEYWORDS):
            detected.append("poi")
        if any(kw in q_lower for kw in PACKAGE_KEYWORDS):
            detected.append("package")
        if detected:
            constraints.entity_types = detected

    # Theme extraction
    if not constraints.themes:
        detected_themes = []
        for theme, keywords in THEME_KEYWORDS.items():
            if any(kw in q_lower for kw in keywords):
                detected_themes.append(theme)
        constraints.themes = detected_themes

    # POI category extraction
    if not constraints.poi_categories:
        detected_cats = []
        for cat, keywords in POI_CATEGORY_KEYWORDS.items():
            if any(kw in q_lower for kw in keywords):
                detected_cats.append(cat)
        constraints.poi_categories = detected_cats

    # Travel style extraction
    if not constraints.travel_style:
        for style, keywords in TRAVEL_STYLE_MAP.items():
            if any(kw in q_lower for kw in keywords):
                constraints.travel_style = style
                break

    return constraints


def detect_intent(query: str, constraints: QueryConstraints) -> QueryIntent:
    """Classify the high-level intent of the query."""
    q_lower = query.lower()

    # Check intent map
    for intent_type, phrases in INTENT_MAP.items():
        if any(phrase in q_lower for phrase in phrases):
            # Map intent to primary entity
            entity = "hotel"
            if "poi" in intent_type or intent_type in ("heritage_poi", "nature_poi", "food_poi", "accessibility"):
                entity = "poi"
            elif "package" in intent_type:
                entity = "package"
            return QueryIntent(
                intent_type=intent_type,
                primary_entity=entity,
                is_exploration=False,
            )

    # Infer from constraints
    if constraints.entity_types:
        primary = constraints.entity_types[0]
        return QueryIntent(
            intent_type=None,
            primary_entity=primary,
            is_exploration=False,
        )

    # Default: exploration across all types
    return QueryIntent(
        intent_type=None,
        primary_entity=None,
        is_exploration=True,
    )


def build_semantic_text(query: str, constraints: QueryConstraints) -> str:
    """
    Build enriched text for semantic embedding.
    Adds structured constraints as natural language context.
    """
    parts = [query]
    if constraints.city:
        parts.append(f"in {constraints.city}")
    if constraints.themes:
        parts.append(f"themes: {', '.join(constraints.themes)}")
    if constraints.poi_categories:
        parts.append(f"categories: {', '.join(constraints.poi_categories)}")
    if constraints.travel_style:
        parts.append(f"style: {constraints.travel_style}")
    return " ".join(parts)
