import logging
import json
import sentry_sdk
import structlog
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from redis import Redis

from autoscout.settings import settings
from autoscout.db.session import get_db
from autoscout.db.models import Base, User
from autoscout.auth.firebase import verify_token
from autoscout.auth.schemas import UserResponse, AuthSyncRequest, AuthSyncResponse
from autoscout.auth.dependencies import get_current_user
from autoscout.profiles.router import router as profiles_router

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
