# 14. Dataset and Data Usage

## 14.1 APS-04 Dataset Summary

| Property | Value |
|----------|-------|
| Name | APS-04 |
| Version | data model v1.1.0-rc1 |
| Format | SQLite (`APS-04.db`) + CSV + DDL |
| Total rows | 28,630 |
| Total tables | 15 |
| Content | Fully synthetic travel data |

## 14.2 Table Reference

| Table | Rows | Used By | Key Fields for NEXORA |
|-------|------|---------|----------------------|
| `users` | 1,200 | Profile engine, evaluation | `user_id`, `travel_style`, `budget_band`, `traveller_type`, `segment`, `locale` |
| `user_preferences` | 1,200 | Profile engine | `interests`, `preferred_languages`, `max_daily_budget`, `accessibility_needs`, `pace`, `preferred_currency` |
| `user_interactions` | 12,339 | Profile engine, evaluation, session seed | `user_id`, `entity_id`, `entity_type`, `interaction_type`, `implicit_rating`, `position_in_list`, `session_id` |
| `hotels` | 300 | Catalogue, hard filter, embedding | `hotel_id`, `name`, `property_type`, `star_rating`, `guest_score`, `description`, `city_id`, `base_currency` |
| `hotel_room_types` | 1,200 | Budget hard filter | `hotel_id`, `base_rate`, `currency`, `max_occupancy`, `bed_config` |
| `hotel_reviews` | 7,500 | Rating signals, `sentiment_hint` | `hotel_id`, `rating`, `language`, `traveller_type`, `sentiment_hint` |
| `activities_poi` | 900 | Catalogue, hard filter, embedding | `poi_id`, `name`, `poi_category`, `entry_cost`, `popularity_score`, `tags`, `description`, `typical_duration_minutes` |
| `tour_packages` | 60 | Catalogue, hard filter, embedding | `package_id`, `name`, `theme`, `tier`, `base_price`, `duration_days`, `languages_offered`, `description` |
| `cities` | 60 | City constraint resolution, joins | `city_id`, `name`, `country_id`, `lat`, `lng`, `primary_language` |
| `countries` | 30 | Geographic joins | `country_id`, `name`, `default_currency` |
| `currencies` | 25 | Display, constraint validation | `iso4217`, `symbol`, `minor_unit_exponent` |
| `languages` | 26 | BCP-47 validation | `bcp47`, `english_name` |
| `categories` | 70 | Category label joins | `category_id`, `code`, `label`, `parent_category_id` |
| `eval_queries` | 120 | Evaluation engine | `query_id`, `query_text`, `language`, `intent`, `target_entity_type`, `city_id`, `persona_user_id`, `filters_json`, `k` |
| `eval_relevance_labels` | 3,600 | Evaluation ground truth | `query_id`, `entity_id`, `entity_type`, `grade` (0–3) |

## 14.3 How Each Dataset Supports NEXORA

### Catalogue Understanding
Hotels, POIs, and packages are embedded using their names, descriptions, categories, tags, and city/country. The FAISS index represents the semantic space of the entire active catalogue. 1,260 items indexed.

### User Profiling
`user_preferences` provides explicit signals without any interaction required — enabling cold-start personalization. `user_interactions` provides behavioural history for warm users. The `segment` field creates testable cohorts (heavy/light/cold_start).

### Interaction Learning
12,339 interactions with `interaction_type`, `implicit_rating`, and `position_in_list`. The `position_in_list` field is critical for debiasing offline evaluation (items shown at position 1 are interacted with more regardless of quality).

### Cold-Start Testing
600 users with exactly zero interactions. Their `user_preferences` rows exist. This enables measuring whether the explicit-preference-only fallback produces useful recommendations.

### Review Intelligence
7,500 reviews across 8 languages with `sentiment_hint` (−1 to +1 decimal). Used as quality signal in rating score. The `language` field enables language-aware display (future: LLM summarization per language).

### Evaluation
120 shared queries with multilingual coverage. 3,600 graded relevance labels (grade 0–3). The `filters_json` field per query contains hard constraints that correct systems must apply. The `persona_user_id` enables personalized evaluation.

## 14.4 Data Rules Observed

Per APS-04 data rules (R1–R8):

| Rule | Observed |
|------|---------|
| R1 Additive only | ✓ No original columns renamed or dropped. Runtime DB adds new tables only. |
| R2 IDs are opaque strings | ✓ IDs are passed through, never parsed or reissued |
| R3 Money is TEXT + currency pair | ✓ `CAST(base_rate AS REAL)` used only for comparison, never arithmetic |
| R4 ISO-8601 timestamps | ✓ `occurred_at` fields read as strings, not converted to floats |
| R5 Enums are lowercase snake_case | ✓ All enum values validated against `enums.json` categories |
| R6 Language is BCP-47 | ✓ `langdetect` output mapped to BCP-47 before any use |
| R7 Geography is WGS-84 | ✓ `lat`/`lng` fields passed through to response, not manipulated |
| R8 Nothing hard-deleted | ✓ `status = 'active'` filter used; no DELETE queries |

## 14.5 What the Data Does NOT Support

These limitations are explicitly acknowledged (not hidden):

- No real booking inventory or availability data → booking flow not implemented
- No airline/flight data in APS-04 tables → flight recommendation not attempted
- `position_in_list` is NULL for ~39% of interactions → full debiasing not possible
- Review text is not structured (pros/cons) → LLM summarization deferred
- Package pricing is for full package duration, not per-night → direct budget comparison to hotel room rates requires normalization (not implemented)
