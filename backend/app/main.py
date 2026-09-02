"""
NEXORA FastAPI Backend — main application entry point.
Startup: validates DB, initialises runtime schema, loads vector index.
"""
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.runtime_schema import init_runtime_db
from app.database.connection import check_source_db
from app.embeddings.engine import load_index
from app.api import search, interactions, profile, session, health, evaluation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup validation: DB, runtime schema, vector index."""
    logger.info("=== NEXORA Backend starting ===")

    # 1. Check source DB
    src = check_source_db()
    if src["status"] != "ok":
        logger.error(f"Source DB unavailable: {src.get('error')}")
        logger.error("Run: scripts/import_dataset.py is not needed — source DB is already at data/source/Recommendations/data/APS-04.db")
    else:
        counts = src.get("counts", {})
        logger.info(f"Source DB: {counts.get('users', 0)} users | {counts.get('hotels', 0)} hotels | "
                    f"{counts.get('activities_poi', 0)} POIs | {counts.get('tour_packages', 0)} packages | "
                    f"{counts.get('user_interactions', 0)} interactions")

    # 2. Initialise runtime DB
    try:
        init_runtime_db()
        logger.info("Runtime DB schema initialised.")
    except Exception as e:
        logger.error(f"Runtime DB init failed: {e}")

    # 3. Load vector index
    loaded = load_index()
    if not loaded:
        logger.warning(
            "Vector index not found. Semantic retrieval will use popularity fallback. "
            "Run: python scripts/generate_embeddings.py"
        )
    else:
        logger.info("Vector index loaded successfully.")

    # 4. Preload city lookup for query understanding
    try:
        from app.services.query_understanding import _load_city_lookup
        _load_city_lookup()
        logger.info("City lookup preloaded.")
    except Exception as e:
        logger.warning(f"City lookup preload failed: {e}")

    logger.info("=== NEXORA Backend ready ===")
    yield
    logger.info("=== NEXORA Backend shutting down ===")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Hyper-personalized travel recommendation engine. APS-04 dataset.",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(search.router, tags=["Search"])
app.include_router(interactions.router, tags=["Interactions"])
app.include_router(profile.router, tags=["Profile"])
app.include_router(session.router, tags=["Session"])
app.include_router(health.router, tags=["Health"])
app.include_router(evaluation.router, tags=["Evaluation"])


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
