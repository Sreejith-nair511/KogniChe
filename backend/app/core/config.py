"""
Core configuration for the NEXORA backend.
All settings can be overridden via environment variables or .env file.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "NEXORA Recommendation Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database — SQLite backed by APS-04
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/runtime/nexora_runtime.db"
    SOURCE_DB_PATH: str = str(BASE_DIR / "data" / "source" / "Recommendations" / "data" / "APS-04.db")

    # Vector index storage
    VECTOR_INDEX_DIR: str = str(BASE_DIR / "data" / "runtime" / "vector_index")

    # Embedding model — multilingual, supports en/hi/ta/kn/ml/bn/mr/te
    EMBEDDING_MODEL: str = "paraphrase-multilingual-mpnet-base-v2"
    EMBEDDING_DIMENSION: int = 768
    EMBEDDING_BATCH_SIZE: int = 64

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # LLM (optional, system works without it)
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""

    # Ranking weights — configurable
    WEIGHT_SEMANTIC: float = 0.40
    WEIGHT_PROFILE: float = 0.25
    WEIGHT_BEHAVIOUR: float = 0.15
    WEIGHT_COLLABORATIVE: float = 0.05
    WEIGHT_RATING: float = 0.05
    WEIGHT_POPULARITY: float = 0.03
    WEIGHT_DIVERSITY: float = 0.07

    # Interaction signal weights
    SIGNAL_CLICK: float = 0.25
    SIGNAL_LIKE: float = 0.60
    SIGNAL_SAVE: float = 0.80
    SIGNAL_BOOK: float = 1.00
    SIGNAL_DISLIKE: float = -0.70
    SIGNAL_DISMISS: float = -0.20
    SIGNAL_VIEW: float = 0.05
    SIGNAL_SHARE: float = 0.40

    # Retrieval
    SEMANTIC_CANDIDATE_LIMIT: int = 50
    FINAL_RESULT_LIMIT: int = 10
    DIVERSITY_LAMBDA: float = 0.7  # MMR lambda — higher = more relevance, lower = more diversity

    # Profile maturity thresholds
    MATURITY_COLD_START: int = 0
    MATURITY_EARLY: int = 5
    MATURITY_LEARNING: int = 20
    MATURITY_MATURE: int = 50

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

settings = Settings()
