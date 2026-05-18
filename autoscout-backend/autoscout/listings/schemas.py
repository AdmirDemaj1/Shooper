from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class ListingCreate(BaseModel):
    title: str
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    price: Optional[str] = None
    currency: str = "EUR"
    mileage: Optional[int] = None
    location_text: Optional[str] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    body_type: Optional[str] = None
    description: Optional[str] = None
    contact_phone: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be blank")
        return v

    @field_validator("description")
    @classmethod
    def description_min_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) < 30:
            raise ValueError("description must be at least 30 characters")
        return v

    @field_validator("year")
    @classmethod
    def year_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1960 <= v <= 2030):
            raise ValueError("year must be between 1960 and 2030")
        return v

    @field_validator("currency")
    @classmethod
    def currency_valid(cls, v: str) -> str:
        if v not in ("EUR", "ALL"):
            raise ValueError("currency must be EUR or ALL")
        return v


class ListingUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[str] = None
    mileage: Optional[int] = None
    description: Optional[str] = None
    contact_phone: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("active", "sold", "removed"):
            raise ValueError("status must be active, sold, or removed")
        return v


class ListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seller_user_id: Optional[UUID] = None
    source_id: str
    source_url: Optional[str] = None
    title: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    price: Optional[str] = None
    currency: str
    mileage: Optional[int] = None
    location_text: Optional[str] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    body_type: Optional[str] = None
    description: Optional[str] = None
    contact_phone: Optional[str] = None
    photo_urls: list[str] = []
    status: str = "active"
    views_count: int = 0
    is_active: bool
    created_at: datetime


class ListingBrowseResponse(BaseModel):
    listings: list[ListingRead]
    has_more: bool
    next_cursor: Optional[str] = None


class PhotoUploadResponse(BaseModel):
    upload_url: str
    final_url: str


class PhotoConfirmRequest(BaseModel):
    url: str


class PhotoDeleteRequest(BaseModel):
    url: str
