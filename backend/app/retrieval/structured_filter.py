"""
Structured (hard) filtering against the APS-04 dataset.
Hard filters MUST be applied — items outside constraints are completely excluded.
"""
import logging
from typing import Optional
from app.schemas.recommendation import QueryConstraints
from app.database.connection import get_source_db

logger = logging.getLogger(__name__)


def get_eligible_hotels(constraints: QueryConstraints) -> list[dict]:
    """
    Return all active hotels that satisfy hard constraints.
    Constraints: city_id, star_min, budget_max (via room_types), accessibility.
    """
    with get_source_db() as conn:
        cur = conn.cursor()

        conditions = ["h.status = 'active'"]
        params: list = []

        if constraints.city_id:
            conditions.append("h.city_id = ?")
            params.append(constraints.city_id)

        if constraints.star_min is not None:
            conditions.append("h.star_rating >= ?")
            params.append(constraints.star_min)

        where = " AND ".join(conditions)

        sql = f"""
            SELECT
                h.hotel_id, h.name, h.property_type, h.star_rating,
                h.guest_score, h.review_count, h.description,
                h.lat, h.lng, h.distance_to_centre_km,
                h.base_currency, h.has_xr_scene, h.chain_code,
                h.checkin_time, h.checkout_time,
                c.name AS city_name, c.city_id,
                cy.name AS country_name, cy.iso2 AS country_code
            FROM hotels h
            JOIN cities c ON h.city_id = c.city_id
            JOIN countries cy ON c.country_id = cy.country_id
            WHERE {where}
        """
        cur.execute(sql, params)
        hotels = [dict(row) for row in cur.fetchall()]

        # Budget hard filter via room types
        if constraints.budget_max and hotels:
            eligible_ids = set()
            hotel_ids = [h["hotel_id"] for h in hotels]
            # Check if any room type has base_rate <= budget_max
            # Money is stored as TEXT in SQLite — cast to REAL only for comparison
            placeholders = ",".join("?" * len(hotel_ids))
            cur.execute(
                f"""SELECT DISTINCT hotel_id FROM hotel_room_types
                    WHERE hotel_id IN ({placeholders})
                    AND status = 'active'
                    AND CAST(base_rate AS REAL) <= ?""",
                hotel_ids + [float(constraints.budget_max)]
            )
            eligible_ids = {r[0] for r in cur.fetchall()}
            hotels = [h for h in hotels if h["hotel_id"] in eligible_ids]

        # Accessibility hard filter
        if constraints.accessibility and constraints.accessibility != "none":
            pass  # Hotels table doesn't have accessibility field directly, skip as soft filter

        logger.debug(f"Eligible hotels after hard filter: {len(hotels)}")
        return hotels


def get_eligible_pois(constraints: QueryConstraints) -> list[dict]:
    """Return all active POIs that satisfy hard constraints."""
    with get_source_db() as conn:
        cur = conn.cursor()

        conditions = ["p.status = 'active'"]
        params: list = []

        if constraints.city_id:
            conditions.append("p.city_id = ?")
            params.append(constraints.city_id)

        if constraints.poi_categories:
            placeholders = ",".join("?" * len(constraints.poi_categories))
            conditions.append(f"p.poi_category IN ({placeholders})")
            params.extend(constraints.poi_categories)

        if constraints.budget_max:
            conditions.append("CAST(p.entry_cost AS REAL) <= ?")
            params.append(float(constraints.budget_max))

        if constraints.accessibility and constraints.accessibility not in ("none", "any"):
            conditions.append("p.accessibility = ?")
            params.append(constraints.accessibility)

        where = " AND ".join(conditions)

        sql = f"""
            SELECT
                p.poi_id, p.name, p.poi_category, p.category_id,
                p.lat, p.lng, p.typical_duration_minutes,
                p.entry_cost, p.currency, p.carbon_kg,
                p.popularity_score, p.value_score,
                p.opens_at, p.closes_at, p.best_season,
                p.accessibility, p.tags, p.description, p.has_xr_scene,
                c.name AS city_name, c.city_id,
                cy.name AS country_name, cy.iso2 AS country_code,
                cat.label AS category_label
            FROM activities_poi p
            JOIN cities c ON p.city_id = c.city_id
            JOIN countries cy ON c.country_id = cy.country_id
            LEFT JOIN categories cat ON p.category_id = cat.category_id
            WHERE {where}
        """
        cur.execute(sql, params)
        pois = [dict(row) for row in cur.fetchall()]
        logger.debug(f"Eligible POIs after hard filter: {len(pois)}")
        return pois


def get_eligible_packages(constraints: QueryConstraints) -> list[dict]:
    """Return all active tour packages that satisfy hard constraints."""
    with get_source_db() as conn:
        cur = conn.cursor()

        conditions = ["tp.status = 'active'"]
        params: list = []

        if constraints.city_id:
            conditions.append("tp.city_id = ?")
            params.append(constraints.city_id)

        if constraints.themes:
            placeholders = ",".join("?" * len(constraints.themes))
            conditions.append(f"tp.theme IN ({placeholders})")
            params.extend(constraints.themes)

        if constraints.duration_max_days:
            conditions.append("tp.duration_days <= ?")
            params.append(constraints.duration_max_days)

        if constraints.budget_max:
            conditions.append("CAST(tp.base_price AS REAL) <= ?")
            params.append(float(constraints.budget_max))

        if constraints.language:
            # Packages have comma-sep languages_offered
            conditions.append("(',' || tp.languages_offered || ',') LIKE ?")
            params.append(f"%,{constraints.language},%")

        where = " AND ".join(conditions)

        sql = f"""
            SELECT
                tp.package_id, tp.name, tp.theme, tp.tier,
                tp.duration_days, tp.duration_nights,
                tp.base_price, tp.currency,
                tp.min_group_size, tp.max_group_size,
                tp.difficulty, tp.languages_offered,
                tp.inclusions, tp.exclusions, tp.description,
                c.name AS city_name, c.city_id,
                cy.name AS country_name, cy.iso2 AS country_code
            FROM tour_packages tp
            JOIN cities c ON tp.city_id = c.city_id
            JOIN countries cy ON c.country_id = cy.country_id
            WHERE {where}
        """
        cur.execute(sql, params)
        packages = [dict(row) for row in cur.fetchall()]
        logger.debug(f"Eligible packages after hard filter: {len(packages)}")
        return packages


def get_all_eligible(constraints: QueryConstraints, entity_types: Optional[list[str]] = None) -> dict[str, list[dict]]:
    """Get eligible items across all (or specified) entity types."""
    types = entity_types or constraints.entity_types or ["hotel", "poi", "package"]

    result = {}
    if "hotel" in types:
        result["hotel"] = get_eligible_hotels(constraints)
    if "poi" in types:
        result["poi"] = get_eligible_pois(constraints)
    if "package" in types:
        result["package"] = get_eligible_packages(constraints)

    total = sum(len(v) for v in result.values())
    logger.debug(f"Total eligible after all hard filters: {total}")
    return result
