# 19. Risks and Fallbacks

| Risk | Impact | Probability | Mitigation | Fallback |
|------|--------|-------------|-----------|---------|
| **Embedding model download fails / slow** | Semantic retrieval unavailable | LOW (model pre-cached) | Cache model before sprint; `HF_HUB_DISABLE_SYMLINKS_WARNING=1` for Windows | Popularity-sorted catalogue. Same API contract. |
| **Vector index not built** | Semantic score = 0 for all candidates | LOW (FAISS index pre-built) | Run `generate_embeddings.py` before sprint starts | `build_candidate_pool()` falls back to popularity-ranked eligible items |
| **SQLite lock contention under concurrent requests** | 5xx errors under load | LOW (WAL mode enabled) | `PRAGMA journal_mode=WAL` allows concurrent reads | Backend handles single user demo; concurrent access not required for hackathon |
| **Cold-start user gets no results** | Empty results page | LOW (explicit prefs always present) | Profile engine uses `user_preferences` even with 0 interactions | Popularity fallback in candidate fusion if semantic candidates < 5 |
| **langdetect misidentifies language** | Wrong BCP-47 tag | MEDIUM (short queries) | Multilingual model handles wrong tag gracefully (still produces embedding) | Query is embedded as-is; semantic retrieval still works |
| **Constraint extraction fails on novel query** | No hard filters applied, all items eligible | LOW | Falls back to semantic-only with no filters → broader result set | User can add explicit `filters` object in API request |
| **Evaluation takes too long** | Demo can't show metrics | LOW (40 queries in ~2 min) | Limit to 20 queries: `?max_queries=20` | Show pre-computed `eval_results.json` |
| **Profile cache grows large** | Memory pressure | VERY LOW (1,200 users, lightweight JSON) | Cache TTL not implemented yet; manual invalidation on interaction | Delete `user_profile_cache` table rows; rebuild on demand |
| **Frontend build fails** | No working demo | LOW (build verified clean) | `pnpm run build` checked before submission | Serve API directly from FastAPI `/docs` for judging |
| **FAISS index file missing on server restart** | Load fails, fallback to popularity | LOW (file persists) | Index saved to `data/runtime/vector_index/` | Graceful degradation with popularity ranking + warning in health endpoint |
| **Multilingual constraint extraction incomplete** | Hindi/Tamil query missing city constraint | MEDIUM | Explicit `filters.city_id` in API | Semantic retrieval still returns relevant items across all cities |
| **APS-04 eval labels biased toward popularity** | NEXORA appears to underperform | Known limitation (documented) | Explain in Section 15 | Present MRR and per-user improvement metrics alongside aggregate NDCG |

## Graceful Degradation Strategy

NEXORA is designed with a degradation hierarchy. Each failure mode reduces functionality without breaking the system:

```
Full NEXORA
  ↓ (no FAISS index)
Popularity + hard filters + profile scoring
  ↓ (no profile data)
Popularity + hard filters only
  ↓ (no database)
HTTP 503 with descriptive error message
```

The health endpoint (`GET /health`) reports the status of each component. The frontend System view shows this status in real time.
