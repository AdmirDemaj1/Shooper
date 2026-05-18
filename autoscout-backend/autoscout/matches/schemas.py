from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ListingSlim(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    title: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    price: Optional[str] = None
    currency: Optional[str] = None
    mileage: Optional[int] = None
    location_text: Optional[str] = None
    description: Optional[str] = None


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    search_profile_id: UUID
    listing_id: UUID
    relevance_score: Optional[int] = None
    score_source: Optional[str] = None
    llm_reasoning: Optional[str] = None
    summary: Optional[str] = None
    selected_for_delivery: bool = False
    delivery_status: str = "pending"
    user_action: Optional[str] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime
    listing: Optional[ListingSlim] = None


class MatchListResponse(BaseModel):
    matches: list[MatchRead]
    has_more: bool
    next_cursor: Optional[str] = None


class MatchActionRequest(BaseModel):
    action: str  # 'clicked' | 'dismissed' | 'saved'
