import logging
import json
import os
import sentry_sdk
import structlog
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from redis import Redis

from autoscout.settings import settings
from autoscout.db.session import get_db
from autoscout.db.models import Base, User
from autoscout.auth.firebase import verify_token
from autoscout.auth.schemas import UserResponse, AuthSyncRequest, AuthSyncResponse
from autoscout.auth.dependencies import get_current_user
from autoscout.profiles.router import router as profiles_router
from autoscout.matches.router import matches_router, profile_matches_router
from autoscout.listings.router import router as listings_router

# Initialize Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            sentry_sdk.integrations.fastapi.FastApiIntegration(),
        ],
        environment=settings.FASTAPI_ENV,
        traces_sample_rate=0.1,
    )

# Initialize structlog with JSON output
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

app = FastAPI(
    title="AutoScout Backend",
    version="0.1.0",
    description="AI-powered used car discovery via WhatsApp"
)

app.include_router(profiles_router)
app.include_router(profile_matches_router)
app.include_router(matches_router)
app.include_router(listings_router)

# Serve locally uploaded photos in development
_uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(_uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")

logger = structlog.get_logger(__name__)


# ============================================================================
# Health Checks
# ============================================================================

@app.get("/health")
async def health():
    """Health check with DB and Redis connectivity."""
    status = "ok"
    db_ok = False
    redis_ok = False

    try:
        db = next(get_db())
        db.execute("SELECT 1")
        db.close()
        db_ok = True
    except Exception as e:
        logger.error("db_health_check_failed", error=str(e))
        status = "degraded"

    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        redis_ok = True
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        status = "degraded"

    response = {
        "status": status,
        "db": db_ok,
        "redis": redis_ok,
        "environment": settings.FASTAPI_ENV
    }

    status_code = 200 if status == "ok" else 503
    return JSONResponse(response, status_code=status_code)


@app.get("/ready")
async def ready():
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        db.close()
        return JSONResponse({"ready": True})
    except Exception as e:
        logger.error(f"Ready check failed: {e}")
        return JSONResponse({"ready": False, "error": str(e)}, status_code=503)


# ============================================================================
# Authentication
# ============================================================================

@app.post("/auth/sync", response_model=AuthSyncResponse)
async def sync_user(request: AuthSyncRequest, db: Session = Depends(get_db)):
    """
    Sync user from Firebase to database.
    Called by mobile app after successful OTP verification.
    Verifies the Firebase token and extracts phone number from claims.
    """
    try:
        decoded = verify_token(request.firebase_token)
        phone_number = decoded.get("phone_number")

        if not phone_number:
            logger.warning("firebase_claims_missing_phone", token=request.firebase_token[:10])
            raise HTTPException(status_code=400, detail="Phone number not in token")

        user = db.query(User).filter(User.phone_number == phone_number).first()

        if not user:
            user = User(phone_number=phone_number, country="AL", locale="sq")
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info("user_created", user_id=str(user.id), phone=phone_number)
        else:
            logger.info("user_synced", user_id=str(user.id), phone=phone_number)

        return AuthSyncResponse(
            user_id=user.id,
            message="User synced"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("auth_sync_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Sync failed")


@app.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get current authenticated user.
    """
    user = db.query(User).filter(
        User.phone_number == current_user.get("phone_number")
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.from_orm(user)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "autoscout.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )


# ============================================================================
# Admin / QA endpoints (no auth for now — internal network only)
# ============================================================================

@app.post("/admin/profiles/{profile_id}/run-match-now", tags=["admin"])
def admin_run_match_now(profile_id: str, db: Session = Depends(get_db)):
    """Crawl all sources for this profile, then run the matching pipeline."""
    import os
    from autoscout.matching.pipeline import run_pipeline
    from autoscout.matching.worker import celery_app

    # Step 1: dispatch one crawl task per source and wait for each to finish
    sources = [s.strip() for s in os.getenv("CRAWL_SOURCES", "merrjep").split(",") if s.strip()]
    crawl_summaries = []
    for source in sources:
        try:
            result = celery_app.send_task(
                "crawler.worker.crawl_profile_source",
                args=[profile_id, source],
                queue="crawler",
            )
            crawl_summaries.append(result.get(timeout=60))
        except Exception as exc:
            crawl_summaries.append({"status": "error", "source": source, "error": str(exc)})

    # Step 2: run the matching pipeline against the freshly crawled listings
    pipeline_result = run_pipeline(profile_id, db=db)
    pipeline_result["crawl"] = crawl_summaries
    return pipeline_result


@app.get("/admin/costs/summary", tags=["admin"])
def admin_costs_summary(days: int = 1, db: Session = Depends(get_db)):
    """
    Summarise LLM token usage and estimated cost for the last `days` days.

    Pricing estimate: Claude Sonnet input $3/M tokens, output $15/M tokens.
    Cache read tokens billed at ~10% of input price.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from autoscout.db.models import LlmCall

    INPUT_PRICE_PER_M = 3.0
    OUTPUT_PRICE_PER_M = 15.0
    CACHE_READ_PRICE_PER_M = 0.30

    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            LlmCall.endpoint,
            func.sum(LlmCall.input_tokens).label("input_tokens"),
            func.sum(LlmCall.output_tokens).label("output_tokens"),
            func.count(LlmCall.id).label("calls"),
        )
        .filter(LlmCall.created_at >= since)
        .group_by(LlmCall.endpoint)
        .all()
    )

    breakdown = []
    total_cost = 0.0
    for row in rows:
        cost = (
            row.input_tokens / 1_000_000 * INPUT_PRICE_PER_M
            + row.output_tokens / 1_000_000 * OUTPUT_PRICE_PER_M
        )
        total_cost += cost
        breakdown.append(
            {
                "endpoint": row.endpoint,
                "calls": row.calls,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
                "estimated_cost_usd": round(cost, 4),
            }
        )

    budget_alert = total_cost > 50.0 * days
    return {
        "period_days": days,
        "total_estimated_cost_usd": round(total_cost, 4),
        "budget_alert": budget_alert,
        "breakdown": breakdown,
    }


@app.get("/admin/matches/{match_id}/debug", tags=["admin"])
def admin_match_debug(match_id: str, db: Session = Depends(get_db)):
    """Return full pipeline trace for a match (QA use)."""
    from sqlalchemy.orm import joinedload
    from autoscout.db.models import Match

    match = (
        db.query(Match)
        .options(joinedload(Match.listing))
        .filter(Match.id == match_id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    listing = match.listing
    return {
        "match_id": str(match.id),
        "profile_id": str(match.search_profile_id),
        "listing_id": str(match.listing_id),
        "score": match.relevance_score,
        "score_source": match.score_source,
        "selected_for_delivery": match.selected_for_delivery,
        "reasoning": match.llm_reasoning,
        "summary": match.summary,
        "delivery_status": match.delivery_status,
        "user_action": match.user_action,
        "created_at": str(match.created_at),
        "listing": {
            "title": listing.title,
            "make": listing.make,
            "model": listing.model,
            "year": listing.year,
            "price": listing.price,
            "currency": listing.currency,
            "mileage": listing.mileage,
            "location": listing.location_text,
            "source_url": listing.source_url,
        } if listing else None,
    }

