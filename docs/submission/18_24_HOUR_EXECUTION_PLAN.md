# 18. 24-Hour Execution Plan

## Pre-Sprint Preparation (Before 12:00 Day 1)
- [ ] APS-04 dataset inspected and understood
- [ ] Architecture agreed and documented
- [ ] Repository structure created
- [ ] `.env.example` ready
- [ ] HuggingFace model pre-cached

---

## Hour 0–1: Dataset Audit + Architecture Freeze

**Goal:** No surprises on Day 1.

- Run `scripts/import_dataset.py` — validate all 15 tables, all row counts, all FK constraints
- Inspect `eval_queries` + `eval_relevance_labels` — understand the ground truth
- Confirm the 3 cohorts: heavy (200), light (400), cold_start (600)
- Confirm `position_in_list` coverage for debiasing awareness
- Freeze architecture decisions: SQLite (not Postgres for speed), FAISS (not pgvector), no LLM

**Deliverables:** `docs/DATASET_AUDIT.md`

---

## Hour 1–3: Database + Data Layer

**Goal:** Source data accessible, runtime DB schema running.

- Implement `app/database/connection.py` — read-only APS-04.db + writeable runtime.db
- Implement `app/database/runtime_schema.py` — sessions, runtime_interactions, profile_cache
- Write and run `scripts/import_dataset.py`
- Verify: `GET /health` returns source_db=ok, runtime_db=ok

---

## Hour 3–6: Embeddings + Vector Index

**Goal:** Semantic retrieval working against real catalogue.

- Implement `app/embeddings/engine.py` — FAISS wrapper, multilingual model
- Implement embedding text builders (hotel, POI, package)
- Run `scripts/generate_embeddings.py` — 1,260 items embedded and indexed
- Verify: FAISS search for "beach adventure" returns relevant POIs

---

## Hour 6–8: Hard Filtering + Hybrid Retrieval

**Goal:** No constraint violations possible.

- Implement `app/retrieval/structured_filter.py` — SQL hard filters for all entity types
- Implement `app/retrieval/hybrid_retriever.py` — FAISS ∩ eligible set + fallback
- Write `app/services/query_understanding.py` — constraint extraction, language detection
- Verify: budget-constrained query returns zero out-of-budget results

---

## Hour 8–11: User Profiles + Interaction Modelling

**Goal:** Real APS-04 user data drives scoring.

- Implement `app/personalization/user_profile.py` — build, cache, invalidate
- Implement profile maturity model (cold_start → early → learning → mature)
- Implement DNA dimension derivation
- Verify: heavy user has category affinity; cold-start user has explicit prefs only

---

## Hour 11–14: Personalized Reranking + Cold Start

**Goal:** Ranking differs per user. Cold-start users get correct fallback.

- Implement `app/ranking/personalized_ranker.py` — 7-signal weighted score
- Implement dynamic weights by profile maturity
- Implement collaborative signal (SQL-based)
- Verify: same query, different users → different top-10 ordering
- Verify: cold-start user gets semantic-dominant ranking

---

## Hour 14–16: Session Learning + Diversity

**Goal:** Interactions change the ranking in real time.

- Implement `app/session/session_engine.py` — create, load, update, persist
- Implement `app/services/interaction_service.py` — record → update session → rebuild profile → re-rank → rank_changes[]
- Implement MMR diversification in ranker
- Verify: POST /interactions → ranking changes in response

---

## Hour 16–18: Explainability + Confidence

**Goal:** Every result has a grounded explanation.

- Implement `app/explanations/explanation_engine.py` — reasons[], why_this, why_now, confidence
- Verify: cold-start user gets no behaviour reasons; warm user gets behaviour reasons when supported
- Verify: disliked items not in top-5

---

## Hour 18–20: Evaluation + Baselines

**Goal:** Honest metrics against APS-04 ground truth.

- Implement `app/evaluation/metrics.py` — Precision@K, NDCG@K, Recall@K, MRR
- Implement `app/evaluation/evaluator.py` — 4 models: Popularity, Semantic, Hybrid, NEXORA
- Run `scripts/evaluate.py` — record real results
- Build evaluation API endpoints

---

## Hour 20–22: Frontend Integration + Testing

**Goal:** Next.js UI fully connected to live backend.

- Implement `frontend/nexora/lib/api.ts` — typed API client
- Update `frontend/nexora/app/page.tsx` — connect search, interactions, profile, evaluation, system
- Run `pnpm run build` — verify zero compilation errors
- Run end-to-end test: cold-start user → search → like → re-rank → Hindi query

---

## Hour 22–24: Demo Hardening + Documentation + PDF

**Goal:** Submission-ready.

- Fix any issues found during end-to-end testing
- Final `pnpm run build` + backend startup check
- Write `docs/submission/` source files
- Generate final PDF from markdown
- Verify PDF < 25MB
- Run `SUBMISSION_CHECKLIST.md`

---

## Reality vs Plan

| Phase | Planned | Actual Status |
|-------|---------|---------------|
| Dataset audit | Hour 0–1 | ✓ Complete |
| Database + schema | Hour 1–3 | ✓ Complete |
| Embeddings + FAISS | Hour 3–6 | ✓ Complete (1,260 vectors) |
| Hard filters + hybrid | Hour 6–8 | ✓ Complete |
| User profiles | Hour 8–11 | ✓ Complete |
| Reranking + cold-start | Hour 11–14 | ✓ Complete |
| Session learning | Hour 14–16 | ✓ Complete |
| Explainability | Hour 16–18 | ✓ Complete |
| Evaluation | Hour 18–20 | ✓ Complete (real metrics) |
| Frontend integration | Hour 20–22 | ✓ Complete (build passes) |
| Documentation | Hour 22–24 | ✓ In progress |
