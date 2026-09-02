# 11. Cold Start and Session Learning

## 11.1 Cold Start

### The Problem

600 of the 1,200 APS-04 users have **zero interaction history**. A recommendation system that depends on behavioural signals cannot serve them at all, or serves them incorrectly by treating empty history as neutral preference.

NEXORA treats cold-start as a first-class condition — not an edge case.

### Cold-Start User Profile

When `segment = 'cold_start'` and interaction count = 0, the profile contains:
- **Explicit preferences** from `user_preferences` (languages, interests, budget, pace, dietary, accessibility)
- **Identity signals** from `users` (travel_style, budget_band, traveller_type, locale)
- **No** behaviour scores, collaborative scores, or saved/liked lists

### Cold-Start Ranker Configuration

| Signal | Cold-Start Weight |
|--------|-----------------|
| Semantic (query match) | 0.55 |
| Profile (explicit prefs + identity) | 0.20 |
| Behaviour | 0.00 |
| Collaborative | 0.00 |
| Rating | 0.10 |
| Popularity | 0.08 |
| Diversity | 0.07 |

The system does not pretend to know preferences it has never observed. Confidence for cold-start users is capped at MEDIUM unless semantic score and profile score are both strong.

### Cold-Start Explanation

A cold-start user's Why This panel shows:
- Semantic match reasons (grounded in query similarity)
- Profile reasons (grounded in explicit preferences)
- Rating/popularity reasons
- No behaviour reasons (correctly omitted — they would be fabricated)

### Cold-Start to Warm — The Transition

After each interaction, profile maturity recalculates:

```
0 interactions → cold_start (semantic + profile dominant)
1–4 interactions → early (behaviour weight appears at 0.05)
5–49 interactions → learning (behaviour grows to 0.12)
50+ interactions → mature (full weighting)
```

The transition is automatic. No code change, no model retraining. The same pipeline adapts.

---

## 11.2 Session Learning

### Long-Term vs Short-Term Intent

A user's long-term profile reflects stable preferences accumulated over time. But a user's intent in a specific session can be different — and the system needs to respond to the current context, not just the historical record.

**Example:**
- Long-term profile: budget guesthouses, cultural travel, slow pace
- Current session: user searched "luxury resort Goa weekend", liked a premium boutique hotel
- The current session signals luxury intent — the long-term profile says budget

Without session learning, the ranking continues to surface budget properties. With session learning, the session signals temporarily override the long-term weight on the luxury dimension.

### Session Profile Structure

```
session_id: str
current_query: str
current_constraints: dict
session_preferences: dict  # entity-level + type-level signals
  "entity:htl_xxxxx": +0.80   # liked
  "entity:htl_yyyyy": -0.80   # disliked
  "type:hotel": +0.40          # aggregate type signal
recent_interactions: list (last 20)
liked_in_session: list
saved_in_session: list
disliked_in_session: list
```

### Signal Weights (Session)

| Interaction | Session Weight |
|-------------|---------------|
| like | +0.80 |
| book | +1.00 |
| save | +0.60 |
| share | +0.40 |
| click | +0.25 |
| view | +0.05 |
| dismiss | −0.30 |
| dislike | −0.80 |

Session weights are slightly higher than long-term weights to ensure recency has greater influence.

### How Session Signals Affect Ranking

Session score is an **additive modifier** applied after the weighted combination:

```python
final = (weighted_sum_of_signals) + 0.15 × session_score
```

The 0.15 multiplier ensures session signals can meaningfully shift rankings (±15 percentage points on the final score) without overriding the base relevance entirely.

A like on a heritage hotel raises all heritage hotels' session scores. A dislike on a beach POI removes beach POIs from the top of the ranking — immediately, without a new search query.

### Persistence

Session state is stored in `nexora_runtime.db`. Sessions survive page refreshes. A user who returns within the same session finds their interaction signals intact.
