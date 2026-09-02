"""
Database connection management.
Runtime DB is SQLite at data/runtime/nexora_runtime.db.
Source DB (read-only) is the APS-04 dataset at data/source/.../APS-04.db.
"""
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_runtime_db_path() -> Path:
    path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_source_db_path() -> Path:
    return Path(settings.SOURCE_DB_PATH)


def _make_row_factory(conn: sqlite3.Connection) -> sqlite3.Connection:
    """Return rows as dicts."""
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_runtime_db():
    """Runtime database — writeable, holds sessions, additional interactions, embeddings metadata."""
    path = get_runtime_db_path()
    conn = sqlite3.connect(str(path), check_same_thread=False)
    _make_row_factory(conn)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_source_db():
    """Source DB — read-only APS-04 dataset."""
    path = get_source_db_path()
    if not path.exists():
        raise RuntimeError(f"APS-04 source database not found at {path}. Run scripts/import_dataset.py first.")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    _make_row_factory(conn)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def check_source_db() -> dict:
    """Check the source database is accessible and has expected tables."""
    try:
        with get_source_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [r[0] for r in cur.fetchall()]
            counts = {}
            for t in tables:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
            return {"status": "ok", "tables": tables, "counts": counts}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_runtime_db() -> dict:
    """Check runtime database."""
    try:
        with get_runtime_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [r[0] for r in cur.fetchall()]
            return {"status": "ok", "tables": tables}
    except Exception as e:
        return {"status": "error", "error": str(e)}
