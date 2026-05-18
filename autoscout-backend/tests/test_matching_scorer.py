"""Tests for matching/scorer.py — deterministic fallback, profile hash, caching."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoscout.matching.scorer import (
    _default_summary,
    _deterministic_score,
    _listing_to_dict,
    _profile_hash,
    score_listings,
)
from tests.conftest import make_listing, make_profile


# ── Profile hash ──────────────────────────────────────────────────────────────

def test_profile_hash_is_16_chars():
    profile = make_profile()
    assert len(_profile_hash(profile)) == 16


def test_profile_hash_same_profile_same_hash():
    p1 = make_profile(make="BMW", model="3 Series", free_text_criteria="no accidents")
    p2 = make_profile(make="BMW", model="3 Series", free_text_criteria="no accidents")
    assert _profile_hash(p1) == _profile_hash(p2)


def test_profile_hash_different_criteria_different_hash():
    p1 = make_profile(free_text_criteria="single owner")
    p2 = make_profile(free_text_criteria="no accidents")
    assert _profile_hash(p1) != _profile_hash(p2)


def test_profile_hash_ignores_name_and_location():
    # Name and location don't affect LLM scoring — hash should be the same
    p1 = make_profile(name="Profile A", location_lat=41.33, location_lng=19.82)
    p2 = make_profile(name="Profile B", location_lat=40.47, location_lng=19.49)
    # Both have the same scoring-relevant fields
    p1.make = p2.make = "Toyota"
    p1.model = p2.model = "Yaris"
    p1.free_text_criteria = p2.free_text_criteria = "low mileage"
    p1.price_max = p2.price_max = 10000
    p1.year_min = p2.year_min = 2018
    p1.year_max = p2.year_max = 2023
    p1.mileage_max = p2.mileage_max = 100000
    p1.fuel_type = p2.fuel_type = None
    p1.transmission = p2.transmission = None
    assert _profile_hash(p1) == _profile_hash(p2)


# ── Deterministic score ───────────────────────────────────────────────────────

def test_deterministic_score_base():
    profile = make_profile()
    listing = make_listing(year=None, mileage=None, price=None, description=None)
    score = _deterministic_score(listing, profile)
    assert score == 60


def test_deterministic_score_new_car_bonus():
    profile = make_profile()
    score = _deterministic_score(make_listing(year=2024), profile)
    assert score >= 80  # base 60 + 20 for ≤3yo


def test_deterministic_score_old_car_penalty():
    profile = make_profile()
    # Clear mileage/description so only the year penalty applies
    score = _deterministic_score(make_listing(year=2005, mileage=None, description=None), profile)
    assert score <= 50  # base 60 - 15 for ≥15yo


def test_deterministic_score_low_mileage_bonus():
    profile = make_profile()
    score = _deterministic_score(make_listing(mileage=30000), profile)
    assert score >= 75  # base 60 + 15 for <50k


def test_deterministic_score_high_mileage_penalty():
    profile = make_profile()
    # Clear year/description so only the mileage penalty applies
    score = _deterministic_score(make_listing(mileage=250000, year=None, description=None), profile)
    assert score <= 50  # base 60 - 15 for >200k


def test_deterministic_score_price_well_under_budget():
    profile = make_profile(price_max=12000)
    score = _deterministic_score(make_listing(price="8000"), profile)
    assert score >= 70  # ratio 0.67 < 0.75 → +10


def test_deterministic_score_price_near_ceiling():
    profile = make_profile(price_max=12000)
    # Clear year/mileage/description so only the price penalty applies
    score = _deterministic_score(make_listing(price="11800", year=None, mileage=None, description=None), profile)
    assert score <= 60  # ratio ~0.98 > 0.95 → -5


def test_deterministic_score_description_bonus():
    profile = make_profile()
    long_desc = "x" * 100
    score_with = _deterministic_score(make_listing(description=long_desc), profile)
    score_without = _deterministic_score(make_listing(description=None), profile)
    assert score_with > score_without


def test_deterministic_score_clamped_to_0_100():
    # No matter the inputs, score must stay in [0, 100]
    profile = make_profile(price_max=1000)
    listing = make_listing(year=1980, mileage=999999, price="999", description=None)
    score = _deterministic_score(listing, profile)
    assert 0 <= score <= 100


# ── Default summary ───────────────────────────────────────────────────────────

def test_default_summary_full():
    listing = make_listing(year=2019, make="Volkswagen", model="Golf", price="9800", mileage=72000, location_text="Tiranë")
    summary = _default_summary(listing)
    assert "2019" in summary
    assert "Volkswagen" in summary
    assert "Golf" in summary
    assert "9800" in summary
    assert "72" in summary
    assert "Tiranë" in summary


def test_default_summary_minimal():
    listing = make_listing(year=None, make=None, model=None, price=None, mileage=None, location_text=None)
    summary = _default_summary(listing)
    assert isinstance(summary, str)  # must not raise


# ── Listing to dict ───────────────────────────────────────────────────────────

def test_listing_to_dict_keys():
    listing = make_listing()
    d = _listing_to_dict(listing)
    assert set(d.keys()) == {"id", "title", "make", "model", "year", "price", "currency", "mileage", "location", "description"}


def test_listing_to_dict_id_is_string():
    listing = make_listing()
    d = _listing_to_dict(listing)
    assert isinstance(d["id"], str)


# ── score_listings — cache hit path ──────────────────────────────────────────

def test_score_listings_empty_returns_empty():
    profile = make_profile()
    assert score_listings(profile, []) == []


def test_score_listings_uses_redis_cache():
    import json
    profile = make_profile()
    listing = make_listing()

    cached_score = {
        "listing_id": str(listing.id),
        "score": 90,
        "reasoning": "Cached.",
        "summary": "2019 VW Golf — €9,800",
        "score_source": "llm",
    }

    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps(cached_score)

    results = score_listings(profile, [listing], redis_client=mock_redis)

    assert len(results) == 1
    assert results[0]["score"] == 90
    assert results[0]["score_source"] == "llm"
    mock_redis.get.assert_called_once()


def test_score_listings_falls_back_on_llm_error():
    profile = make_profile()
    listing = make_listing()

    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # cache miss

    with patch("autoscout.matching.scorer._score_with_llm", side_effect=Exception("API down")):
        results = score_listings(profile, [listing], redis_client=mock_redis)

    assert len(results) == 1
    assert results[0]["score_source"] == "fallback"
    assert 0 <= results[0]["score"] <= 100


def test_score_listings_fallback_without_redis():
    profile = make_profile()
    listing = make_listing()

    with patch("autoscout.matching.scorer._score_with_llm", side_effect=Exception("API down")):
        results = score_listings(profile, [listing], redis_client=None)

    assert len(results) == 1
    assert results[0]["score_source"] == "fallback"
