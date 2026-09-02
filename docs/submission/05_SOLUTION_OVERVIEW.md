# 5. Solution Overview

## 5.1 Core Premise

NEXORA separates the recommendation problem into two distinct challenges that most travel search systems conflate:

1. **What is eligible?** — Hard, non-negotiable constraints that define the feasible set
2. **What is best?** — Soft ranking across the feasible set using user intelligence

Conflating these leads to budget violations, location mismatches, and recommendations that technically match a query but are practically useless. NEXORA keeps them separate throughout the pipeline.

## 5.2 The Pipeline at a Glance

| Stage | What Happens | Method |
|-------|-------------|--------|
| Query Understanding | Parse language, intent, constraints | `langdetect` + deterministic rules |
| Hard Filtering | Enforce budget, city, star, duration, language | SQL predicates on APS-04 |
| Semantic Retrieval | Find nearest catalogue items to query embedding | FAISS + multilingual-mpnet |
| Candidate Fusion | Intersect semantic hits with eligible set | Set intersection |
| Profile Scoring | Score by user preferences + interaction history | Weighted signal model |
| Session Scoring | Apply recency-weighted session signals | In-memory session profile |
| Reranking | Combine all signals into final score | Configurable weighted sum |
| Diversification | Prevent duplicate categories/types | MMR (λ=0.7) |
| Explanation | Generate per-result grounded reasons | Signal-based text generation |
| Learning | Store interaction, update profile/session, re-rank | Runtime DB + cache invalidation |

## 5.3 What Makes This Different from Basic Retrieval

| Capability | Basic Search | NEXORA |
|-----------|-------------|--------|
| Budget enforcement | Soft penalty | Hard SQL filter |
| Personalization | None | Profile + session |
| Cold-start | Fails | Explicit prefs + popularity fallback |
| Multilingual | English only | 50+ languages via multilingual model |
| Explanation | None | Per-result grounded reasons |
| Session adaptation | None | Live signal accumulation |
| Diversity | None | MMR reranking |
| Evaluation | None | Precision@K, NDCG@K, MRR vs APS-04 labels |

## 5.4 Novelty

**Dynamic weight adjustment by profile maturity.** The ranker does not use static weights. A cold-start user gets semantic=0.55, behaviour=0.00. A mature user gets semantic=0.40, behaviour=0.15. The system knows when it can and cannot trust its own signals.

**Hard/soft boundary.** Most RS systems use soft constraints — a budget item gets penalized. NEXORA uses a two-stage architecture where hard constraints are resolved before ML scoring begins. This makes the filtering auditable and prevents constraint violations.

**Evidence-grounded explanations.** The explanation engine only generates reasons supported by actual data. If no behaviour evidence exists, it does not fabricate one. Confidence is computed from query clarity, semantic strength, and profile maturity — not asserted.

**Session-long temporal learning.** Within a session, interactions update a lightweight profile that has higher weight than long-term history. A user who came in looking for budget stays and then liked a heritage property will see their session intent shift reflected immediately — without requiring a new query.
