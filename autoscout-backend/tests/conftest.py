"""Shared test fixtures for AutoScout backend tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from autoscout.db.models import Listing, Match, SearchProfile, User


# ── Model factories ───────────────────────────────────────────────────────────

def make_user(**kwargs) -> User:
    defaults = dict(
        id=uuid.uuid4(),
        phone_number="+355691234567",
        whatsapp_opt_in=False,
        country="AL",
        locale="sq",
        created_at=datetime.now(timezone.utc),
    )
    return User(**{**defaults, **kwargs})


def make_profile(**kwargs) -> SearchProfile:
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Test Profile",
        make="Volkswagen",
        model="Golf",
        year_min=2017,
        year_max=2021,
        price_min=None,
        price_max=12000,
        currency="EUR",
        mileage_max=150000,
        location_lat=41.33,
        location_lng=19.82,
        radius_km=50,
        body_type=None,
        transmission=None,
        fuel_type=None,
        free_text_criteria="single owner, no accidents",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    return SearchProfile(**{**defaults, **kwargs})


def make_listing(**kwargs) -> Listing:
    defaults = dict(
        id=uuid.uuid4(),
        source_id="merrjep",
        source_listing_id=str(uuid.uuid4()),
        source_url="https://merrjep.al/listing/1",
        title="VW Golf 7 2019",
        make="Volkswagen",
        model="Golf",
        year=2019,
        price="9800",
        currency="EUR",
        mileage=72000,
        location_text="Tiranë",
        transmission="manual",
        fuel_type="petrol",
        body_type="hatchback",
        description="Single owner, full history.",
        is_active=True,
        last_seen_at=datetime.now(timezone.utc),
        first_seen_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    return Listing(**{**defaults, **kwargs})


def make_match(**kwargs) -> Match:
    defaults = dict(
        id=uuid.uuid4(),
        search_profile_id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        relevance_score=82,
        score_source="llm",
        llm_reasoning="Matches all criteria.",
        summary="2019 VW Golf 7 — €9,800 · 72 000 km · Tiranë",
        selected_for_delivery=True,
        delivery_status="pending",
        user_action=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return Match(**{**defaults, **kwargs})


# ── Mock DB session ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """A MagicMock that looks enough like a SQLAlchemy Session for unit tests."""
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.all.return_value = []
    db.first.return_value = None
    return db
