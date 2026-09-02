"""
Dataset Import Script — APS-04
Validates source DB integrity, reports statistics, and initialises the runtime DB.
The source DB (APS-04.db) is already the authoritative dataset — we do NOT copy it;
we open it read-only and just verify and report.
"""
import sys
import sqlite3
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.database.connection import get_source_db, get_runtime_db
from app.database.runtime_schema import init_runtime_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def validate_and_report():
    logger.info("=" * 60)
    logger.info("NEXORA Dataset Import & Validation")
    logger.info("=" * 60)

    src_path = Path(settings.SOURCE_DB_PATH)
    if not src_path.exists():
        logger.error(f"Source DB not found: {src_path}")
        logger.error("Please ensure APS-04.db is at: data/source/Recommendations/data/APS-04.db")
        sys.exit(1)

    logger.info(f"Source DB: {src_path}")

    with get_source_db() as conn:
        cur = conn.cursor()

        # Table counts
        expected_tables = [
            "users", "user_preferences", "user_interactions",
            "hotels", "hotel_room_types", "hotel_reviews",
            "activities_poi", "tour_packages",
            "cities", "countries", "currencies", "languages", "categories",
            "eval_queries", "eval_relevance_labels",
        ]

        logger.info("\n--- Table Row Counts ---")
        counts = {}
        for table in expected_tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                n = cur.fetchone()[0]
                counts[table] = n
                logger.info(f"  {table:<30} {n:>8} rows")
            except Exception as e:
                logger.error(f"  {table:<30} ERROR: {e}")

        # User cohorts
        logger.info("\n--- User Cohorts ---")
        cur.execute("""
            SELECT u.segment,
                   COUNT(DISTINCT u.user_id) AS users,
                   COUNT(i.interaction_id) AS interactions,
                   ROUND(1.0*COUNT(i.interaction_id)/COUNT(DISTINCT u.user_id),1) AS per_user
            FROM users u
            LEFT JOIN user_interactions i ON i.user_id = u.user_id
            GROUP BY u.segment
        """)
        for row in cur.fetchall():
            logger.info(f"  segment={row[0]:<12} users={row[1]:<6} interactions={row[2]:<8} per_user={row[3]}")

        # Eval set
        logger.info("\n--- Evaluation Set ---")
        cur.execute("SELECT language, COUNT(*) FROM eval_queries GROUP BY language")
        for row in cur.fetchall():
            logger.info(f"  eval_queries language={row[0]:<10} count={row[1]}")

        cur.execute("SELECT grade, COUNT(*) FROM eval_relevance_labels GROUP BY grade ORDER BY grade DESC")
        for row in cur.fetchall():
            logger.info(f"  eval_relevance_labels grade={row[0]} count={row[1]}")

        # Entity types in interactions
        logger.info("\n--- Interaction Entity Types ---")
        cur.execute("SELECT entity_type, COUNT(*) as cnt FROM user_interactions GROUP BY entity_type ORDER BY cnt DESC")
        for row in cur.fetchall():
            logger.info(f"  {row[0]:<20} {row[1]}")

        # Review languages
        logger.info("\n--- Hotel Review Languages ---")
        cur.execute("SELECT language, COUNT(*) FROM hotel_reviews GROUP BY language ORDER BY COUNT(*) DESC")
        for row in cur.fetchall():
            logger.info(f"  {row[0]:<15} {row[1]}")

        # Cold-start users
        cur.execute("SELECT COUNT(*) FROM users WHERE segment='cold_start'")
        cold = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE segment='heavy'")
        heavy = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE segment='light'")
        light = cur.fetchone()[0]
        logger.info(f"\n  Cold-start users: {cold} (zero interactions — cold start testable)")
        logger.info(f"  Heavy users:      {heavy} (avg ~42 interactions each)")
        logger.info(f"  Light users:      {light} (avg ~10 interactions each)")

        # Validation checks
        logger.info("\n--- Validation ---")
        errors = 0

        # Check all user IDs have usr_ prefix
        cur.execute("SELECT COUNT(*) FROM users WHERE user_id NOT LIKE 'usr_%'")
        bad = cur.fetchone()[0]
        if bad > 0:
            logger.error(f"  {bad} users with invalid ID prefix")
            errors += 1
        else:
            logger.info("  ✓ All user IDs have usr_ prefix")

        # Check FK: user_interactions → users
        cur.execute("""
            SELECT COUNT(*) FROM user_interactions i
            WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.user_id = i.user_id)
        """)
        bad = cur.fetchone()[0]
        if bad > 0:
            logger.error(f"  {bad} user_interactions with orphan user_id")
            errors += 1
        else:
            logger.info("  ✓ All user_interactions have valid user_id FK")

        # Check money: base_rate is 2-decimal TEXT
        cur.execute("SELECT COUNT(*) FROM hotel_room_types WHERE base_rate NOT GLOB '*.*'")
        bad = cur.fetchone()[0]
        if bad > 0:
            logger.warning(f"  {bad} room types with non-decimal base_rate")
        else:
            logger.info("  ✓ Money fields appear valid (TEXT with decimal point)")

        # Check eval_relevance_labels grades are 0-3
        cur.execute("SELECT COUNT(*) FROM eval_relevance_labels WHERE grade NOT IN (0,1,2,3)")
        bad = cur.fetchone()[0]
        if bad > 0:
            logger.error(f"  {bad} eval labels with out-of-range grade")
            errors += 1
        else:
            logger.info("  ✓ All relevance grades in range 0-3")

        # Check position_in_list present for debiasing
        cur.execute("SELECT COUNT(*) FROM user_interactions WHERE position_in_list IS NOT NULL")
        with_pos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM user_interactions")
        total = cur.fetchone()[0]
        logger.info(f"  position_in_list present: {with_pos}/{total} interactions (use for debiasing)")

    # Initialise runtime DB
    logger.info("\n--- Runtime DB Initialisation ---")
    try:
        init_runtime_db()
        logger.info("  ✓ Runtime DB schema ready")
    except Exception as e:
        logger.error(f"  Runtime DB init failed: {e}")
        errors += 1

    logger.info("\n" + "=" * 60)
    if errors == 0:
        logger.info("Dataset imported successfully")
        logger.info(f"  Users:            {counts.get('users', 0)}")
        logger.info(f"  Hotels:           {counts.get('hotels', 0)}")
        logger.info(f"  Activities/POIs:  {counts.get('activities_poi', 0)}")
        logger.info(f"  Tour packages:    {counts.get('tour_packages', 0)}")
        logger.info(f"  Interactions:     {counts.get('user_interactions', 0)}")
        logger.info(f"  Evaluation queries: {counts.get('eval_queries', 0)}")
        logger.info(f"  Relevance labels: {counts.get('eval_relevance_labels', 0)}")
        logger.info(f"  Hotel reviews:    {counts.get('hotel_reviews', 0)}")
        logger.info("=" * 60)
        logger.info("Next step: python scripts/generate_embeddings.py")
    else:
        logger.error(f"{errors} validation error(s). Check the source dataset.")
    return errors


if __name__ == "__main__":
    sys.exit(validate_and_report())
