"""
Interaction Service.
Handles LIKE, SAVE, DISLIKE, CLICK, VIEW, DISMISS.
Records interaction, updates session + profile, re-ranks, returns rank movements.
"""
import uuid
import json
import logging
from datetime import datetime
from typing import Optional

from app.schemas.recommendation import (
    InteractionRequest, InteractionResponse, RankChange, ProfileUpdate,
    ProfileDNA, DNADimension,
)
from app.database.connection import get_runtime_db
from app.personalization.user_profile import get_or_build_profile, invalidate_profile_cache, UserProfile
from app.session.session_engine import create_or_load_session, update_session
from app.services.recommendation_service import search, _build_session_summary, _build_profile_summary
from app.schemas.recommendation import SearchRequest, SearchFilters

logger = logging.getLogger(__name__)


def record_interaction(request: InteractionRequest) -> InteractionResponse:
    """
    Full interaction pipeline:
    1. Validate interaction
    2. Store in runtime DB
    3. Update session
    4. Invalidate & rebuild profile
    5. Re-run recommendation query
    6. Calculate rank movements
    7. Return updated state
    """
    valid_types = {"view", "click", "like", "save", "book", "dismiss", "dislike", "share", "search"}
    if request.interaction_type.lower() not in valid_types:
        return InteractionResponse(
            recorded=False,
            interaction_id="",
            rank_changes=[],
            recommendations=[],
        )

    interaction_id = f"rit_{uuid.uuid4().hex[:12]}"

    # Store interaction
    try:
        with get_runtime_db() as rt:
            rt.execute("""
                INSERT INTO runtime_interactions
                    (interaction_id, user_id, session_id, entity_type, entity_id,
                     interaction_type, occurred_at, position_in_list, query_text)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
            """, (
                interaction_id,
                request.user_id,
                request.session_id,
                request.entity_type,
                request.entity_id,
                request.interaction_type.lower(),
                request.position_in_list,
                request.query_text,
            ))
    except Exception as e:
        logger.error(f"Failed to store interaction: {e}")
        return InteractionResponse(
            recorded=False,
            interaction_id=interaction_id,
            rank_changes=[],
            recommendations=[],
        )

    # Load session and update
    session = create_or_load_session(request.session_id, request.user_id)
    update_session(session, request.interaction_type, request.entity_id, request.entity_type)

    # Invalidate profile cache so rebuild uses the new interaction
    invalidate_profile_cache(request.user_id)

    # Rebuild profile
    profile_before = get_or_build_profile(request.user_id)
    dna_before = _extract_dna(profile_before)

    invalidate_profile_cache(request.user_id)
    profile_after = get_or_build_profile(request.user_id, force_rebuild=True)
    dna_after = _extract_dna(profile_after)

    # Re-run recommendations if we have a query
    recommendations = []
    rank_changes = []
    if session.current_query:
        prev_query = session.current_query
        prev_constraints_data = session.current_constraints or {}

        # Reconstruct filters from session constraints
        filters = SearchFilters(
            city_id=prev_constraints_data.get("city_id"),
            budget_max=prev_constraints_data.get("budget_max"),
            star_min=prev_constraints_data.get("star_min"),
        )

        search_req = SearchRequest(
            user_id=request.user_id,
            session_id=request.session_id,
            query=prev_query,
            filters=filters,
            limit=10,
        )
        response = search(search_req)
        recommendations = response.results

        # Calculate rank changes (compare with stored rank before interaction)
        rank_changes = _compute_rank_changes(
            request.session_id,
            request.entity_id,
            recommendations,
        )

        # Annotate recommendations with rank changes
        rank_change_map = {rc: rank_changes[i] for i, rc in enumerate([r.entity_id for r in recommendations[:len(rank_changes)]])}
        for item in recommendations:
            item.rank_change = rank_change_map.get(item.entity_id)

    # Build profile update summary
    changed_dims = _changed_dimensions(dna_before, dna_after)
    profile_update = ProfileUpdate(
        changed_dimensions=changed_dims,
        dna_before=dna_before,
        dna_after=dna_after,
    )

    return InteractionResponse(
        recorded=True,
        interaction_id=interaction_id,
        profile_update=profile_update,
        session_update=_build_session_summary(session),
        rank_changes=rank_changes,
        recommendations=recommendations,
    )


def _extract_dna(profile: Optional[UserProfile]) -> Optional[ProfileDNA]:
    if not profile:
        return None
    return ProfileDNA(
        dimensions=[
            DNADimension(
                dimension=dim,
                score=round(score, 3),
                previous_score=None,
                change=0.0,
            )
            for dim, score in sorted(profile.dna.items(), key=lambda x: -x[1])
        ],
        confidence=round(profile.maturity_score, 3),
        profile_maturity=profile.maturity_class,
    )


def _changed_dimensions(before: Optional[ProfileDNA], after: Optional[ProfileDNA]) -> list[str]:
    """Identify DNA dimensions that changed significantly."""
    if not before or not after:
        return []
    before_map = {d.dimension: d.score for d in before.dimensions}
    after_map = {d.dimension: d.score for d in after.dimensions}
    changed = []
    for dim, score in after_map.items():
        prev = before_map.get(dim, 0.0)
        if abs(score - prev) > 0.05:
            changed.append(dim)
    return changed


def _compute_rank_changes(
    session_id: str,
    interacted_entity_id: str,
    new_results: list,
) -> list[RankChange]:
    """
    Compute rank changes by comparing new ranking against last stored ranking for this session.
    """
    # Load previous ranks from runtime DB
    prev_ranks: dict[str, int] = {}
    try:
        with get_runtime_db() as rt:
            cur = rt.cursor()
            cur.execute("""
                SELECT entity_id, new_rank FROM rank_changes
                WHERE session_id = ?
                ORDER BY occurred_at DESC
                LIMIT 50
            """, (session_id,))
            for row in cur.fetchall():
                if row["entity_id"] not in prev_ranks:
                    prev_ranks[row["entity_id"]] = row["new_rank"]
    except Exception as e:
        logger.debug(f"Could not load prev ranks: {e}")

    changes = []
    for item in new_results:
        eid = item.entity_id
        new_rank = item.rank
        prev_rank = prev_ranks.get(eid)

        if prev_rank is None:
            # New in ranking
            rc = RankChange(previous_rank=None, new_rank=new_rank, rank_delta=0, direction="new")
        else:
            delta = prev_rank - new_rank  # positive = moved up
            direction = "up" if delta > 0 else "down" if delta < 0 else "unchanged"
            rc = RankChange(previous_rank=prev_rank, new_rank=new_rank, rank_delta=delta, direction=direction)

        changes.append(rc)

        # Persist new rank
        try:
            with get_runtime_db() as rt:
                rt.execute("""
                    INSERT INTO rank_changes (session_id, entity_id, entity_type, previous_rank, new_rank, rank_delta, occurred_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """, (session_id, eid, item.entity_type, prev_rank, new_rank, changes[-1].rank_delta))
        except Exception as e:
            logger.debug(f"Could not persist rank change: {e}")

    return changes
