import os
from celery import Celery
from celery.schedules import crontab

from crawler.db import SessionLocal
from crawler.models import SearchProfile
from crawler.persistence import persist_listings
from crawler.settings import settings
from crawler.sources.registry import get_adapter

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery("autoscout")
app.conf.broker_url = redis_url
app.conf.result_backend = redis_url
app.conf.task_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.result_serializer = "json"
app.conf.timezone = "UTC"
app.conf.task_default_queue = "crawler"
app.conf.beat_schedule = {
    "crawl-active-profiles-daily": {
        "task": "crawler.worker.schedule_daily_crawls",
        "schedule": crontab(
            minute=settings.CRAWL_SCHEDULE_MINUTE,
            hour=settings.CRAWL_SCHEDULE_HOUR,
        ),
    }
}


@app.task(bind=True)
def schedule_daily_crawls(self):
    """Enqueue one crawl task per (active profile x source)."""
    db = SessionLocal()

    try:
        active_profiles = db.query(SearchProfile).filter_by(is_active=True).all()
        sources = settings.crawl_sources
        queued = 0

        for profile in active_profiles:
            for source_name in sources:
                crawl_profile_source.delay(str(profile.id), source_name)
                queued += 1

        print(f"[scheduler] queued {queued} crawl tasks for {len(active_profiles)} active profiles")
        return {
            "status": "completed",
            "active_profiles": len(active_profiles),
            "sources": sources,
            "queued_tasks": queued,
        }
    finally:
        db.close()


@app.task(bind=True)
def crawl_profile_source(self, profile_id: str, source_name: str):
    """
    Crawl a source for listings matching a profile.
    """
    print(f"[{source_name}] Starting crawl for profile {profile_id}")

    try:
        adapter = get_adapter(source_name)

        # Execute search
        raw_listings = adapter.search({"profile_id": profile_id})
        print(f"[{source_name}] Found {len(raw_listings)} listings")

        # Parse listings
        normalized = []
        for raw in raw_listings:
            parsed = adapter.parse(raw)
            normalized.append(parsed)

        inserted, updated, skipped = persist_listings(adapter.name, normalized)

        return {
            "status": "completed",
            "source": source_name,
            "profile_id": profile_id,
            "listings_found": len(normalized),
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
        }

    except Exception as e:
        print(f"[{source_name}] Error: {e}")
        return {
            "status": "failed",
            "source": source_name,
            "error": str(e),
        }
