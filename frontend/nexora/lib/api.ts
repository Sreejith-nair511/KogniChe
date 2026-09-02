/**
 * NEXORA typed API client.
 * Connects the existing Next.js UI to the FastAPI recommendation backend.
 * All types match the Pydantic schemas in backend/app/schemas/recommendation.py
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ── Types ──────────────────────────────────────────────────────────────────────

export interface SearchFilters {
  city_id?: string
  city_name?: string
  country?: string
  entity_types?: string[]
  budget_max?: number
  budget_currency?: string
  star_min?: number
  duration_max_days?: number
  themes?: string[]
  poi_categories?: string[]
  travel_style?: string
  language?: string
  accessibility?: string
}

export interface SearchRequest {
  user_id?: string
  session_id?: string
  query: string
  filters?: SearchFilters
  limit?: number
}

export interface ExplanationReason {
  type: string
  text: string
  strength: number
}

export interface WhyThis {
  query_match: number
  profile_match: number
  behaviour_match: number
  constraint_match: number
  rating_score: number
  diversity_score: number
  final_score: number
  evidence: string[]
}

export interface WhyNow {
  text: string
  triggered_by: string
}

export interface RankChange {
  previous_rank: number | null
  new_rank: number
  rank_delta: number
  direction: 'up' | 'down' | 'new' | 'unchanged'
}

export interface Price {
  amount: string | null
  currency: string | null
  display: string | null
}

export interface RecommendationItem {
  entity_id: string
  entity_type: string
  rank: number
  title: string
  description: string
  image: string | null
  location: string | null
  city: string | null
  country: string | null
  category: string | null
  tags: string[]
  price: Price | null
  rating: number | null
  star_rating: number | null
  duration: string | null
  language: string | null
  semantic_score: number
  profile_score: number
  behaviour_score: number
  collaborative_score: number
  diversity_score: number
  rating_score: number
  popularity_score: number
  final_score: number
  match_percentage: number
  confidence: 'HIGH' | 'MEDIUM' | 'LOW'
  reasons: ExplanationReason[]
  why_this: WhyThis | null
  why_now: WhyNow | null
  rank_change: RankChange | null
  metadata: Record<string, unknown>
}

export interface RetrievalTelemetry {
  catalogue_count: number
  eligible_count: number
  filtered_count: number
  semantic_candidate_count: number
  personalized_candidate_count: number
  final_count: number
  query_parse_ms: number
  embedding_ms: number
  retrieval_ms: number
  reranking_ms: number
  total_ms: number
}

export interface DNADimension {
  dimension: string
  score: number
  previous_score: number | null
  change: number
}

export interface ProfileDNA {
  dimensions: DNADimension[]
  confidence: number
  profile_maturity: string
}

export interface ProfileSummary {
  user_id: string
  display_name: string | null
  locale: string | null
  budget_band: string | null
  travel_style: string | null
  traveller_type: string | null
  segment: string | null
  profile_maturity: string
  maturity_score: number
  interaction_count: number
  dna: ProfileDNA | null
  category_affinities: Record<string, number>
  preferred_languages: string[]
  preferred_currency: string | null
  max_daily_budget: string | null
  max_daily_budget_currency: string | null
  pace: string | null
}

export interface SessionSummary {
  session_id: string
  user_id: string | null
  current_query: string | null
  current_constraints: Record<string, unknown>
  recent_interactions: Array<Record<string, unknown>>
  session_preferences: Record<string, number>
  ranking_changes: RankChange[]
}

export interface QueryIntent {
  intent_type: string | null
  is_exploration: boolean
  primary_entity: string | null
}

export interface QueryConstraints {
  city: string | null
  city_id: string | null
  country: string | null
  budget_max: number | null
  budget_currency: string
  duration_max_days: number | null
  themes: string[]
  poi_categories: string[]
  entity_types: string[]
  star_min: number | null
  language: string | null
  travel_style: string | null
  accessibility: string | null
}

export interface SearchResponse {
  query: string
  detected_language: string
  intent: QueryIntent
  constraints: QueryConstraints
  retrieval: RetrievalTelemetry
  results: RecommendationItem[]
  profile: ProfileSummary | null
  session: SessionSummary | null
}

export interface InteractionRequest {
  user_id: string
  session_id: string
  entity_id: string
  entity_type: string
  interaction_type: string
  position_in_list?: number
  query_text?: string
}

export interface ProfileUpdate {
  changed_dimensions: string[]
  dna_before: ProfileDNA | null
  dna_after: ProfileDNA | null
  maturity_change: string | null
}

export interface InteractionResponse {
  recorded: boolean
  interaction_id: string
  profile_update: ProfileUpdate | null
  session_update: SessionSummary | null
  rank_changes: RankChange[]
  recommendations: RecommendationItem[]
}

export interface EvalMetrics {
  precision_at_5: number
  precision_at_10: number
  ndcg_at_5: number
  ndcg_at_10: number
  recall_at_10: number
  mrr: number
  num_queries: number
}

export interface EvaluationSummary {
  number_of_queries: number
  precision_at_5: number
  precision_at_10: number
  ndcg_at_5: number
  ndcg_at_10: number
  recall_at_10: number
  mrr: number
}

export interface EvaluationComparison {
  popularity: EvalMetrics
  semantic: EvalMetrics
  hybrid: EvalMetrics
  nexora: EvalMetrics
}

export interface HealthResponse {
  status: string
  api: string
  database: string
  vector_index: string
  embedding_model: string
  dataset: string
  details: Record<string, unknown>
}

// ── API helpers ────────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

// ── API functions ──────────────────────────────────────────────────────────────

export async function search(req: SearchRequest): Promise<SearchResponse> {
  return apiFetch<SearchResponse>('/search', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function recordInteraction(req: InteractionRequest): Promise<InteractionResponse> {
  return apiFetch<InteractionResponse>('/interactions', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export async function getProfile(userId: string): Promise<ProfileSummary> {
  return apiFetch<ProfileSummary>(`/profile/${userId}`)
}

export async function getSession(sessionId: string): Promise<SessionSummary> {
  return apiFetch<SessionSummary>(`/session/${sessionId}`)
}

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health')
}

export async function getEvaluationSummary(maxQueries?: number): Promise<EvaluationSummary> {
  const qs = maxQueries ? `?max_queries=${maxQueries}` : ''
  return apiFetch<EvaluationSummary>(`/evaluation/summary${qs}`)
}

export async function getEvaluationComparison(maxQueries = 20): Promise<EvaluationComparison> {
  return apiFetch<EvaluationComparison>(`/evaluation/comparison?max_queries=${maxQueries}`)
}

export async function listUsers(segment?: string, limit = 20) {
  const qs = segment ? `?segment=${segment}&limit=${limit}` : `?limit=${limit}`
  return apiFetch<{ users: Array<Record<string, string>> }>(`/users${qs}`)
}

export async function listEvalQueries(limit = 20) {
  return apiFetch<{ total: number; queries: Array<Record<string, unknown>> }>(`/evaluation/queries?limit=${limit}`)
}
