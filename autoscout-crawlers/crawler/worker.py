import os
from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery("autoscout")
app.conf.broker_url = redis_url
app.conf.result_backend = redis_url
app.conf.task_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.result_serializer = "json"
app.conf.timezone = "UTC"


@app.task(bind=True)
def crawl_profile_source(self, profile_id: str, source_name: str):
    """
    Crawl a source for listings matching a profile.
    """
    print(f"[{source_name}] Starting crawl for profile {profile_id}")

    try:
        from crawler.sources.merrjep import MerrjepAdapter

        if source_name == "merrjep":
            adapter = MerrjepAdapter()
        else:
            raise ValueError(f"Unknown source: {source_name}")

        # Execute search
        raw_listings = adapter.search({"profile_id": profile_id})
        print(f"[{source_name}] Found {len(raw_listings)} listings")

        # Parse listings
        normalized = []
        for raw in raw_listings:
            parsed = adapter.parse(raw)
            normalized.append(parsed)

        return {
            "status": "completed",
            "source": source_name,
            "listings_found": len(normalized),
            "listings": normalized,
        }

    except Exception as e:
        print(f"[{source_name}] Error: {e}")
        return {
            "status": "failed",
            "source": source_name,
            "error": str(e),
        }
