import logging
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from autoscout.settings import settings
from autoscout.db.session import get_db, engine
from autoscout.db.models import Base, User
from autoscout.auth.firebase import verify_token
from autoscout.auth.schemas import UserResponse, AuthSyncRequest, AuthSyncResponse

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AutoScout Backend",
    version="0.1.0",
    description="AI-powered used car discovery via WhatsApp"
)

logger = logging.getLogger(__name__)


# ============================================================================
# Health Checks
# ============================================================================

@app.get("/health")
async def health():
    return JSONResponse({
        "status": "ok",
        "environment": settings.FASTAPI_ENV
    })


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

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        token = authorization.replace("Bearer ", "")
        decoded = verify_token(token)
        if not decoded:
            raise HTTPException(status_code=401, detail="Invalid token")
        return decoded
    except Exception as e:
        logger.error(f"Auth failed: {e}")
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/auth/sync", response_model=AuthSyncResponse)
async def sync_user(request: AuthSyncRequest, db: Session = Depends(get_db)):
    """
    Sync user from Firebase to database.
    Called by mobile app after successful OTP verification.
    """
    phone_number = request.phone_number

    user = db.query(User).filter(User.phone_number == phone_number).first()

    if not user:
        user = User(phone_number=phone_number, country="AL", locale="sq")
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user: {user.id}")

    return AuthSyncResponse(
        user_id=user.id,
        message="User synced"
    )


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
