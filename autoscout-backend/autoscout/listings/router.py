from __future__ import annotations

import uuid
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from autoscout.auth.dependencies import get_db_user
from autoscout.db.models import Listing, User
from autoscout.db.session import get_db
from autoscout.settings import settings

from .schemas import (
    ListingBrowseResponse,
    ListingCreate,
    ListingRead,
    ListingUpdate,
    PhotoConfirmRequest,
    PhotoDeleteRequest,
    PhotoUploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["listings"])

MAX_PHOTOS = 10
MAX_PROFILES_PER_LISTING = 50  # safety cap for immediate matching fanout


def _get_r2_client():
    import boto3
    endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def _get_owned_listing(listing_id: UUID, user: User, db: Session) -> Listing:
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your listing")
    return listing


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/listings", response_model=ListingRead, status_code=201)
def create_listing(
    body: ListingCreate,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> Listing:
    listing_uuid = uuid.uuid4()
    listing = Listing(
        id=listing_uuid,
        source_id="autoscout",
        source_listing_id=str(listing_uuid),
        seller_user_id=user.id,
        status="active",
        is_active=True,
        photo_urls=[],
        views_count=0,
        **body.model_dump(),
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)

    # Trigger immediate matching in the background
    try:
        from autoscout.matching.worker import match_new_listing
        match_new_listing.delay(str(listing.id))
    except Exception as exc:
        logger.warning("match_new_listing enqueue failed: %s", exc)

    logger.info("listing_created source=autoscout id=%s user=%s", listing.id, user.id)
    return listing


# ── Browse (public) ───────────────────────────────────────────────────────────

@router.get("/listings", response_model=ListingBrowseResponse)
def browse_listings(
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    year_min: Optional[int] = Query(None),
    year_max: Optional[int] = Query(None),
    price_min: Optional[float] = Query(None),
    price_max: Optional[float] = Query(None),
    mileage_max: Optional[int] = Query(None),
    fuel_type: Optional[str] = Query(None),
    transmission: Optional[str] = Query(None),
    body_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    cursor: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> ListingBrowseResponse:
    query = db.query(Listing).filter(
        Listing.source_id == "autoscout",
        Listing.status == "active",
        Listing.is_active.is_(True),
    )

    if make:
        query = query.filter(Listing.make.ilike(f"%{make}%"))
    if model:
        query = query.filter(Listing.model.ilike(f"%{model}%"))
    if year_min:
        query = query.filter(Listing.year >= year_min)
    if year_max:
        query = query.filter(Listing.year <= year_max)
    if mileage_max:
        query = query.filter(Listing.mileage <= mileage_max)
    if fuel_type:
        query = query.filter(Listing.fuel_type.ilike(fuel_type))
    if transmission:
        query = query.filter(Listing.transmission.ilike(transmission))
    if body_type:
        query = query.filter(Listing.body_type.ilike(body_type))
    if price_min is not None:
        query = query.filter(Listing.price.cast(db.bind.dialect.FLOAT) >= price_min)
    if price_max is not None:
        query = query.filter(Listing.price.cast(db.bind.dialect.FLOAT) <= price_max)

    # Cursor: ISO datetime string → only listings created before cursor
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            query = query.filter(Listing.created_at < cursor_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format")

    query = query.order_by(Listing.created_at.desc())
    rows = query.limit(limit + 1).all()

    has_more = len(rows) > limit
    listings = rows[:limit]
    next_cursor = listings[-1].created_at.isoformat() if has_more and listings else None

    return ListingBrowseResponse(
        listings=listings,
        has_more=has_more,
        next_cursor=next_cursor,
    )


# ── Detail (public) ───────────────────────────────────────────────────────────

@router.get("/listings/{listing_id}", response_model=ListingRead)
def get_listing(
    listing_id: UUID,
    db: Session = Depends(get_db),
) -> Listing:
    listing = db.query(Listing).filter(
        Listing.id == listing_id,
        Listing.source_id == "autoscout",
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Increment view count (best-effort, non-blocking)
    try:
        listing.views_count = (listing.views_count or 0) + 1
        db.commit()
    except Exception:
        db.rollback()

    return listing


# ── Edit (owner) ──────────────────────────────────────────────────────────────

@router.patch("/listings/{listing_id}", response_model=ListingRead)
def update_listing(
    listing_id: UUID,
    body: ListingUpdate,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> Listing:
    listing = _get_owned_listing(listing_id, user, db)

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(listing, field, value)

    if updates.get("status") in ("sold", "removed"):
        listing.is_active = False

    db.commit()
    db.refresh(listing)
    return listing


# ── Delete (owner) ────────────────────────────────────────────────────────────

@router.delete("/listings/{listing_id}")
def delete_listing(
    listing_id: UUID,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> Response:
    listing = _get_owned_listing(listing_id, user, db)
    listing.status = "removed"
    listing.is_active = False
    db.commit()
    return Response(status_code=204)


# ── My listings (auth) ────────────────────────────────────────────────────────

@router.get("/me/listings", response_model=list[ListingRead])
def my_listings(
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> list[Listing]:
    return (
        db.query(Listing)
        .filter(Listing.seller_user_id == user.id)
        .order_by(Listing.created_at.desc())
        .all()
    )


# ── Photo upload ──────────────────────────────────────────────────────────────

@router.post("/listings/{listing_id}/photos", response_model=PhotoUploadResponse)
def get_photo_upload_url(
    listing_id: UUID,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> PhotoUploadResponse:
    listing = _get_owned_listing(listing_id, user, db)

    current_photos = listing.photo_urls or []
    if len(current_photos) >= MAX_PHOTOS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_PHOTOS} photos per listing")

    if not settings.R2_ACCOUNT_ID:
        raise HTTPException(status_code=503, detail="Photo storage not configured")

    photo_key = f"listings/{listing_id}/{uuid.uuid4()}.jpg"
    final_url = f"{settings.R2_PUBLIC_URL}/{photo_key}"

    try:
        s3 = _get_r2_client()
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.R2_BUCKET_NAME,
                "Key": photo_key,
                "ContentType": "image/jpeg",
            },
            ExpiresIn=600,  # 10 minutes
        )
    except Exception as exc:
        logger.error("r2_presign_failed listing=%s error=%s", listing_id, exc)
        raise HTTPException(status_code=502, detail="Could not generate upload URL")

    return PhotoUploadResponse(upload_url=upload_url, final_url=final_url)


@router.post("/listings/{listing_id}/photos/confirm", response_model=ListingRead)
def confirm_photo_upload(
    listing_id: UUID,
    body: PhotoConfirmRequest,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> Listing:
    listing = _get_owned_listing(listing_id, user, db)

    current = list(listing.photo_urls or [])
    if body.url not in current:
        current.append(body.url)
    listing.photo_urls = current
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/listings/{listing_id}/photos")
def remove_photo(
    listing_id: UUID,
    body: PhotoDeleteRequest,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> Response:
    listing = _get_owned_listing(listing_id, user, db)

    listing.photo_urls = [u for u in (listing.photo_urls or []) if u != body.url]
    db.commit()
    return Response(status_code=204)


# ── Local dev upload (no R2 needed) ──────────────────────────────────────────

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")


@router.post("/listings/{listing_id}/photos/upload", response_model=ListingRead)
async def upload_photo_local(
    listing_id: UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> Listing:
    """Multipart upload directly to the backend filesystem. Used in development when R2 is not configured."""
    listing = _get_owned_listing(listing_id, user, db)

    current_photos = listing.photo_urls or []
    if len(current_photos) >= MAX_PHOTOS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_PHOTOS} photos per listing")

    dest_dir = os.path.join(UPLOADS_DIR, "listings", str(listing_id))
    os.makedirs(dest_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}.jpg"
    dest_path = os.path.join(dest_dir, filename)

    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    final_url = f"{base_url}/uploads/listings/{listing_id}/{filename}"

    listing.photo_urls = list(current_photos) + [final_url]
    db.commit()
    db.refresh(listing)

    logger.info("photo_uploaded_local listing=%s url=%s", listing_id, final_url)
    return listing
