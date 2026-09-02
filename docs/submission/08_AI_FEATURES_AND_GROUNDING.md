# 8. AI Features and Grounding

## 8.1 Feature Inventory

| Feature | Input | Method | Output | Grounded In | Business Value |
|---------|-------|--------|--------|-------------|----------------|
| **Multilingual semantic retrieval** | Query string | `paraphrase-multilingual-mpnet-base-v2` + FAISS | Top-K similar items | Item descriptions, tags, city data | Serves 80%+ of Indian travellers in their native language |
| **Query understanding** | Raw query | Deterministic rule engine + `langdetect` | `QueryConstraints` + `QueryIntent` | APS-04 enum values, city names | Converts free text to structured search |
| **User profile construction** | `user_preferences` + `user_interactions` | Signal aggregation + DNA derivation | `UserProfile` with maturity class | APS-04 data only | Personalizes every downstream step |
| **Behaviour scoring** | Profile liked/saved/disliked entities | Set membership + entity_type_affinity | Per-candidate behaviour_score | Real APS-04 interaction history | Increases relevance for returning users |
| **Collaborative signal** | Similar users (style + band) | SQL group-by interaction count | collaborative_score | APS-04 `user_interactions` | Surfaces items popular with similar travellers |
| **Session learning** | Like, save, dislike, click events | Weighted signal accumulation | Session preference map | Runtime interactions (live session) | Adapts to current intent without new query |
| **Personalized reranking** | All signals | Weighted linear combination | final_score per candidate | All of the above | Produces a per-user ranking, not a catalogue ranking |
| **MMR diversification** | Scored candidates | Maximal Marginal Relevance | Diverse top-K | Category + entity type | Prevents monotonous result sets |
| **Grounded explanations** | Signals used in scoring | Evidence selection | `reasons[]`, `why_this`, `why_now` | Only signals with supporting data | Builds user trust, explains the system |
| **Confidence estimation** | Semantic score + maturity + query clarity | Heuristic function | HIGH / MEDIUM / LOW | Actual signal strength | Communicates reliability per result |

## 8.2 The Grounding Principle

**NEXORA does not generate recommendations.** It retrieves, ranks, and explains them.

Every recommendation must pass through:

1. **Hard eligibility gate** — the item exists in APS-04, is `status=active`, and satisfies all hard constraints. An item that fails this gate is never shown.

2. **Signal grounding** — every component of the final score is computed from actual data:
   - `semantic_score` — from FAISS cosine similarity against the actual item embedding
   - `profile_score` — from the user's `user_preferences` and `user_interactions` rows
   - `behaviour_score` — from actual like/save/dislike records
   - `collaborative_score` — from other users' actual interaction records
   - `rating_score` — from `guest_score`, `popularity_score`, or `tier` fields
   - `session_score` — from interactions recorded in this session

3. **Explanation grounding** — the explanation engine only emits a reason if the supporting evidence exists. If behaviour evidence is absent (cold-start), the behaviour reason is omitted. If the profile shows no relevant category affinity, the profile reason is not generated.

## 8.3 What NEXORA Does Not Do

| Claim | Status |
|-------|--------|
| "Generate" recommendations using an LLM | ✗ Not done. Items come from APS-04. |
| Fabricate review summaries | ✗ Not done. `sentiment_hint` is used as signal only. |
| Pretend to know a cold-start user's preferences | ✗ Not done. Cold-start users get semantic + popularity + explicit prefs only. |
| Claim a calibrated probability score | ✗ Not done. `confidence` is a heuristic band, clearly labelled as such. |
| Return items outside hard constraints | ✗ Not done. Hard filters are SQL predicates, not soft scores. |

## 8.4 The Cold-Start Contract

For a user with zero interactions, the system makes the following explicit guarantees:

- All results satisfy hard constraints
- All results are semantically relevant to the query
- All results use explicit preferences from `user_preferences` for profile scoring
- Popularity and rating signals provide a quality floor
- No fabricated behaviour evidence is shown in explanations

The system states this transparently: maturity class = `cold_start`, confidence = `MEDIUM`, no behaviour reasons in the Why This panel.
