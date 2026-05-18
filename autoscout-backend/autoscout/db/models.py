import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Float, Text, Numeric, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

def _now():
    return datetime.now(timezone.utc)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    whatsapp_opt_in = Column(Boolean, default=False)
    country = Column(String(2), default="AL")
    locale = Column(String(10), default="sq")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    search_profiles = relationship("SearchProfile", back_populates="user", cascade="all, delete-orphan")


class SearchProfile(Base):
    __tablename__ = "search_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    make = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    year_min = Column(Integer, nullable=True)
    year_max = Column(Integer, nullable=True)
    price_min = Column(Numeric(12, 2), nullable=True)
    price_max = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), default='EUR')
    mileage_max = Column(Integer, nullable=True)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    radius_km = Column(Integer, nullable=True)
    body_type = Column(String(50), nullable=True)
    transmission = Column(String(50), nullable=True)
    fuel_type = Column(String(50), nullable=True)
    free_text_criteria = Column(Text, nullable=True)
    delivery_time_local = Column(Integer, default=8)
    timezone = Column(String(64), default='Europe/Tirane')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("User", back_populates="search_profiles")
    matches = relationship("Match", back_populates="search_profile", cascade="all, delete-orphan")


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("source_id", "source_listing_id", name="uq_listings_source_listing"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String(50), nullable=False, index=True)
    source_listing_id = Column(String(255), nullable=False)
    source_url = Column(String(500))
    title = Column(String(500))
    description = Column(String(2000))
    make = Column(String(100))
    model = Column(String(100))
    year = Column(Integer)
    mileage = Column(Integer)
    price = Column(String(50))
    currency = Column(String(3), default="EUR")
    location_text = Column(String(255))
    transmission = Column(String(50), nullable=True)
    fuel_type = Column(String(50), nullable=True)
    body_type = Column(String(50), nullable=True)
    seller_name = Column(String(255))
    raw_payload = Column(JSONB, nullable=True)
    dedup_hash = Column(String(255), index=True)
    first_seen_at = Column(DateTime, default=_now)
    last_seen_at = Column(DateTime, default=_now, onupdate=_now)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)

    # Platform listing fields (source_id = 'autoscout')
    seller_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="active")
    photo_urls = Column(JSONB, nullable=False, default=list)
    contact_phone = Column(String(30), nullable=True)
    views_count = Column(Integer, nullable=False, default=0)

    seller = relationship("User", foreign_keys=[seller_user_id])


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    endpoint = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_now)


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("search_profile_id", "listing_id", name="uq_matches_profile_listing"),
        Index("ix_matches_profile_delivered_at", "search_profile_id", "delivered_at"),
        Index("ix_matches_profile_created_at", "search_profile_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_profile_id = Column(UUID(as_uuid=True), ForeignKey("search_profiles.id"), nullable=False, index=True)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False, index=True)
    relevance_score = Column(Integer)
    score_source = Column(String(20), default="llm")  # 'llm' | 'fallback' | 'tiebreaker'
    llm_reasoning = Column(Text)
    summary = Column(Text)  # short blurb for WhatsApp card
    selected_for_delivery = Column(Boolean, default=False, nullable=False)
    delivered_at = Column(DateTime)
    delivery_channel = Column(String(50))  # 'whatsapp'
    delivery_status = Column(String(50), default="pending")
    user_action = Column(String(50))  # 'clicked' | 'dismissed' | 'saved'
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    search_profile = relationship("SearchProfile", back_populates="matches")
    listing = relationship("Listing")
