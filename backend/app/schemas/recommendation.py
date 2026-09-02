"""
Pydantic schemas for all API request/response objects.
Field names are adapted to the actual APS-04 dataset.
"""
from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel, Field


# ── Search request ─────────────────────────────────────────────────────────────

class SearchFilters(BaseModel):
    city_id: Optional[str] = None
    city_name: Optional[str] = None
    country: Optional[str] = None
    entity_types: Optional[list[str]] = None  # hotel | poi | package
    budget_max: Optional[float] = None
    budget_currency: Optional[str] = None
    star_min: Optional[int] = None
    duration_max_days: Optional[int] = None
    themes: Optional[list[str]] = None
    poi_categories: Optional[list[str]] = None
    travel_style: Optional[str] = None
    language: Optional[str] = None
    accessibility: Optional[str] = None


class SearchRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    query: str
    filters: Optional[SearchFilters] = None
    limit: int = 10


# ── Interaction request ─────────────────────────────────────────────────────────

class InteractionRequest(BaseModel):
    user_id: str
    session_id: str
    entity_id: str
    entity_type: str
    interaction_type: str  # like | save | dislike | click | view | dismiss | share
    position_in_list: Optional[int] = None
    query_text: Optional[str] = None


# ── Explanation ─────────────────────────────────────────────────────────────────

class ExplanationReason(BaseModel):
    type: str  # profile | constraint | behaviour | semantic | collaborative | rating
    text: str
    strength: float


class WhyThis(BaseModel):
    query_match: float
    profile_match: float
    behaviour_match: float
    constraint_match: float
    rating_score: float
    diversity_score: float
    final_score: float
    evidence: list[str]


class WhyNow(BaseModel):
    text: str
    triggered_by: str  # session_like | session_save | session_dislike | initial


# ── Rank change ─────────────────────────────────────────────────────────────────

class RankChange(BaseModel):
    previous_rank: Optional[int]
    new_rank: int
    rank_delta: int
    direction: str  # up | down | new | unchanged


# ── Price ───────────────────────────────────────────────────────────────────────

class Price(BaseModel):
    amount: Optional[str]
    currency: Optional[str]
    display: Optional[str]


# ── Recommendation item ─────────────────────────────────────────────────────────

class RecommendationItem(BaseModel):
    entity_id: str
    entity_type: str  # hotel | poi | package
    rank: int
    title: str
    description: str
    image: Optional[str] = None  # placeholder URL
    location: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = []
    price: Optional[Price] = None
    rating: Optional[float] = None
    star_rating: Optional[int] = None
    duration: Optional[str] = None
    language: Optional[str] = None

    # Scores
    semantic_score: float = 0.0
    profile_score: float = 0.0
    behaviour_score: float = 0.0
    collaborative_score: float = 0.0
    diversity_score: float = 0.0
    rating_score: float = 0.0
    popularity_score: float = 0.0
    final_score: float = 0.0

    # UX
    match_percentage: int = 0
    confidence: str = "MEDIUM"  # HIGH | MEDIUM | LOW
    reasons: list[ExplanationReason] = []
    why_this: Optional[WhyThis] = None
    why_now: Optional[WhyNow] = None
    rank_change: Optional[RankChange] = None

    # Metadata
    metadata: dict[str, Any] = {}


# ── Retrieval telemetry ─────────────────────────────────────────────────────────

class RetrievalTelemetry(BaseModel):
    catalogue_count: int
    eligible_count: int
    filtered_count: int
    semantic_candidate_count: int
    personalized_candidate_count: int
    final_count: int
    query_parse_ms: float = 0.0
    embedding_ms: float = 0.0
    retrieval_ms: float = 0.0
    reranking_ms: float = 0.0
    total_ms: float = 0.0


# ── Profile DNA ─────────────────────────────────────────────────────────────────

class DNADimension(BaseModel):
    dimension: str
    score: float
    previous_score: Optional[float] = None
    change: float = 0.0


