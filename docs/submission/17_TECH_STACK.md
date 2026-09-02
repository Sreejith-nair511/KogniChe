# 17. Technology Stack

## 17.1 Full Stack

| Layer | Technology | Version | Role | Why |
|-------|-----------|---------|------|-----|
| **Frontend** | Next.js | 16.3.3 | UI framework | Pre-existing design; React 19 + Turbopack |
| **Frontend** | TypeScript | 5.7.3 | Type safety | Full type coverage for API client |
| **Frontend** | Tailwind CSS v4 | 4.3.3 | Styling | Existing design system |
| **Frontend** | Lucide React | 1.16.0 | Icons | Existing component library |
| **Backend** | Python | 3.13.1 | Runtime | Mature ML ecosystem |
| **Backend** | FastAPI | 0.115.7 | API framework | Async, auto OpenAPI docs, Pydantic integration |
| **Backend** | Uvicorn | 0.34.0 | ASGI server | Production-grade async server |
| **Backend** | Pydantic v2 | 2.13.3 | Data validation | Type-safe request/response schemas |
| **Backend** | pydantic-settings | 2.8.0 | Configuration | `.env` driven configuration |
| **Database** | SQLite (APS-04.db) | — | Source dataset | Supplied as-is; no import step needed |
| **Database** | SQLite (runtime) | — | Sessions, interactions, cache | Zero-setup writeable store |
| **Vector Search** | FAISS (faiss-cpu) | 1.10.0 | ANN search | IndexFlatIP, AVX2, 1,260 vectors |
| **Embeddings** | sentence-transformers | 5.3.0 | Embedding framework | Pre-trained multilingual models |
| **Embedding Model** | paraphrase-multilingual-mpnet-base-v2 | — | Text embedding | 768d, 50+ languages, cosine similarity |
| **Language Detection** | langdetect | 1.0.9 | BCP-47 detection | Lightweight, deterministic |
| **HTTP Client** | httpx | 0.28.1 | Async HTTP | Used for health checks / future integrations |
| **Package Manager** | pnpm | 10.15.0 | Frontend packages | Fast, deterministic installs |

## 17.2 Architecture Decisions

### SQLite over PostgreSQL
APS-04 ships as SQLite. Using it read-only avoids an import step, eliminates a database server dependency, and makes the system fully self-contained. The API contract is identical — `DATABASE_URL` in `.env` can be changed to PostgreSQL + pgvector when scaling.

For production: switch `get_source_db()` to SQLAlchemy async with `asyncpg`, add `pgvector` extension, migrate FAISS to `pgvector` index. Zero business logic changes required.

### FAISS over pgvector
For 1,260 vectors, FAISS IndexFlatIP is faster and simpler than pgvector. IndexFlatIP performs exact search (no approximation error) in under 1ms. For 1M+ items, pgvector's HNSW index would be preferred.

### Multilingual-mpnet over other models
- `paraphrase-multilingual-MiniLM-L12-v2` (384d): faster but lower quality for Indian languages
- `multilingual-e5-large` (1024d): higher quality but 3× the inference time and memory
- `paraphrase-multilingual-mpnet-base-v2` (768d): best quality/latency tradeoff for the APS-04 language set

### No LLM Dependency
The system works fully without an LLM. Query understanding is deterministic. Explanations are signal-based. This eliminates latency, cost, and hallucination risk. An LLM can be added optionally for review summarization when needed.

## 17.3 Infrastructure

| Component | Development | Production Path |
|-----------|------------|----------------|
| Database | SQLite files | PostgreSQL + pgvector |
| Vector index | FAISS local file | pgvector HNSW or managed vector DB |
| Backend | Uvicorn single process | Uvicorn + Gunicorn workers, Docker container |
| Frontend | pnpm dev | pnpm build + static/SSR deployment |
| Model | HuggingFace local cache | Containerized model server |

A `docker-compose.yml` is included for single-command local setup.

## 17.4 Environment Configuration

All settings are in `.env` (not committed). Key variables:

```
DATABASE_URL=sqlite:///data/runtime/nexora_runtime.db
SOURCE_DB_PATH=data/source/Recommendations/data/APS-04.db
VECTOR_INDEX_DIR=data/runtime/vector_index
EMBEDDING_MODEL=paraphrase-multilingual-mpnet-base-v2
CORS_ORIGINS=http://localhost:3000
WEIGHT_SEMANTIC=0.40
WEIGHT_PROFILE=0.25
WEIGHT_BEHAVIOUR=0.15
SIGNAL_LIKE=0.60
SIGNAL_SAVE=0.80
SIGNAL_DISLIKE=-0.70
```

Ranking weights and signal weights are configurable without code changes.
