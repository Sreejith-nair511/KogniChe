# 10. Personalization and Reranking

## 10.1 User Profile Construction

The `UserProfile` object is built from three APS-04 sources, layered in order of specificity:

### Source 1 — Identity Fields (users table)
```
travel_style:    adventure | budget | luxury | comfort | slow | cultural | wellness
budget_band:     shoestring | value | mid | premium | luxury
traveller_type:  solo | couple | family | business | friends | senior | backpacker
locale:          BCP-47 language tag
home_city_id:    geographic anchor
segment:         heavy | light | cold_start
```

### Source 2 — Explicit Preferences (user_preferences table)
```
preferred_languages:      comma-sep BCP-47, most-preferred first
interests:                comma-sep category codes (e.g., adventure_trek, beach_quiet)
max_daily_budget:         TEXT decimal + currency pair
dietary_flags:            vegetarian | vegan | halal | jain | none
accessibility_needs:      step_free | hearing | vision | none
pace:                     relaxed | balanced | packed
```

### Source 3 — Interaction History (user_interactions + runtime_interactions)

Signal weights used for profile construction:

| Interaction Type | Weight |
|-----------------|--------|
| book | +1.00 |
| save | +0.80 |
| like | +0.60 |
| share | +0.40 |
| click | +0.25 |
| search | +0.10 |
| view | +0.05 |
| dismiss | −0.20 |
| dislike | −0.70 |

`implicit_rating` from `user_interactions` is used when present; otherwise the type weight is applied.

### Derived Signals

**category_affinity:** Weighted sum of signal scores, grouped by item category. Normalised to [−1, 1]. Augmented by interest keywords and travel_style.

**entity_type_affinity:** Normalised affinity per entity type (hotel, poi, package).

**liked/saved/disliked_entities:** Explicit feedback lists used directly in behaviour scoring.

## 10.2 Profile Maturity Model

| Class | Interaction Count | Behaviour Weight | Semantic Weight |
|-------|------------------|-----------------|----------------|
| cold_start | 0 | 0.00 | 0.55 |
| early | 1–4 | 0.05 | 0.48 |
| learning | 5–49 | 0.12 | 0.40 |
| mature | 50+ | 0.15 | 0.40 |

The maturity class determines which scoring weights are applied. A cold-start user gets a fundamentally different ranker configuration from a mature user — same pipeline, different parameters.

**Maturity score** is a continuous 0–1 value used for the DNA confidence display. It increases sub-linearly: fast gains early, diminishing returns at scale.

## 10.3 Personalized Reranker — Scoring Components

### Semantic Score
FAISS cosine similarity between query embedding and item embedding. Already computed during retrieval. Range: [−1, 1] (in practice 0.3–0.9 for relevant items).

### Profile Score
Computed per (user, candidate) pair. Components:
- Budget match: travel_style vs property_type/theme/cost
- Category affinity from interaction-derived signals
- Language preference match (packages)
- Traveller type alignment (family packages, solo adventures)
- Pace alignment (duration vs preferred pace)

Range: [0, 1]

### Behaviour Score
- If entity_id in liked_entities → 0.9
- If entity_id in saved_entities → 0.8
- If entity_id in disliked_entities → −0.5
- Otherwise: entity_type_affinity score × 0.6

### Collaborative Score
```sql
SELECT COUNT(DISTINCT i.user_id)
FROM user_interactions i
JOIN users u ON i.user_id = u.user_id
WHERE u.travel_style = user.travel_style
  AND u.budget_band = user.budget_band
  AND i.entity_id = candidate_id
  AND i.interaction_type IN ('like', 'save', 'book')
```
Normalised: count / 10, capped at 0.5. Disabled for cold-start users.

### Rating Score
- Hotels: `guest_score / 10` (0–10 scale → 0–1)
- POIs: `popularity_score / 100`
- Packages: tier proxy (standard=0.5, deluxe=0.7, premium=0.9)

### Session Score (additive)
From the session profile: `session_preferences["entity:id"]` plus type-level signals. Applied as additive modifier (not weighted component) so it can push items up without distorting the base ranking.

## 10.4 The Reranking Formula

```
final_score = 
    w_sem   × semantic_score
  + w_prof  × profile_score
  + w_beh   × behaviour_score
  + w_collab× collaborative_score
  + w_rating× rating_score
  + w_pop   × popularity_score
  + 0.15    × session_score
```

Hard penalty for disliked items: `final_score = min(final_score × 0.1, 0.05)`

All weights are in `.env` and can be tuned without code changes.

## 10.5 MMR Diversification

After scoring, the top-50 candidates enter MMR:

```python
while len(selected) < top_k:
    if not selected:
        best = max(remaining, key=lambda c: c.final_score)
    else:
        best = max(remaining, key=lambda c:
            λ × c.final_score
            - (1-λ) × similarity_to_selected(c, selected)
        )
    selected.append(best)
```

`similarity_to_selected` uses category and entity_type overlap. λ=0.7 means 70% relevance, 30% diversity. This prevents the top-10 from being 10 beach POIs even if they all score highly.

## 10.6 Same Query, Different User

This is a required property of the system. A verified example from testing:

- Query: `"beach adventure activities"`
- Cold-start user (no history): semantic-dominant ranking, popularity floor
- Heavy user with adventure history: behaviour score lifts trekking/adventure POIs, session signals from prior likes amplify the effect
- User who disliked beach POIs previously: beach items receive hard penalty, wildlife/nature alternatives surface

The ranking is not a list — it is a function of (query, user, session).
