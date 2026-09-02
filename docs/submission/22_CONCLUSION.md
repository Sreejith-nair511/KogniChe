# 22. Conclusion

## What NEXORA Is

NEXORA is a recommendation engine that treats retrieval and ranking as two distinct, non-negotiable problems — and solves both.

Retrieval defines what is possible: items that satisfy hard constraints, exist in the catalogue, and are semantically related to the user's intent. Ranking determines what is best: a per-user ordering that incorporates explicit preferences, interaction history, session behaviour, collaborative signals, and quality evidence — explained, confidence-rated, and continuously updated.

This distinction matters. A system that conflates retrieval and ranking either violates constraints or fails to personalize. NEXORA does neither.

## What It Delivers

| Capability | Evidence |
|-----------|----------|
| Real data | 28,630 rows, 15 APS-04 tables, zero fabrication |
| Real retrieval | FAISS index, 1,260 vectors, multilingual-mpnet |
| Real personalization | Per-user profiles from APS-04 preferences + interactions |
| Real session learning | Interactions change rankings in the same API response |
| Real multilingual | Hindi query returns correct hotels; `detected_language: hi` |
| Real evaluation | NDCG@10 computed against 3,600 graded APS-04 labels |
| Real explanations | Reasons grounded in signals; omitted when evidence is absent |
| Real cold-start | 600 zero-history users served correctly via preference fallback |

## The Core Architecture, Summarised

```
UNDERSTAND   →   query language + intent + hard constraints
RETRIEVE     →   semantic FAISS ∩ SQL hard filter = eligible candidates
PERSONALIZE  →   user profile (explicit + behavioural) + session signals
RERANK       →   7-signal weighted score + MMR diversity
EXPLAIN      →   grounded reasons per result, grounded only in evidence
LEARN        →   interaction → profile update → re-rank → rank_changes[]
```

Each stage produces a measurable output. Each output is traceable to a data source. The `/recommendation/{id}/trace` endpoint makes the scoring fully auditable.

## What Makes This Worth Building

The 600 cold-start users in APS-04 have preferences but no history. The Tamil and Malayalam queries in the evaluation set have meaning but no English equivalent. The user who liked two heritage properties despite searching for budget accommodation has a current intent that differs from their long-term profile.

These are not edge cases. They are the majority of real travellers — new users, non-English speakers, users whose context changes. A popularity ranker serves none of them well. A pure semantic ranker serves only those who phrase queries in catalogue-adjacent English.

NEXORA was built to serve the rest.

---

*NEXORA — Adaptive Recommendation Intelligence*
*APS-04 · Kognivera Hackathon 2026*

> *Search tells you what exists.*
> *NEXORA learns what belongs to you.*
