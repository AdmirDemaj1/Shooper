"""Backend Celery app for the matching pipeline.

Run as:
  poetry run celery -A autoscout.matching.worker worker -B --loglevel=info
"""
from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

celery_app = Celery("autoscout_matching")
celery_app.conf.broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app.conf.result_backend = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"
celery_app.conf.task_default_queue = "backend"
celery_app.conf.beat_schedule = {
    "run-daily-matching-pipeline": {
        "task": "autoscout.matching.worker.run_daily_pipelines",
        "schedule": crontab(
            minute=int(os.getenv("PIPELINE_SCHEDULE_MINUTE", "0")),
            hour=int(os.getenv("PIPELINE_SCHEDULE_HOUR", "7")),
        ),
    }
}


@celery_app.task(bind=True, name="autoscout.matching.worker.run_matching_pipeline")
def run_matching_pipeline(self, profile_id: str) -> dict:
    """Run the full matching pipeline for one profile."""
    from autoscout.matching.pipeline import run_pipeline
    return run_pipeline(profile_id)


@celery_app.task(bind=True, name="autoscout.matching.worker.match_new_listing")
def match_new_listing(self, listing_id: str) -> dict:
    """
    When a platform listing is posted, run the pipeline for every active profile
    whose hard bounds the listing passes (capped at MAX_PROFILES to limit LLM cost).
    """
    from autoscout.db.models import Listing, SearchProfile
    from autoscout.db.session import SessionLocal
    from autoscout.matching.filters import _passes_geo_filter, _passes_hard_bounds
    from autoscout.matching.pipeline import run_pipeline

    MAX_PROFILES = 50

    db = SessionLocal()
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if not listing:
            return {"status": "skipped", "reason": "listing not found"}

        profiles = (
            db.query(SearchProfile)
            .filter(SearchProfile.is_active.is_(True))
            .limit(MAX_PROFILES * 4)  # over-fetch to account for filtering
            .all()
        )

        triggered = 0
        for profile in profiles:
            if triggered >= MAX_PROFILES:
                break
            if _passes_hard_bounds(listing, profile) and _passes_geo_filter(listing, profile):
                run_pipeline(str(profile.id))
                triggered += 1

        print(f"[match_new_listing] listing={listing_id} triggered={triggered} pipelines")
        return {"status": "ok", "listing_id": listing_id, "triggered": triggered}
    finally:
        db.close()


@celery_app.task(bind=True, name="autoscout.matching.worker.run_daily_pipelines")
def run_daily_pipelines(self) -> dict:
    """Fan out one run_matching_pipeline task per active profile."""
    from autoscout.db.models import SearchProfile
    from autoscout.db.session import SessionLocal

    db = SessionLocal()
    try:
        profiles = db.query(SearchProfile).filter(SearchProfile.is_active == True).all()  # noqa: E712
        for profile in profiles:
            run_matching_pipeline.delay(str(profile.id))
        print(f"[pipeline-scheduler] queued {len(profiles)} pipeline tasks")
        return {"status": "ok", "queued": len(profiles)}
    finally:
        db.close()
