# 20. MVP Acceptance Criteria

## Status Key
- ✅ Implemented and verified
- ⚠️ Implemented with known limitation
- 🔲 Not implemented (documented)

---

## Data Layer
- ✅ APS-04 dataset loaded (28,630 rows, 15 tables)
- ✅ All 15 tables accessible via read-only connection
- ✅ Dataset validation passes (IDs, FKs, enum values, money fields)
- ✅ Runtime database schema initialized
- ✅ 1,260 item embeddings generated (300 hotels + 900 POIs + 60 packages)
- ✅ FAISS index built and persisted

## Retrieval
- ✅ Semantic retrieval returns relevant results for English queries
- ✅ Semantic retrieval works for Hindi queries (verified: `परिवार के लिए होटल` → hotel results)
- ✅ Hard filters enforce budget constraint (items over budget excluded at SQL level)
- ✅ Hard filters enforce city constraint
- ✅ Hard filters enforce star rating constraint
- ✅ Hard filters enforce duration constraint (packages)
- ✅ Hybrid retrieval combines semantic + structured candidates
- ✅ Popularity fallback activates when semantic candidates < 5

## Personalization
- ✅ User profile built from `user_preferences` (explicit signals)
- ✅ User profile built from `user_interactions` (implicit signals)
- ✅ Profile maturity model: cold_start → early → learning → mature
- ✅ Cold-start users receive recommendations using explicit preferences only
- ✅ Profile cache with invalidation on interaction
- ✅ Category affinity derived from interactions
- ✅ DNA dimensions computed from profile data

## Ranking
- ✅ 7-signal personalized reranker implemented
- ✅ Dynamic weights by profile maturity
- ✅ Collaborative signal from similar users (SQL-based)
- ✅ MMR diversification (λ=0.7)
- ✅ Hard penalty for disliked items
- ✅ Same query + different users → different rankings (verified)

## Session Learning
- ✅ Session profile created/loaded per session_id
- ✅ Like, save, dislike, click signals stored and applied
- ✅ Session signals have higher weight than long-term history
- ✅ Session persistence across API calls
- ✅ Re-ranking after interaction (rank_changes[] returned)
- ✅ Profile rebuilt after interaction (maturity updates)

## Explainability
- ✅ `reasons[]` generated per result (up to 3 grounded reasons)
- ✅ `why_this` breakdown with component scores
- ✅ `why_now` generated from session signals
- ✅ Confidence band (HIGH / MEDIUM / LOW)
- ✅ Match percentage (50–99% display range)
- ✅ No fabricated reasons — evidence threshold enforced
- ✅ Cold-start users get no behaviour reasons (correct)

## Evaluation
- ✅ Precision@5 computed from APS-04 labels
- ✅ Precision@10 computed
- ✅ NDCG@5 computed
- ✅ NDCG@10 computed
- ✅ Recall@10 computed
- ✅ MRR computed
- ✅ Popularity baseline evaluated
- ✅ Semantic baseline evaluated
- ✅ NEXORA evaluated
- ✅ Real metrics reported (not fabricated)
- ⚠️ Position bias not corrected (documented limitation)
- ⚠️ Language-stratified metrics not yet separated

## API
- ✅ `POST /search` returns recommendations with full scoring
- ✅ `POST /interactions` records and updates ranking
- ✅ `GET /profile/{user_id}` returns profile + DNA
- ✅ `GET /session/{session_id}` returns session state
- ✅ `GET /health` returns full system status
- ✅ `GET /evaluation/summary` returns real metrics
- ✅ `GET /evaluation/comparison` returns 4-model comparison
- ✅ `GET /recommendation/{id}/trace` returns score breakdown
- ✅ Error handling: clean JSON errors, no stack traces

## Frontend
- ✅ `pnpm run build` passes with zero errors
- ✅ Search connected to `POST /search`
- ✅ Like/Save/Dislike connected to `POST /interactions`
- ✅ Why This drawer shows real scores and reasons
- ✅ Profile view shows real DNA from APS-04 user
- ✅ Evaluation view runs and displays real metrics
- ✅ System view shows live health status
- ✅ Rank changes displayed after interaction

## Demo
- ✅ Cold-start user search works end-to-end
- ✅ Like interaction records + profile updates + re-ranks
- ✅ Dislike removes item from top-5
- ✅ Hindi query handled correctly
- ✅ Full end-to-end test passes
