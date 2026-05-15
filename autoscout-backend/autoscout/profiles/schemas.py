from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

_CURRENT_YEAR = datetime.date.today().year


class SearchProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    make: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    year_min: Optional[int] = Field(None, ge=1960, le=_CURRENT_YEAR + 1)
    year_max: Optional[int] = Field(None, ge=1960, le=_CURRENT_YEAR + 1)
    price_min: Optional[Decimal] = Field(None, ge=0)
    price_max: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field("EUR", pattern="^(EUR|ALL)$")
    mileage_max: Optional[int] = Field(None, ge=0)
    location_lat: Optional[float] = Field(None, ge=-90, le=90)
    location_lng: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[int] = Field(None, ge=1, le=200)
    body_type: Optional[str] = Field(None, max_length=50)
    transmission: Optional[str] = Field(None, max_length=50)
    fuel_type: Optional[str] = Field(None, max_length=50)
    free_text_criteria: Optional[str] = None
    delivery_time_local: int = Field(8, ge=0, le=23)
    timezone: str = Field("Europe/Tirane", max_length=64)
    is_active: bool = True

    @model_validator(mode="after")
    def check_ranges(self) -> "SearchProfileBase":
        if self.year_min and self.year_max and self.year_min > self.year_max:
            raise ValueError("year_min must be <= year_max")
        if self.price_min and self.price_max and self.price_min > self.price_max:
            raise ValueError("price_min must be <= price_max")
        return self


class SearchProfileCreate(SearchProfileBase):
    pass


class SearchProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    make: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    year_min: Optional[int] = Field(None, ge=1960, le=_CURRENT_YEAR + 1)
    year_max: Optional[int] = Field(None, ge=1960, le=_CURRENT_YEAR + 1)
    price_min: Optional[Decimal] = Field(None, ge=0)
    price_max: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, pattern="^(EUR|ALL)$")
    mileage_max: Optional[int] = Field(None, ge=0)
    location_lat: Optional[float] = Field(None, ge=-90, le=90)
    location_lng: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[int] = Field(None, ge=1, le=200)
    body_type: Optional[str] = Field(None, max_length=50)
    transmission: Optional[str] = Field(None, max_length=50)
    fuel_type: Optional[str] = Field(None, max_length=50)
    free_text_criteria: Optional[str] = None
    delivery_time_local: Optional[int] = Field(None, ge=0, le=23)
    timezone: Optional[str] = Field(None, max_length=64)
    is_active: Optional[bool] = None


class SearchProfileRead(SearchProfileBase):
    id: UUID
    user_id: UUID
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class ParseRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=2000)


class ParseResponse(BaseModel):
    profile: SearchProfileCreate
    needs_review: bool
    low_confidence_fields: list[str]
