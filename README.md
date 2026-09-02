# NEXORA — Hyper-Personalized Recommendation Engine

APS-04 · Kognivera Hackathon 2026 · Travel & Tourism

A fully functional recommendation system built on the APS-04 dataset, with a FastAPI backend, multilingual semantic retrieval, personalized reranking, session learning, and evaluation metrics — connected to the existing Next.js UI.

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 20+ with pnpm
- Internet access (first run downloads the embedding model ~1.1GB)

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env if needed — defaults work out of the box
```

### 3. Verify dataset
```bash
cd backend
python scripts/import_dataset.py
```
Expected output ends with `Dataset imported successfully`.

### 4. Generate embeddings
```bash
python scripts/generate_embeddings.py
```
Downloads `paraphrase-multilingual-mpnet-base-v2` on first run, then builds a FAISS index of 1,260 vectors (300 hotels + 900 POIs + 60 packages).

### 5. Start the backend
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Backend available at http://localhost:8000 — API docs at http://localhost:8000/docs

### 6. Install frontend dependencies
```bash
cd ../frontend/nexora
pnpm install
```

### 7. Start the frontend
```bash
pnpm run dev
```
Open http://localhost:3000

### 8. Run evaluation
```bash
cd ../../backend
python scripts/evaluate.py
```
Runs all 4 models (Popularity, Semantic, Hybrid, NEXORA) against real APS-04 eval queries. Results saved to `docs/eval_results.json`.

---

## Architecture

```
APS-04 Dataset (SQLite, read-only)
        │
        ▼
┌─────────────────────────────┐
│  FastAPI Backend            │
│  ├─ Query Understanding     │  Language detection, constraint parsing
│  ├─ Hard Filtering (SQL)    │  Budget, city, star rating, category
│  ├─ Semantic Retrieval      │  FAISS + multilingual-mpnet (768d)
│  ├─ User Profile Engine     │  Explicit prefs + interaction history
│  ├─ Session Engine          │  Short-term signals (like/save/dislike)
│  ├─ Personalized Reranker   │  7-component weighted score + MMR
│  ├─ Explanation Engine      │  Grounded reasons per result
│  └─ Evaluation Service      │  Precision@K, NDCG@K, MRR vs labels
└─────────────────────────────┘
        │  REST API
        ▼
┌─────────────────────────────┐
│  Next.js Frontend           │
│  Existing UI — unchanged    │
│  Connected via lib/api.ts   │
└─────────────────────────────┘
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/search` | Main recommendation search |
| POST | `/interactions` | Record like/save/dislike/click |
| GET | `/profile/{user_id}` | User profile + DNA |
| GET | `/session/{session_id}` | Session state |
| GET | `/health` | System health check |
| GET | `/evaluation/summary` | NEXORA metrics |
| GET | `/evaluation/comparison` | All 4 models compared |
| GET | `/evaluation/query/{id}` | Per-query results |
| GET | `/evaluation/failures` | Worst-performing queries |
| GET | `/recommendation/{id}/trace` | Score breakdown debug |
| GET | `/users` | List APS-04 users |

## Key Design Decisions

### Why SQLite not PostgreSQL?
The APS-04 dataset ships as SQLite. Using it directly (read-only) avoids a data import step and keeps the system self-contained. The API contract is identical — swap `DATABASE_URL` for PostgreSQL + pgvector at any time.

### Multilingual retrieval
`paraphrase-multilingual-mpnet-base-v2` supports 50+ languages natively. Queries in Hindi, Tamil, and Malayalam retrieve relevant results without translation. Confirmed by end-to-end test.

### Cold start
600 users in APS-04 have zero interaction history. For these users, ranking weights shift towards semantic relevance (0.55), explicit preferences (0.20), and popularity (0.08), with no collaborative component. As interactions accumulate, weights shift toward behaviour (profile maturity classes: cold_start → early → learning → mature).

### Hard filters
Budget, city, star rating, category, and language constraints are applied as SQL hard filters before any ML ranking. An item outside budget **never appears** regardless of its semantic score.

### Ranking components
```
final_score = 
  0.40 × semantic_score          (FAISS cosine similarity)
  0.25 × profile_score           (explicit prefs + travel style match)
  0.15 × behaviour_score         (interaction history)
  0.05 × collaborative_score     (similar users' interactions)
  0.05 × rating_score            (guest_score / popularity)
  0.03 × popularity_score
  + 0.15 × session_score         (additive session boost)
```
All weights are configurable via `.env`.

### Evaluation
Uses the actual 120 `eval_queries` and 3,600 `eval_relevance_labels` from APS-04 as ground truth. Metrics (Precision@K, NDCG@K, MRR, Recall@K) are computed honestly. Results are not manipulated.

## Files

```
backend/
  app/
    api/          search, interactions, profile, session, health, evaluation
    core/         config (all settings)
    database/     connection, runtime_schema
    embeddings/   FAISS engine
    evaluation/   metrics, evaluator (4 models)
    explanations/ explanation_engine (Why This, Why Now, confidence)
    personalization/ user_profile (build, cache, DNA)
    ranking/      personalized_ranker (MMR, dynamic weights)
    retrieval/    structured_filter (hard filters), hybrid_retriever
    schemas/      recommendation (all Pydantic models)
    services/     recommendation_service, interaction_service, query_understanding
    session/      session_engine
    main.py
  scripts/
    import_dataset.py    validate + init runtime DB
    generate_embeddings.py  build FAISS index
    evaluate.py          run all 4 models, report metrics
  requirements.txt

frontend/nexora/
  app/page.tsx    fully connected UI (real data, real interactions)
  lib/api.ts      typed API client
  .env.local      NEXT_PUBLIC_API_URL=http://localhost:8000

docs/
  DATASET_AUDIT.md
  eval_results.json   (generated after running scripts/evaluate.py)

data/
  source/Recommendations/data/APS-04.db   source dataset (read-only)
  runtime/nexora_runtime.db               sessions, runtime interactions
  runtime/vector_index/                   FAISS index + metadata
```

## Limitations & Notes

- Images are contextual Unsplash placeholders (no media URLs in APS-04)
- Position bias: `position_in_list` is present in 61% of interactions; full IPTW debiasing is documented as a future improvement
- Collaborative filtering uses a lightweight SQL approach; a full matrix factorization model would improve at scale
- LLM summarization of hotel reviews is not implemented; review data is used for rating signals only
- Evaluation metrics are computed offline; production CTR metrics require live traffic
