import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


def _now():
    return datetime.now(timezone.utc)


Base = declarative_base()


class SearchProfile(Base):
    __tablename__ = "search_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    make = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    year_min = Column(Integer, nullable=True)
    year_max = Column(Integer, nullable=True)
    price_min = Column(Numeric(12, 2), nullable=True)
    price_max = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), default="EUR")
    mileage_max = Column(Integer, nullable=True)
    transmission = Column(String(50), nullable=True)
    fuel_type = Column(String(50), nullable=True)
    radius_km = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)


class Listing(Base):
    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String(50), nullable=False, index=True)
    source_listing_id = Column(String(255), nullable=False)
    source_url = Column(String(500), nullable=True)
    title = Column(String(500), nullable=True)
    description = Column(String(2000), nullable=True)
    make = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)
    mileage = Column(Integer, nullable=True)
    price = Column(String(50), nullable=True)
    currency = Column(String(3), default="EUR")
    location_text = Column(String(255), nullable=True)
    seller_name = Column(String(255), nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    dedup_hash = Column(String(255), index=True)
    first_seen_at = Column(DateTime, default=_now)
    last_seen_at = Column(DateTime, default=_now, onupdate=_now)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)
