import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    whatsapp_opt_in = Column(Boolean, default=False)
    country = Column(String(2), default="AL")
    locale = Column(String(10), default="sq")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SearchProfile(Base):
    __tablename__ = "search_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Listing(Base):
    __tablename__ = "listings"

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
    seller_name = Column(String(255))
    raw_payload = Column(String)  # JSON as string for now
    dedup_hash = Column(String(255), index=True)
    first_seen_at = Column(DateTime, server_default=func.now())
    last_seen_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Match(Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_profile_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    listing_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    relevance_score = Column(Integer)
    llm_reasoning = Column(String(1000))
    delivered_at = Column(DateTime)
    delivery_status = Column(String(50), default="pending")
    created_at = Column(DateTime, server_default=func.now())
