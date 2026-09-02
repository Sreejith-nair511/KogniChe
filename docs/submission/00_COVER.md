---
title: "NEXORA — Adaptive Recommendation Intelligence"
subtitle: "Design Submission · APS-04 · Kognivera Hackathon 2026"
---

<div style="page-break-after: always;"></div>

# NEXORA

## Adaptive Recommendation Intelligence

---

### Hyper-Personalized Recommendation Engine
### Hybrid Retrieval + Personalized Reranking + Session Learning

---

**Problem Statement** APS-04  
**Track** Travel & Tourism  
**Event** Kognivera Hackathon 2026  
**Dataset** APS-04 · data model v1.1.0-rc1 · 28,630 rows · 15 tables

---

> *Search tells you what exists.*
> *NEXORA learns what belongs to you.*

---

**Solution at a glance**

NEXORA is a full-stack personalized recommendation engine built on the APS-04 travel dataset. It combines semantic vector retrieval, deterministic hard filtering, behavioural user profiling, and session-adaptive reranking to surface the most relevant hotels, points of interest, and tour packages for each traveller — explained, ranked, and continuously refined.

---

| Component | Status |
|-----------|--------|
| Hybrid retrieval (semantic + structured) | **Implemented** |
| User profile engine (explicit + implicit) | **Implemented** |
| Session learning | **Implemented** |
| Personalized reranking (7-signal, MMR) | **Implemented** |
| Cold-start handling (600 test users) | **Implemented** |
| Multilingual queries (en-IN, hi, ta, ml) | **Implemented** |
| Grounded explanations (Why This / Why Now) | **Implemented** |
| Offline evaluation (Precision@K, NDCG@K, MRR) | **Implemented** |
| Next.js frontend connected to live backend | **Implemented** |

---

*Document compiled from source files in `docs/submission/`*
*Evaluation metrics computed from APS-04 ground truth labels*
