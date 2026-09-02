# Dataset Audit — APS-04
**Generated from actual database queries against APS-04.db**

## Source
- File: `data/source/Recommendations/data/APS-04.db`
- Total rows: 28,630 across 15 tables
- Content: Fully synthetic travel data (no real people)

## Table Row Counts

| Table | Rows | Purpose |
|-------|------|---------|
| `users` | 1,200 | Traveller identities — 3 cohorts |
| `user_preferences` | 1,200 | Explicit preferences (one per user) |
| `user_interactions` | 12,339 | Interaction history |
| `hotels` | 300 | Hotel catalogue |
| `hotel_room_types` | 1,200 | Bookable units (4 per hotel) |
| `hotel_reviews` | 7,500 | Reviews (~25 per hotel, multilingual) |
| `activities_poi` | 900 | Points of interest |
| `tour_packages` | 60 | Curated tour packages |
| `cities` | 60 | Geographic anchor |
| `countries` | 30 | ISO country reference |
| `currencies` | 25 | Currency reference |
| `languages` | 26 | BCP-47 language reference |
| `categories` | 70 | Two-level taxonomy |
| `eval_queries` | 120 | Shared evaluation queries |
| `eval_relevance_labels` | 3,600 | Graded relevance (0–3) |

## User Cohorts

| Segment | Users | Interactions | Per User |
|---------|-------|-------------|----------|
| `cold_start` | 600 | 0 | 0.0 |
| `heavy` | 200 | 8,458 | 42.3 |
| `light` | 400 | 3,881 | 9.7 |

**Cold-start users: 600** — zero interactions, making cold-start fully testable.

## Evaluation Set

### Queries by Language
| Language | Count | Notes |
|----------|-------|-------|
| `en-IN` | 80 | English (Indian) |
| `hi` | 16 | Hindi |
| `ta` | 16 | Tamil |
| `ml` | 8 | Malayalam |

### Relevance Label Distribution
| Grade | Count | Meaning |
|-------|-------|---------|
| 3 | 257 | Ideal |
| 2 | 490 | Relevant |
| 1 | 892 | Marginal |
| 0 | 1,961 | Irrelevant |

### Entity Types in Labels
| Entity Type | Labels |
|-------------|--------|
| `hotel` | 2,160 |
| `poi` | 960 |
| `package` | 480 |

## Interaction Signal Types

| Type | Entity | Count |
|------|--------|-------|
| view | poi | 3,688 |
| click | poi | 1,699 |
| view | hotel | 1,230 |
| search | poi | 960 |
| like | poi | 769 |
| save | poi | 664 |
| click | hotel | 565 |
| dismiss | poi | 537 |
| book | poi | 325 |
| share | poi | 269 |
| *(others)* | | 2,671 |

## Hotel Review Languages
| Language | Reviews |
|----------|---------|
| en-IN | 3,109 |
| hi | 1,252 |
| ta | 752 |
| ml | 539 |
| bn | 491 |
| en-GB | 478 |
| mr | 442 |
| te | 437 |

## Position Bias
- `position_in_list` present in **7,525 / 12,339** interactions
- Available for offline debiasing in evaluation

## Key Foreign Key Relationships
- `user_interactions.user_id` → `users.user_id`
- `user_preferences.user_id` → `users.user_id` (1:1)
- `hotels.city_id` → `cities.city_id`
- `activities_poi.city_id` → `cities.city_id`
- `tour_packages.city_id` → `cities.city_id`
- `hotel_reviews.hotel_id` → `hotels.hotel_id`
- `hotel_room_types.hotel_id` → `hotels.hotel_id`
- `eval_relevance_labels.query_id` → `eval_queries.query_id`
- `eval_queries.persona_user_id` → `users.user_id`
- `cities.country_id` → `countries.country_id`

## Validation Results
- ✓ All user IDs carry `usr_` prefix
- ✓ All user_interaction FKs resolve
- ✓ All relevance grades in range 0–3
- ✓ Money fields stored as TEXT (compliant with Rule R3)
- ✓ 15 expected tables present
