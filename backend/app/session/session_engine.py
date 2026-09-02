"""
Session Engine.
Tracks short-term user intent and recent behaviour within a session.
Session signals have higher weight than historical long-term behaviour.
"""
import json
import uuid
import logging
from typing import Optional
from datetime import datetime

from app.database.connection import get_runtime_db

logger = logging.getLogger(__name__)

SESSION_INTERACTION_WEIGHTS = {
    "like": 0.80,
    "save": 0.60,
    "click": 0.25,
    "view": 0.05,
    "book": 1.00,
    "share": 0.40,
    "dismiss": -0.30,
    "dislike": -0.80,
    "search": 0.10,
}


class SessionProfile:
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.current_query: Optional[str] = None
        self.current_constraints: dict = {}
        self.recent_interactions: list[dict] = []
        self.session_preferences: dict[str, float] = {}  # entity_type → affinity delta
        self.intent_summary: Optional[str] = None
        self.liked_in_session: list[str] = []
        self.saved_in_session: list[str] = []
        self.disliked_in_session: list[str] = []
        self.clicked_in_session: list[str] = []


def create_or_load_session(session_id: Optional[str], user_id: Optional[str]) -> SessionProfile:
    """Create a new session or load an existing one from runtime DB."""
    if not session_id:
        session_id = f"ses_{uuid.uuid4().hex[:12]}"

    session = SessionProfile(session_id=session_id, user_id=user_id)

    try:
        with get_runtime_db() as rt:
            cur = rt.cursor()
            cur.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            if row:
                session.current_query = row["current_query"]
                session.current_constraints = json.loads(row["current_constraints"] or "{}")
                session.session_preferences = json.loads(row["session_preferences"] or "{}")
                session.intent_summary = row["intent_summary"]

                # Load recent interactions from this session
                cur.execute("""
                    SELECT entity_id, entity_type, interaction_type, occurred_at
                    FROM runtime_interactions
                    WHERE session_id = ?
                    ORDER BY occurred_at DESC
                    LIMIT 20
                """, (session_id,))
                for r in cur.fetchall():
                    session.recent_interactions.append(dict(r))
                    itype = r["interaction_type"]
                    eid = r["entity_id"]
                    if itype == "like" and eid not in session.liked_in_session:
                        session.liked_in_session.append(eid)
                    elif itype == "save" and eid not in session.saved_in_session:
                        session.saved_in_session.append(eid)
                    elif itype in ("dislike", "dismiss") and eid not in session.disliked_in_session:
                        session.disliked_in_session.append(eid)
                    elif itype == "click" and eid not in session.clicked_in_session:
                        session.clicked_in_session.append(eid)
            else:
                # New session — persist it
                rt.execute("""
                    INSERT OR IGNORE INTO sessions (session_id, user_id, created_at, updated_at)
                    VALUES (?, ?, datetime('now'), datetime('now'))
                """, (session_id, user_id))
    except Exception as e:
        logger.warning(f"Session load error ({session_id}): {e}")

    return session


def update_session(session: SessionProfile, interaction_type: str, entity_id: str, entity_type: str):
    """Record a new interaction in the session and update signals."""
    # Update in-memory state
    itype = interaction_type.lower()
    if itype == "like" and entity_id not in session.liked_in_session:
        session.liked_in_session.append(entity_id)
    elif itype == "save" and entity_id not in session.saved_in_session:
        session.saved_in_session.append(entity_id)
    elif itype in ("dislike", "dismiss") and entity_id not in session.disliked_in_session:
        session.disliked_in_session.append(entity_id)
    elif itype == "click" and entity_id not in session.clicked_in_session:
        session.clicked_in_session.append(entity_id)

    weight = SESSION_INTERACTION_WEIGHTS.get(itype, 0.0)
    key = f"entity:{entity_id}"
    session.session_preferences[key] = session.session_preferences.get(key, 0.0) + weight

    type_key = f"type:{entity_type}"
    session.session_preferences[type_key] = session.session_preferences.get(type_key, 0.0) + weight * 0.5

    session.recent_interactions.insert(0, {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "interaction_type": itype,
        "occurred_at": datetime.utcnow().isoformat(),
    })
    # Keep only last 20 in memory
    session.recent_interactions = session.recent_interactions[:20]

    # Persist to runtime DB
    try:
        with get_runtime_db() as rt:
            rt.execute("""
                UPDATE sessions SET
                    session_preferences = ?,
                    updated_at = datetime('now')
                WHERE session_id = ?
            """, (json.dumps(session.session_preferences), session.session_id))
    except Exception as e:
        logger.warning(f"Session update error: {e}")


def update_session_query(session: SessionProfile, query: str, constraints: dict):
    """Record the current query and constraints in the session."""
    session.current_query = query
    session.current_constraints = constraints
    try:
        with get_runtime_db() as rt:
            rt.execute("""
                UPDATE sessions SET
                    current_query = ?,
                    current_constraints = ?,
                    updated_at = datetime('now')
                WHERE session_id = ?
            """, (query, json.dumps(constraints), session.session_id))
    except Exception as e:
        logger.warning(f"Session query update error: {e}")


def get_session_score(session: SessionProfile, entity_id: str, entity_type: str) -> float:
    """
    Compute a session-level relevance score for a candidate.
    Items liked/saved in this session get a boost.
    Items disliked/dismissed get a penalty.
    """
    score = 0.0
    key = f"entity:{entity_id}"
    type_key = f"type:{entity_type}"
    score += session.session_preferences.get(key, 0.0)
    score += session.session_preferences.get(type_key, 0.0) * 0.3
    # Recency boost for items matching session liked types
    if entity_type in [i.get("entity_type") for i in session.recent_interactions[:5] if i.get("interaction_type") == "like"]:
        score += 0.2
    return max(-1.0, min(1.0, score))
