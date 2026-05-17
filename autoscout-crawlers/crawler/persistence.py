import hashlib
from datetime import datetime, timezone
from typing import Any

from crawler.db import SessionLocal
from crawler.models import Listing

# Canonical make names — keys are lowercase variants found in real listings
_MAKE_CANON: dict[str, str] = {
    "vw": "Volkswagen",
    "volkswagen": "Volkswagen",
    "volks": "Volkswagen",
    "mercedes": "Mercedes-Benz",
    "mercedes-benz": "Mercedes-Benz",
    "merc": "Mercedes-Benz",
    "mb": "Mercedes-Benz",
    "bmw": "BMW",
    "audi": "Audi",
    "opel": "Opel",
    "vauxhall": "Opel",
    "renault": "Renault",
    "peugeot": "Peugeot",
    "fiat": "Fiat",
    "ford": "Ford",
    "toyota": "Toyota",
    "honda": "Honda",
    "hyundai": "Hyundai",
    "kia": "Kia",
    "skoda": "Skoda",
    "seat": "Seat",
    "mazda": "Mazda",
    "nissan": "Nissan",
    "mitsubishi": "Mitsubishi",
    "suzuki": "Suzuki",
    "citroen": "Citroën",
    "citroën": "Citroën",
    "alfa": "Alfa Romeo",
    "alfa romeo": "Alfa Romeo",
    "landrover": "Land Rover",
    "land rover": "Land Rover",
    "jeep": "Jeep",
    "volvo": "Volvo",
    "porsche": "Porsche",
    "subaru": "Subaru",
    "chevrolet": "Chevrolet",
    "dacia": "Dacia",
    "lancia": "Lancia",
}


def canonicalize_make(make: str | None) -> str | None:
    if not make:
        return make
    return _MAKE_CANON.get(make.strip().lower(), make)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def compute_dedup_hash(listing: dict[str, Any]) -> str:
    """
    Build a deterministic hash for deduplication.

    We prioritize source id + source_listing_id when present, and otherwise fall
    back to a canonical tuple used for cross-source approximate dedup in Sprint 3.
    """
    source = (listing.get("source") or "").strip().lower()
    source_listing_id = (listing.get("source_listing_id") or "").strip().lower()

    if source and source_listing_id:
        key = f"{source}:{source_listing_id}"
    else:
        price = str(listing.get("price") or "").strip().lower()
        mileage = str(listing.get("mileage") or "").strip().lower()
        year = str(listing.get("year") or "").strip().lower()
        make = str(listing.get("make") or "").strip().lower()
        model = str(listing.get("model") or "").strip().lower()
        location = str(listing.get("location_text") or "").strip().lower()
        key = "|".join([make, model, year, price, mileage, location])

    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def persist_listings(source_name: str, listings: list[dict[str, Any]]) -> tuple[int, int, int]:
    """
    Persist listings with idempotent upsert-like semantics.

    Returns (inserted, updated, skipped).
    """
    db = SessionLocal()
    inserted = 0
    updated = 0
    skipped = 0

    try:
        for parsed in listings:
            dedup_hash = compute_dedup_hash(parsed)

            existing = db.query(Listing).filter_by(
                source_id=source_name,
                source_listing_id=parsed.get("source_listing_id"),
            ).first()

            if not existing:
                existing = db.query(Listing).filter_by(dedup_hash=dedup_hash).first()

            if existing:
                existing.last_seen_at = _now()
                existing.is_active = True

                # Keep source identity stable if the exact listing already exists,
                # but refresh core mutable fields to reflect latest crawl data.
                existing.source_url = parsed.get("source_url") or existing.source_url
                existing.title = parsed.get("title") or existing.title
                existing.description = parsed.get("description") or existing.description
                existing.make = canonicalize_make(parsed.get("make")) or existing.make
                existing.model = parsed.get("model") or existing.model
                existing.year = parsed.get("year") or existing.year
                existing.mileage = parsed.get("mileage") or existing.mileage
                existing.price = parsed.get("price") or existing.price
                existing.currency = parsed.get("currency") or existing.currency
                existing.location_text = parsed.get("location_text") or existing.location_text
                existing.raw_payload = parsed
                existing.dedup_hash = dedup_hash
                updated += 1
                continue

            listing = Listing(
                source_id=source_name,
                source_listing_id=parsed.get("source_listing_id"),
                source_url=parsed.get("source_url"),
                title=parsed.get("title"),
                description=parsed.get("description"),
                make=canonicalize_make(parsed.get("make")),
                model=parsed.get("model"),
                year=parsed.get("year"),
                mileage=parsed.get("mileage"),
                price=parsed.get("price"),
                currency=parsed.get("currency") or "EUR",
                location_text=parsed.get("location_text"),
                dedup_hash=dedup_hash,
                raw_payload=parsed,
                is_active=True,
                first_seen_at=_now(),
                last_seen_at=_now(),
            )
            db.add(listing)
            inserted += 1

        db.commit()
        return inserted, updated, skipped
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
