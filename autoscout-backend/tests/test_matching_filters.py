"""Tests for matching/filters.py — hard bounds, geo filter, haversine."""
from __future__ import annotations

import pytest

from autoscout.matching.filters import (
    _haversine_km,
    _listing_coords,
    _passes_geo_filter,
    _passes_hard_bounds,
)
from tests.conftest import make_listing, make_profile


# ── Haversine ─────────────────────────────────────────────────────────────────

def test_haversine_same_point():
    assert _haversine_km(41.33, 19.82, 41.33, 19.82) == pytest.approx(0.0, abs=0.01)


def test_haversine_tirana_to_durres():
    # Tirana → Durrës is ~33 km
    dist = _haversine_km(41.33, 19.82, 41.32, 19.45)
    assert 30 <= dist <= 38


def test_haversine_tirana_to_saranda():
    # Tirana → Sarandë is ~200 km
    dist = _haversine_km(41.33, 19.82, 39.88, 20.00)
    assert 160 <= dist <= 220


# ── City coordinate lookup ────────────────────────────────────────────────────

def test_listing_coords_known_city():
    coords = _listing_coords("Tiranë")
    assert coords is not None
    lat, lon = coords
    assert 41.0 <= lat <= 42.0
    assert 19.0 <= lon <= 20.5


def test_listing_coords_alias():
    assert _listing_coords("tirana") == _listing_coords("Tiranë")
    assert _listing_coords("durres") == _listing_coords("Durrës")


def test_listing_coords_city_in_text():
    # City name embedded in longer text
    coords = _listing_coords("Shitet makina, Tiranë, afër qendrës")
    assert coords is not None


def test_listing_coords_unknown_city():
    assert _listing_coords("Unknown City XYZ") is None


def test_listing_coords_none():
    assert _listing_coords(None) is None


def test_listing_coords_empty():
    assert _listing_coords("") is None


# ── Geo filter ────────────────────────────────────────────────────────────────

def test_geo_filter_no_profile_location():
    profile = make_profile(location_lat=None, location_lng=None, radius_km=None)
    listing = make_listing(location_text="Tiranë")
    assert _passes_geo_filter(listing, profile) is True


def test_geo_filter_within_radius():
    # Profile in Tirana, radius 50km — Durrës (~33km) should pass
    profile = make_profile(location_lat=41.33, location_lng=19.82, radius_km=50)
    listing = make_listing(location_text="Durrës")
    assert _passes_geo_filter(listing, profile) is True


def test_geo_filter_outside_radius():
    # Profile in Tirana, radius 50km — Sarandë (~200km) should fail
    profile = make_profile(location_lat=41.33, location_lng=19.82, radius_km=50)
    listing = make_listing(location_text="Sarandë")
    assert _passes_geo_filter(listing, profile) is False


def test_geo_filter_unknown_location_passes():
    # Listings with unrecognised location are kept (LLM will score them lower)
    profile = make_profile(location_lat=41.33, location_lng=19.82, radius_km=50)
    listing = make_listing(location_text="Some Unknown Village")
    assert _passes_geo_filter(listing, profile) is True


def test_geo_filter_no_listing_location_passes():
    profile = make_profile(location_lat=41.33, location_lng=19.82, radius_km=50)
    listing = make_listing(location_text=None)
    assert _passes_geo_filter(listing, profile) is True


# ── Hard bounds ───────────────────────────────────────────────────────────────

def test_hard_bounds_passes_all():
    profile = make_profile(year_min=2017, year_max=2021, price_max=12000, mileage_max=150000)
    listing = make_listing(year=2019, price="9800", mileage=72000)
    assert _passes_hard_bounds(listing, profile) is True


def test_hard_bounds_year_too_old():
    profile = make_profile(year_min=2017)
    listing = make_listing(year=2010)
    assert _passes_hard_bounds(listing, profile) is False


def test_hard_bounds_year_too_new():
    profile = make_profile(year_max=2020)
    listing = make_listing(year=2023)
    assert _passes_hard_bounds(listing, profile) is False


def test_hard_bounds_year_at_boundary():
    profile = make_profile(year_min=2017, year_max=2021)
    assert _passes_hard_bounds(make_listing(year=2017), profile) is True
    assert _passes_hard_bounds(make_listing(year=2021), profile) is True


def test_hard_bounds_price_too_high():
    profile = make_profile(price_max=12000)
    listing = make_listing(price="15000")
    assert _passes_hard_bounds(listing, profile) is False


def test_hard_bounds_price_too_low():
    profile = make_profile(price_min=5000)
    listing = make_listing(price="3000")
    assert _passes_hard_bounds(listing, profile) is False


def test_hard_bounds_price_at_ceiling_passes():
    profile = make_profile(price_max=12000)
    listing = make_listing(price="12000")
    assert _passes_hard_bounds(listing, profile) is True


def test_hard_bounds_unparseable_price_passes():
    profile = make_profile(price_max=12000)
    listing = make_listing(price="negotiable")
    assert _passes_hard_bounds(listing, profile) is True


def test_hard_bounds_mileage_too_high():
    profile = make_profile(mileage_max=150000)
    listing = make_listing(mileage=200000)
    assert _passes_hard_bounds(listing, profile) is False


def test_hard_bounds_mileage_at_limit_passes():
    profile = make_profile(mileage_max=150000)
    listing = make_listing(mileage=150000)
    assert _passes_hard_bounds(listing, profile) is True


def test_hard_bounds_transmission_mismatch():
    profile = make_profile(transmission="manual")
    listing = make_listing(transmission="automatic")
    assert _passes_hard_bounds(listing, profile) is False


def test_hard_bounds_transmission_match():
    profile = make_profile(transmission="manual")
    listing = make_listing(transmission="manual")
    assert _passes_hard_bounds(listing, profile) is True


def test_hard_bounds_transmission_unknown_listing_passes():
    # If listing doesn't specify transmission, don't filter it out
    profile = make_profile(transmission="manual")
    listing = make_listing(transmission=None)
    assert _passes_hard_bounds(listing, profile) is True


def test_hard_bounds_fuel_type_mismatch():
    profile = make_profile(fuel_type="diesel")
    listing = make_listing(fuel_type="petrol")
    assert _passes_hard_bounds(listing, profile) is False


def test_hard_bounds_fuel_type_case_insensitive():
    profile = make_profile(fuel_type="Diesel")
    listing = make_listing(fuel_type="diesel")
    assert _passes_hard_bounds(listing, profile) is True


def test_hard_bounds_body_type_mismatch():
    profile = make_profile(body_type="convertible")
    listing = make_listing(body_type="hatchback")
    assert _passes_hard_bounds(listing, profile) is False


def test_hard_bounds_no_profile_constraints_passes_all():
    profile = make_profile(
        year_min=None, year_max=None, price_min=None, price_max=None,
        mileage_max=None, transmission=None, fuel_type=None, body_type=None,
    )
    listing = make_listing(year=2005, price="1000", mileage=500000)
    assert _passes_hard_bounds(listing, profile) is True


def test_hard_bounds_missing_listing_values_skipped():
    profile = make_profile(year_min=2017, mileage_max=150000)
    # Listing without year or mileage should not be filtered
    listing = make_listing(year=None, mileage=None)
    assert _passes_hard_bounds(listing, profile) is True
