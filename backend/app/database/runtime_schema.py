"""
Runtime database schema.
This creates tables that extend (never replace) the APS-04 source data.
All original APS-04 data stays in the source DB (read-only).
We add: sessions, embedding metadata, user profile cache, runtime interactions.
"""
import logging
from app.database.connection import get_runtime_db

logger = logging.getLogger(__name__)

RUNTIME_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Sessions: stores session-level signals
CREATE TABLE IF NOT EXISTS sessions (
    session_id          TEXT PRIMARY KEY,
    user_id             TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    current_query       TEXT,
    current_constraints TEXT,  -- JSON
    session_preferences TEXT,  -- JSON
    intent_summary      TEXT
);

-- Runtime interactions (new interactions recorded via API, not in APS-04)
CREATE TABLE IF NOT EXISTS runtime_interactions (
    interaction_id      TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL,
    session_id          TEXT NOT NULL,
    entity_type         TEXT NOT NULL,
    entity_id           TEXT NOT NULL,
    interaction_type    TEXT NOT NULL,
    occurred_at         TEXT NOT NULL DEFAULT (datetime('now')),
    position_in_list    INTEGER,
    query_text          TEXT,
    implicit_rating     REAL
);

-- Embedding metadata: tracks which items have been embedded
CREATE TABLE IF NOT EXISTS embedding_metadata (
    entity_type     TEXT NOT NULL,
    entity_id       TEXT NOT NULL,
    model_name      TEXT NOT NULL,
    embedding_dim   INTEGER NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (entity_type, entity_id)
);

-- User profile cache (computed signals, refreshed on interaction)
CREATE TABLE IF NOT EXISTS user_profile_cache (
    user_id             TEXT PRIMARY KEY,
    profile_json        TEXT NOT NULL,  -- serialized UserProfile
    maturity_score      REAL NOT NULL DEFAULT 0.0,
    maturity_class      TEXT NOT NULL DEFAULT 'cold_start',
    interaction_count   INTEGER NOT NULL DEFAULT 0,
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Rank change log: tracks rank movements per session query
CREATE TABLE IF NOT EXISTS rank_changes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    entity_id       TEXT NOT NULL,
    entity_type     TEXT NOT NULL,
    previous_rank   INTEGER,
    new_rank        INTEGER,
    rank_delta      INTEGER,
    occurred_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Index on frequently queried columns
CREATE INDEX IF NOT EXISTS idx_ri_user ON runtime_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_ri_session ON runtime_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_ri_entity ON runtime_interactions(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""


def init_runtime_db():
    """Create all runtime tables if they don't exist."""
    with get_runtime_db() as conn:
        conn.executescript(RUNTIME_SCHEMA)
        logger.info("Runtime database schema initialized.")
