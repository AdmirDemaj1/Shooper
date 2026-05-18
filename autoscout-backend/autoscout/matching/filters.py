"""Strict filter + geo filter + already-seen suppression for the matching pipeline."""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from autoscout.db.models import Listing, Match, SearchProfile

if TYPE_CHECKING:
    pass


# ── Albanian city coordinate lookup ─────────────────────────────────────────
# Used for geo filtering when listings only have location_text.
_CITY_COORDS: dict[str, tuple[float, float]] = {
    # key: lowercase normalized city name → (lat, lon)
    "tiranë": (41.33, 19.82),
    "tirana": (41.33, 19.82),
    "tirane": (41.33, 19.82),
    "durrës": (41.32, 19.45),
    "durres": (41.32, 19.45),
    "durr\u00ebs": (41.32, 19.45),
    "vlorë": (40.47, 19.49),
    "vlore": (40.47, 19.49),
    "vlora": (40.47, 19.49),
    "shkodër": (42.07, 19.51),
    "shkoder": (42.07, 19.51),
    "fier": (40.72, 19.56),
    "korçë": (40.62, 20.78),
    "korce": (40.62, 20.78),
    "korca": (40.62, 20.78),
    "elbasan": (41.11, 20.08),
    "berat": (40.71, 19.95),
    "lushnjë": (40.94, 19.70),
    "lushnje": (40.94, 19.70),
    "kavajë": (41.19, 19.56),
    "kavaje": (41.19, 19.56),
    "gjirokastër": (40.07, 20.14),
    "gjirokaster": (40.07, 20.14),
    "sarandë": (39.88, 20.00),
    "sarande": (39.88, 20.00),
    "lezhë": (41.78, 19.64),
    "lezhe": (41.78, 19.64),
    "kukës": (42.07, 20.42),
    "kukes": (42.07, 20.42),
    "pogradec": (40.90, 20.66),
    "patos": (40.68, 19.62),
    "laç": (41.63, 19.71),
    "lac": (41.63, 19.71),
    "krujë": (41.51, 19.79),
    "kruje": (41.51, 19.79),
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _listing_coords(location_text: str | None) -> tuple[float, float] | None:
    """Return (lat, lon) for a listing's location_text, or None if unrecognised."""
    if not location_text:
        return None
    text = location_text.lower().replace(",", " ")
    for city, coords in _CITY_COORDS.items():
        if city in text:
            return coords
    return None


def _passes_geo_filter(listing: Listing, profile: SearchProfile) -> bool:
    """
    Return True if the listing is within the profile's radius.

    Rules:
    - If the profile has no location set, skip geo filtering (pass all).
    - If the listing has no recognisable city, keep it (flag as location_uncertain
      for the LLM to consider).
    - Otherwise apply haversine distance check.
    """
    if not profile.location_lat or not profile.location_lng or not profile.radius_km:
        return True

    coords = _listing_coords(listing.location_text)
    if coords is None:
        return True  # location_uncertain — LLM will assess

    dist = _haversine_km(profile.location_lat, profile.location_lng, coords[0], coords[1])
    return dist <= profile.radius_km


def get_candidate_listings(
    db: Session,
    profile: SearchProfile,
    hours_lookback: int = 48,
) -> list[Listing]:
    """
    Return listings that:
    1. Were seen within the last `hours_lookback` hours (recently crawled).
    2. Pass strict hard bounds (price, year, mileage, body_type, transmission, fuel_type).
    3. Pass geo filter (within profile radius).
    4. Have NOT been matched to this profile in the last 30 days.
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours_lookback)
    seen_cutoff = datetime.utcnow() - timedelta(days=30)

    # IDs already matched (30-day cool-down)
    already_seen_ids: set = {
        row[0]
        for row in db.query(Match.listing_id)
        .filter(
            Match.search_profile_id == profile.id,
            Match.created_at >= seen_cutoff,
        )
        .all()
    }

    # Recent active listings
    listings = (
        db.query(Listing)
        .filter(
            Listing.is_active == True,  # noqa: E712
            Listing.last_seen_at >= cutoff,
        )
        .all()
    )

    return [
        listing
        for listing in listings
        if (
            listing.id not in already_seen_ids
            and _passes_hard_bounds(listing, profile)
            and _passes_geo_filter(listing, profile)
        )
    ]


def _passes_hard_bounds(listing: Listing, profile: SearchProfile) -> bool:
    """Return True if listing is within all of the profile's hard numeric bounds."""
    # Year
    if listing.year:
        if profile.year_min and listing.year < profile.year_min:
            return False
        if profile.year_max and listing.year > profile.year_max:
            return False

    # Mileage
    if listing.mileage and profile.mileage_max:
        if listing.mileage > profile.mileage_max:
            return False

    # Price — stored as string (e.g. "8900"); parse gracefully
    if listing.price:
        try:
            price = float(listing.price)
            if profile.price_min and price < float(profile.price_min):
                return False
            if profile.price_max and price > float(profile.price_max):
                return False
        except (ValueError, TypeError):
            pass  # unparseable price → keep listing (LLM will assess)

    # Transmission — only filter when both sides are known
    if profile.transmission and listing.transmission:
        if listing.transmission.lower() != profile.transmission.lower():
            return False

    # Fuel type
    if profile.fuel_type and listing.fuel_type:
        if listing.fuel_type.lower() != profile.fuel_type.lower():
            return False

    # Body type
    if profile.body_type and listing.body_type:
        if listing.body_type.lower() != profile.body_type.lower():
            return False

    return True

