"""Full matching pipeline: filter → score → persist to matches table."""
from __future__ import annotations

import logging
from typing import Any

from redis import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from autoscout.db.models import Match, SearchProfile
from autoscout.db.session import SessionLocal
from autoscout.matching.filters import get_candidate_listings
from autoscout.matching.scorer import score_listings
from autoscout.settings import settings

logger = logging.getLogger(__name__)

TOP_N_DEFAULT = 5


def run_pipeline(
    profile_id: str,
    db: Session | None = None,
    redis_client: Redis | None = None,
    top_n: int | None = None,
) -> dict[str, Any]:
    """
    Execute the full matching pipeline for a single profile.

    Steps:
      1. Strict filter + already-seen suppression  → candidate listings
      2. LLM (or fallback) relevance scoring
      3. Top-N selection
      4. Persist all scored candidates to `matches`; mark top-N as selected_for_delivery

    Accepts an optional `db` session (used by the admin endpoint so it can
    share the request-scoped session); creates its own session otherwise.

    Returns a summary dict.
    """
    own_db = db is None
    if own_db:
        db = SessionLocal()

    try:
        profile = (
            db.query(SearchProfile)
            .filter(SearchProfile.id == profile_id, SearchProfile.is_active == True)  # noqa: E712
            .first()
        )
        if not profile:
            return {"status": "skipped", "reason": "profile not found or inactive", "profile_id": profile_id}

        # ── Step 1: candidates ───────────────────────────────────────────────
        candidates = get_candidate_listings(db, profile)
        logger.info("[pipeline] profile=%s candidates=%d", profile_id, len(candidates))

        if not candidates:
            return {"status": "ok", "profile_id": profile_id, "candidates": 0, "inserted": 0, "top_n": 0}

        # ── Step 2: scoring ──────────────────────────────────────────────────
        if redis_client is None:
            try:
                redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            except Exception:
                pass

        scores = score_listings(profile, candidates, redis_client, db=db)
        score_map = {s["listing_id"]: s for s in scores}

        # ── Step 3: top-N selection ──────────────────────────────────────────
        n = top_n or TOP_N_DEFAULT
        sorted_scores = sorted(scores, key=lambda s: -s["score"])
        top_ids = {s["listing_id"] for s in sorted_scores[:n]}

        # ── Step 4: persist ──────────────────────────────────────────────────
        inserted = 0
        skipped = 0
        for listing in candidates:
            lid = str(listing.id)
            sd = score_map.get(lid, {
                "score": 50,
                "reasoning": "No score available.",
                "summary": "",
                "score_source": "fallback",
            })
            match = Match(
                search_profile_id=profile.id,
                listing_id=listing.id,
                relevance_score=sd["score"],
                score_source=sd.get("score_source", "llm"),
                llm_reasoning=sd.get("reasoning", ""),
                summary=sd.get("summary", ""),
                selected_for_delivery=lid in top_ids,
                delivery_status="pending",
            )
            db.add(match)
            try:
                db.flush()
                inserted += 1
            except IntegrityError:
                # (profile, listing) pair already exists — skip
                db.rollback()
                skipped += 1

        db.commit()
        logger.info(
            "[pipeline] profile=%s inserted=%d skipped=%d top_n=%d",
            profile_id, inserted, skipped, len(top_ids),
        )
        return {
            "status": "ok",
            "profile_id": profile_id,
            "candidates": len(candidates),
            "inserted": inserted,
            "skipped": skipped,
            "top_n": min(n, inserted),
        }

    except Exception as exc:
        db.rollback()
        logger.error("[pipeline] Error for profile %s: %s", profile_id, exc, exc_info=True)
        return {"status": "error", "profile_id": profile_id, "error": str(exc)}
    finally:
        if own_db:
            db.close()
