# 4. User Journey

## 4.1 Human Journey — Traveller Perspective

**Traveller:** Arjun, 34, adventure traveller, based in Bangalore. Budget: mid. Travelling solo. Locale: `en-IN`.

---

**Step 1 — Query**
Arjun opens NEXORA and types:
> "I want a 4-day adventure package in Coorg under ₹20,000"

He does not fill out any form. He does not select filters. The system understands him.

**Step 2 — Language & Intent**
The system detects `en-IN`, classifies intent as `adventure_package`, extracts constraints: `city=Coorg`, `budget_max=20000`, `duration_max_days=4`, `entity_type=package`.

**Step 3 — Hard Filter**
Only packages in Coorg, under ₹20,000, with duration ≤ 4 days pass the filter. A ₹35,000 luxury wellness package is not shown. It is not ranked last — it is removed entirely.

**Step 4 — Semantic Retrieval**
"Adventure package 4 days Coorg" is embedded using the multilingual model. The FAISS index returns the 50 nearest matching catalogue items.

**Step 5 — Profile Application**
Arjun has previous interactions — he viewed trekking POIs, liked two wildlife packages. His profile shows category affinity for `adventure` and `nature`. Profile score boosts adventure-category candidates.

**Step 6 — Personalized Reranking**
The 7-signal ranker produces a final score per candidate. A trekking package in Coorg scores highest — it matches his query, his profile, his budget, and his interaction history.

**Step 7 — Recommendations**
10 results appear. Each shows:
- Match percentage (e.g., 84%)
- Confidence band (HIGH)
- Price, duration, category
- Tags from the catalogue

**Step 8 — Why This**
Arjun taps "Why this?" on the top result. A panel opens:
> *"Matches your query for adventure packages · Fits your ₹20,000 budget · Similar to wildlife packages you liked · Popular among solo travellers"*

Every reason is grounded in actual signals — not generated text.

**Step 9 — Interaction**
Arjun likes the top result. The interaction is recorded. The session profile is updated. The ranker re-runs. The next-best result for a solo adventure traveller in this budget band moves up.

**Step 10 — Dislike**
Arjun dislikes a wellness retreat that appeared due to city overlap. It is penalized and removed from view.

**Step 11 — Session Learning**
By the third interaction, NEXORA has learned from this session: Arjun's current intent is trekking-heavy adventure, not general outdoor. The ranking shifts accordingly — without requiring a page refresh or new query.

**Step 12 — Profile Update**
The interaction is persisted. Arjun's profile maturity moves from `cold_start` toward `early`. His DNA dimensions for Adventure and Nature increase.

---

## 4.2 Technical Journey — System Perspective

```
User Input: "adventure package Coorg under 20000"
          │
          ▼
[Language Detection]
  langdetect → "en-IN"
          │
          ▼
[Query Understanding]
  intent = adventure_package
  city = Coorg → city_id lookup → cty_xxxxx
  budget_max = 20000 INR
  duration_max_days = 4
  entity_types = [package]
          │
          ▼
[Hard SQL Filter]
  SELECT * FROM tour_packages
  WHERE city_id = 'cty_xxxxx'
    AND CAST(base_price AS REAL) <= 20000
    AND duration_days <= 4
    AND status = 'active'
  → N eligible candidates
          │
          ▼
[Semantic Embedding]
  embed("adventure package 4 days Coorg")
  → 768-dim vector
          │
          ▼
[FAISS Search]
  top-150 nearest neighbours
  ↓ intersect with eligible set
  → 50 semantic candidates
          │
          ▼
[Profile Scoring]
  load user_preferences + user_interactions
  profile_maturity = early
  category_affinity: {adventure: 0.8, nature: 0.6}
  per-candidate profile_score
          │
          ▼
[Behaviour Scoring]
  liked_entities, saved_entities, disliked_entities
  → per-candidate behaviour_score
          │
          ▼
[Session Scoring]
  session_preferences = {type:package: +0.25}
  → per-candidate session_score
          │
          ▼
[Collaborative Signal]
  similar users (travel_style=adventure, budget_band=mid)
  who liked/saved/booked this entity
  → collaborative_score
          │
          ▼
[Weighted Combination]
  final = 0.40×sem + 0.25×profile + 0.15×behaviour
        + 0.05×collab + 0.05×rating + 0.03×pop
        + 0.15×session (additive)
          │
          ▼
[MMR Diversification]
  λ=0.7: balance relevance vs category diversity
  → top 10 diverse results
          │
          ▼
[Explanation Generation]
  per-result: reasons[], why_this{}, why_now, confidence
  grounded in actual signals only
          │
          ▼
[API Response]
  SearchResponse{results, profile, session, retrieval_telemetry}
          │
          ▼
[Next.js UI renders results]
          │
          ▼
[User interacts → POST /interactions]
  → store in runtime_interactions
  → update session_preferences
  → invalidate profile cache
  → rebuild profile
  → re-run ranking
  → return rank_changes[]
```
