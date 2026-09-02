# 21. Final Demo Flow

## Overview

**Duration:** 4–5 minutes  
**Goal:** Prove that NEXORA personalizes in real time — not just displays a beautiful UI with static data.

---

## Step 1 — System Health (30 seconds)

**Action:** Open `http://localhost:3000`. Navigate to **System** tab.

**Show:**
- All systems green: API ✓ · Database ✓ · Vector index ✓ · Embedding model ✓
- Dataset stats: 1,200 users · 1,260 vectors indexed · 120 eval queries

**Message:** "This is a live system running against the APS-04 dataset. Every number you see comes from real data."

---

## Step 2 — Cold Start User (30 seconds)

**Action:** Navigate to **Profile** tab. The profile shown is a real APS-04 heavy user.

**Show:**
- Profile maturity class
- Travel style, budget band, traveller type
- DNA dimensions

**Message:** "NEXORA loaded this profile from APS-04 `user_preferences` and `user_interactions`. The DNA dimensions are derived from actual interaction history — not hardcoded."

---

## Step 3 — Natural Language Search (45 seconds)

**Action:** Navigate to **Discover**. Type:
> `beach adventure activities`

**Show:**
- Processing animation (retrieval → reranking → explaining)
- 9 results appear — real APS-04 hotels, POIs, packages
- Retrieval telemetry at the bottom: `165 eligible · 50 semantic · 9 final`
- First result: Lighthouse Beach POI with 77% match, MEDIUM confidence

**Message:** "The query was parsed, a 768-dimensional vector was computed, 50 semantic candidates were retrieved from the FAISS index, hard filters were applied, and the result was personalized and ranked — all in under 200ms."

---

## Step 4 — Why This (30 seconds)

**Action:** Click **Why This?** on the first result.

**Show:**
- Reasons: "Popular among travellers (score: 100/100)" · "Fits within your stated budget" · "Aligns with your adventure travel style"
- Why This breakdown: query_match, profile_match, behaviour_match, rating_score
- Evidence list

**Message:** "Every reason is grounded in real data. The system won't say 'matches your interests' unless the category affinity signal is above threshold. No fabricated justifications."

---

## Step 5 — Like Interaction (45 seconds)

**Action:** Click the **heart (Like)** button on the first result (Lighthouse Beach).

**Show:**
- Processing (near-instant)
- Rank changes: items moving up/down
- Profile maturity updates from cold_start to `early`
- DNA dimensions update
- Why Now appears on relevant results: "Your recent likes boosted this result"

**Message:** "That like was sent to `POST /interactions`. The interaction was stored, the session profile updated, the user profile rebuilt, and the ranking re-ran. The order changed — for real, not animation."

---

## Step 6 — Dislike (30 seconds)

**Action:** Click the **thumbs down** on the second-ranked result.

**Show:**
- That item drops out of the top 5 (or receives a visible penalty)
- The item that was previously ranked 6 or 7 moves up

**Message:** "Disliked items receive a ×0.1 score penalty. They're not hidden — they're down-ranked. A judge can inspect the score breakdown via the trace endpoint."

---

## Step 7 — Multilingual Query (30 seconds)

**Action:** Type in the search box:
> `परिवार के लिए होटल`

**Show:**
- `detected_language: hi`
- Hotel results appear from APS-04
- Top result: Heritage Residency Inn (or similar)

**Message:** "Hindi query. No translation service. The multilingual model maps this to the same semantic space as 'family hotel' in English. Cross-lingual retrieval — working."

---

## Step 8 — Evaluation Dashboard (45 seconds)

**Action:** Navigate to **Evaluation** tab. Click **Run evaluation**.

**Show:**
- Progress (takes ~60–90 seconds for 30 queries)
- Or use pre-computed result:

| Model | NDCG@10 | MRR |
|-------|---------|-----|
| Popularity | 0.5403 | 0.6807 |
| Semantic | 0.1905 | 0.4392 |
| **NEXORA** | **0.2988** | **0.5687** |

**Message:** "These numbers are computed against 3,600 graded relevance labels in APS-04. NEXORA outperforms pure semantic retrieval by 57% on NDCG@10. Popularity scores higher on offline NDCG because the labels reflect catalogue quality — but NEXORA's value is per-user ranking, which offline aggregate metrics cannot fully capture."

---

## Step 9 — Debug Trace (30 seconds, optional for judges)

**Action:** In a browser tab, open:
```
http://localhost:8000/recommendation/{entity_id}/trace?query=beach+adventure&user_id={user_id}
```

**Show:**
```json
{
  "entity_id": "poi_5a4b1db1",
  "scores": {
    "semantic_score": 0.5629,
    "profile_score": 0.6500,
    "behaviour_score": 0.9000,
    "final_score": 0.7234
  },
  "weights": {
    "semantic": 0.48,
    "profile": 0.22,
    "behaviour": 0.05,
    ...
  }
}
```

**Message:** "Full scoring transparency. Every number has a source. No black box."

---

## What This Demo Proves

| Claim | Verified By |
|-------|------------|
| Real APS-04 data | Row counts in System view |
| Hard constraint enforcement | Budget filter test |
| Multilingual retrieval | Hindi query returning results |
| Personalized ranking | Profile DNA + maturity shown |
| Session learning | Rank changes after like |
| Grounded explanations | Why This panel showing real evidence |
| Honest evaluation | Real NDCG numbers, Popularity acknowledged as higher |
| Traceable scoring | `/recommendation/{id}/trace` endpoint |
