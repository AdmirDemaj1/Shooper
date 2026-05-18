"""Match history API endpoints."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from autoscout.auth.dependencies import get_db_user
from autoscout.db.models import Match, SearchProfile, User
from autoscout.db.session import get_db
from autoscout.matches.schemas import MatchActionRequest, MatchListResponse, MatchRead

# Routes live under /profiles/{id}/matches and /matches/{id}
profile_matches_router = APIRouter(prefix="/profiles", tags=["matches"])
matches_router = APIRouter(prefix="/matches", tags=["matches"])

_VALID_ACTIONS = {"clicked", "dismissed", "saved"}


@profile_matches_router.get("/{profile_id}/matches", response_model=MatchListResponse)
def list_profile_matches(
    profile_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None, description="ISO datetime cursor for pagination"),
    current_user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
):
    """List matches for a profile, newest first. Paginated via cursor (ISO datetime)."""
    profile = (
        db.query(SearchProfile)
        .filter(SearchProfile.id == str(profile_id), SearchProfile.user_id == str(current_user.id))
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    q = (
        db.query(Match)
        .options(joinedload(Match.listing))
        .filter(Match.search_profile_id == str(profile_id))
        .order_by(Match.created_at.desc())
    )

    if cursor:
        from datetime import datetime
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            q = q.filter(Match.created_at < cursor_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format (expected ISO datetime)")

    rows = q.limit(limit + 1).all()
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    next_cursor = str(rows[-1].created_at.isoformat()) if has_more and rows else None

    return MatchListResponse(
        matches=[MatchRead.model_validate(m) for m in rows],
        has_more=has_more,
        next_cursor=next_cursor,
    )


@matches_router.get("/{match_id}", response_model=MatchRead)
def get_match(
    match_id: UUID,
    current_user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
):
    """Get full match detail including listing and score reasoning."""
    match = (
        db.query(Match)
        .options(joinedload(Match.listing))
        .filter(Match.id == str(match_id))
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Ownership check via profile
    profile = (
        db.query(SearchProfile)
        .filter(
            SearchProfile.id == str(match.search_profile_id),
            SearchProfile.user_id == str(current_user.id),
        )
        .first()
    )
    if not profile:
        raise HTTPException(status_code=403, detail="Forbidden")

    return MatchRead.model_validate(match)


@matches_router.post("/{match_id}/action")
def record_match_action(
    match_id: UUID,
    body: MatchActionRequest,
    current_user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
):
    """Record a user action (clicked / dismissed / saved) on a match."""
    if body.action not in _VALID_ACTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action '{body.action}'. Must be one of: {sorted(_VALID_ACTIONS)}",
        )

    match = db.query(Match).filter(Match.id == str(match_id)).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Ownership check
    profile = (
        db.query(SearchProfile)
        .filter(
            SearchProfile.id == str(match.search_profile_id),
            SearchProfile.user_id == str(current_user.id),
        )
        .first()
    )
    if not profile:
        raise HTTPException(status_code=403, detail="Forbidden")

    match.user_action = body.action
    db.commit()
    return {"status": "ok", "match_id": str(match_id), "action": body.action}
