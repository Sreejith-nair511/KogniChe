# 3. Scope and Non-Scope

The MVP is constrained to what can be **built, tested, and demonstrated** within a 24-hour sprint. Features are classified by delivery tier.

## 3.1 In MVP — Implemented

| Feature | Description | Data Source |
|---------|-------------|-------------|
| Natural language query parsing | Language detection, intent classification, constraint extraction | Query text |
| Multilingual semantic retrieval | FAISS index, multilingual-mpnet-768d | `hotels`, `activities_poi`, `tour_packages` |
| Hard structured filtering | Budget, city, star rating, category, duration, language — enforced as SQL predicates | All catalogue tables |
| Hybrid retrieval pipeline | Semantic + structured → candidate fusion | Combined |
| User profile construction | Explicit preferences + interaction signals | `user_preferences`, `user_interactions` |
| Profile maturity model | cold_start → early → learning → mature | Interaction count |
| Cold-start handling | Semantic + preference + popularity weighting, no history required | `user_preferences`, catalogue |
| Personalized reranking | 7-signal weighted score (semantic, profile, behaviour, collaborative, rating, popularity, diversity) | All |
| MMR diversification | Maximal Marginal Relevance, configurable λ | Ranked candidates |
| Session engine | Per-session signal capture (like, save, dislike, click) | Runtime DB |
| Session-adaptive ranking | Session signals applied as additive score modifier | Session profile |
| Grounded explanations | Why This, Why Now, confidence band, match percentage | All signal sources |
| Recommendation DNA | Per-user dimension profile (Adventure, Culture, Nature, etc.) | `user_preferences`, interactions |
| Rank movement tracking | Previous rank vs new rank after interaction | Session + ranking |
| Offline evaluation | Precision@5/10, NDCG@5/10, Recall@10, MRR | `eval_queries`, `eval_relevance_labels` |
| Baseline comparison | Popularity, Semantic, Hybrid, NEXORA | Eval dataset |
| FastAPI backend | REST API, 8 endpoints | — |
| Next.js frontend | Connected to live backend, real data | — |

## 3.2 Planned but Not Implemented in MVP

| Feature | Reason deferred |
|---------|-----------------|
| Full collaborative filtering (matrix factorization) | Requires offline training job; lightweight SQL-based signal used instead |
| LLM review summarization | Latency risk; review sentiment available as `sentiment_hint` |
| Real-time ranking re-training | Requires persistent model update pipeline; batch profile rebuild used |
| A/B testing framework | Infrastructure overhead; out of 24h scope |

## 3.3 Explicitly Out of Scope

| Feature | Rationale |
|---------|-----------|
| Live booking / payment processing | No inventory or payment data in APS-04; separate business domain |
| Real airline inventory integration | Not in APS-04 dataset |
| XR/AR scene rendering | `has_xr_scene` field flagged in data; rendering pipeline not built |
| Production-scale distributed infrastructure | Kubernetes, load balancing — not required for demo |
| Reinforcement learning from human feedback | Requires production traffic feedback loop |
| Full autonomous trip planning | APS-09 territory — separate problem statement |

## 3.4 Why This Scope

The 24-hour constraint forces a clear priority order:

1. **Real data first** — APS-04 must be loaded, indexed, and queryable
2. **Retrieval before ranking** — Precision of candidates bounds everything downstream
3. **Cold-start before personalization** — 600 users have no history; the system must work for them
4. **Evaluation last but non-negotiable** — A recommendation system without measured quality is unverifiable

Everything in the "In MVP" column was implemented, verified, and demonstrated end-to-end.
