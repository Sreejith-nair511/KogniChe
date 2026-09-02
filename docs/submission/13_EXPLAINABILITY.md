# 13. Explainability

## 13.1 Why Explainability Matters

A recommendation system that cannot explain its output is a black box. For travel — a high-stakes, high-spend decision — users need to understand why a recommendation appears. Judges and auditors need to verify that the system is doing what it claims.

NEXORA generates explanations at three levels:
1. **Why This** — why this specific item appeared in the results
2. **Why Now** — why this item has increased relevance in this session
3. **Confidence** — how certain the system is about this recommendation

## 13.2 Why This

The `why_this` object contains a full breakdown of the scoring evidence:

```json
{
  "query_match": 0.612,
  "profile_match": 0.734,
  "behaviour_match": 0.000,
  "constraint_match": 1.000,
  "rating_score": 0.890,
  "diversity_score": 0.700,
  "final_score": 0.723,
  "evidence": [
    "Your travel style: adventure",
    "Your budget preference: mid",
    "Your interests: adventure_trek, nature_lake",
    "Category: adventure",
    "Popularity score: 87/100"
  ]
}
```

Every field comes from computed signals on real data. `behaviour_match = 0.000` for a cold-start user is correct and honest — not fabricated.

## 13.3 Grounded Reasons (reasons[])

Up to 3 reasons are generated per result. Each has a type, text, and strength:

```json
"reasons": [
  {
    "type": "rating",
    "text": "Popular among travellers (score: 87/100)",
    "strength": 0.87
  },
  {
    "type": "constraint",
    "text": "Fits within your stated budget",
    "strength": 0.95
  },
  {
    "type": "profile",
    "text": "Aligns with your adventure travel style",
    "strength": 0.73
  }
]
```

### Reason Types and Their Evidence Sources

| Type | Generated When | Evidence Source |
|------|---------------|-----------------|
| `semantic` | `semantic_score >= 0.45` | FAISS similarity score |
| `profile` | `profile_score >= 0.55` | `user_preferences`, `travel_style`, category_affinity |
| `behaviour` | `behaviour_score >= 0.40` | liked/saved entities, entity_type_affinity |
| `session` | `abs(session_score) >= 0.20` | Session interactions in current session |
| `rating` | `rating_score >= 0.75` | `guest_score`, `popularity_score` |
| `constraint` | User has explicit budget/preference | Profile budget field |

**Critical rule:** If the evidence threshold is not met, the reason is not generated. The system never says "Matches your interests" without a `category_affinity > 0.4` signal to support it.

## 13.4 Why Now

Generated only when session activity justifies it:

```json
{
  "text": "Your recent likes this session included similar POIs, boosting this result.",
  "triggered_by": "session_like"
}
```

`triggered_by` values: `session_like`, `session_save`, `initial`

If no session activity is relevant, `why_now` is `null`. It is never fabricated.

## 13.5 Confidence Band

Three levels computed from actual signal strength:

| Level | Condition |
|-------|-----------|
| HIGH | final_score ≥ 0.70 AND semantic_score ≥ 0.55 AND maturity ≠ cold_start |
| MEDIUM | final_score ≥ 0.50 OR semantic_score ≥ 0.45 |
| LOW | Otherwise |

Cold-start users are capped at MEDIUM even if scores are high — because behavioural confirmation is absent.

## 13.6 Recommendation DNA

The profile DNA represents the user's inferred interest dimensions. These are derived from `travel_style`, `budget_band`, `traveller_type`, `interests`, and category affinity scores — never from fabricated signals.

| Dimension | Derived From |
|-----------|-------------|
| Adventure | `travel_style=adventure`, interests containing `adventure_*`, category affinity |
| Culture | `travel_style=cultural`, interests containing `heritage_*`, `museum_*` |
| Nature | interests containing `nature_*`, `beach_*`, category affinity |
| Relaxation | `travel_style=wellness` or `slow`, `pace=relaxed` |
| Food | interests containing `food_*` |
| Luxury | `budget_band=premium/luxury`, `travel_style=luxury` |
| Budget | `budget_band=shoestring/value`, `travel_style=budget` |
| Family | `traveller_type=family` |

The DNA confidence percentage = profile maturity score × 100. A 0-interaction cold-start user shows 0% confidence — not a fabricated number.

## 13.7 The Explainability Contract

NEXORA's explanation system makes this contract with users and judges:

1. **No reason is generated without supporting evidence**
2. **Confidence reflects actual signal quality, not a desired output**
3. **Absence of evidence is visible** — a cold-start profile shows no behaviour reasons, not placeholder text
4. **The debug trace endpoint** (`GET /recommendation/{id}/trace`) exposes the full scoring breakdown for any item in any query — available to judges at any time