class ProfileDNA(BaseModel):
    dimensions: list[DNADimension]
    confidence: float
    profile_maturity: str  # cold_start | early | learning | mature


# ── User profile summary ─────────────────────────────────────────────────────────

class ProfileSummary(BaseModel):
    user_id: str
    display_name: Optional[str]
    locale: Optional[str]
    budget_band: Optional[str]
    travel_style: Optional[str]
    traveller_type: Optional[str]
    segment: Optional[str]
    profile_maturity: str
    maturity_score: float
    interaction_count: int
    dna: Optional[ProfileDNA] = None
    category_affinities: dict[str, float] = {}
    preferred_languages: list[str] = []
    preferred_currency: Optional[str] = None
    max_daily_budget: Optional[str] = None
    max_daily_budget_currency: Optional[str] = None
    pace: Optional[str] = None


# ── Session summary ─────────────────────────────────────────────────────────────

class SessionSummary(BaseModel):
    session_id: str
    user_id: Optional[str]
    current_query: Optional[str]
    current_constraints: dict[str, Any] = {}
    recent_interactions: list[dict] = []
    session_preferences: dict[str, float] = {}
    ranking_changes: list[RankChange] = []


# ── Intent / constraints ─────────────────────────────────────────────────────────

class QueryConstraints(BaseModel):
    city: Optional[str] = None
    city_id: Optional[str] = None
    country: Optional[str] = None
    budget_max: Optional[float] = None
    budget_currency: Optional[str] = "INR"
    duration_max_days: Optional[int] = None
    themes: list[str] = []
    poi_categories: list[str] = []
    entity_types: list[str] = []
    star_min: Optional[int] = None
    language: Optional[str] = None
    travel_style: Optional[str] = None
    accessibility: Optional[str] = None


class QueryIntent(BaseModel):
    intent_type: Optional[str] = None  # budget_stay | luxury_stay | adventure_package etc.
    is_exploration: bool = False
    primary_entity: Optional[str] = None  # hotel | poi | package


# ── Search response ─────────────────────────────────────────────────────────────

class SearchResponse(BaseModel):
    query: str
    detected_language: str
    intent: QueryIntent
    constraints: QueryConstraints
    retrieval: RetrievalTelemetry
    results: list[RecommendationItem]
    profile: Optional[ProfileSummary] = None
    session: Optional[SessionSummary] = None


# ── Interaction response ─────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    changed_dimensions: list[str] = []
    dna_before: Optional[ProfileDNA] = None
    dna_after: Optional[ProfileDNA] = None
    maturity_change: Optional[str] = None


class InteractionResponse(BaseModel):
    recorded: bool
    interaction_id: str
    profile_update: Optional[ProfileUpdate] = None
    session_update: Optional[SessionSummary] = None
    rank_changes: list[RankChange] = []
    recommendations: list[RecommendationItem] = []


# ── Evaluation schemas ─────────────────────────────────────────────────────────

class EvalMetrics(BaseModel):
    precision_at_5: float
    precision_at_10: float
    ndcg_at_5: float
    ndcg_at_10: float
    recall_at_10: float
    mrr: float
    num_queries: int


class ModelMetrics(BaseModel):
    model_name: str
    metrics: EvalMetrics


class EvaluationSummary(BaseModel):
    number_of_queries: int
    precision_at_5: float
    precision_at_10: float
    ndcg_at_5: float
    ndcg_at_10: float
    recall_at_10: float
    mrr: float


class EvaluationComparison(BaseModel):
    popularity: EvalMetrics
    semantic: EvalMetrics
    hybrid: EvalMetrics
    nexora: EvalMetrics


class QueryEvalResult(BaseModel):
    query_id: str
    query_text: str
    language: str
    intent: str
    ground_truth: list[dict]
    retrieved_items: list[str]
    ranks: dict[str, int]
    relevance: dict[str, int]
    metrics: dict[str, float]


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    api: str
    database: str
    vector_index: str
    embedding_model: str
    dataset: str
    details: dict[str, Any] = {}
