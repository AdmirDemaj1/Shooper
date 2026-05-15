import argparse
import sys
import hashlib
import json
from crawler.sources.merrjep import MerrjepAdapter
from crawler.db import SessionLocal


def compute_dedup_hash(listing: dict) -> str:
    """Generate a dedup hash from source + listing_id."""
    key = f"{listing['source']}_{listing['source_listing_id']}"
    return hashlib.sha256(key.encode()).hexdigest()


def persist_listings(source_name: str, listings: list):
    """Persist parsed listings to the database."""
    # Import here to avoid issues when models aren't available
    import sys
    sys.path.insert(0, "/Users/admirdemaj/Desktop/Personal/Shooper/autoscout-backend")

    from autoscout.db.models import Listing

    db = SessionLocal()
    try:
        inserted = 0
        skipped = 0

        for parsed in listings:
            dedup_hash = compute_dedup_hash(parsed)

            # Check if listing already exists
            existing = db.query(Listing).filter_by(dedup_hash=dedup_hash).first()
            if existing:
                existing.last_seen_at = existing.first_seen_at  # Refresh timestamp
                skipped += 1
                continue

            # Insert new listing
            listing = Listing(
                source_id=source_name,
                source_listing_id=parsed['source_listing_id'],
                source_url=parsed['source_url'],
                title=parsed['title'],
                description=parsed.get('description'),
                make=parsed['make'],
                model=parsed['model'],
                year=parsed['year'],
                mileage=parsed['mileage'],
                price=parsed['price'],
                currency=parsed['currency'],
                location_text=parsed['location_text'],
                dedup_hash=dedup_hash,
                raw_payload=parsed,
            )
            db.add(listing)
            inserted += 1

        db.commit()
        return inserted, skipped
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="AutoScout Crawler")
    parser.add_argument("--source", default="merrjep", help="Source to crawl")
    parser.add_argument("--profile", default="test", help="Profile ID to search for")
    args = parser.parse_args()

    print(f"Crawling {args.source} for profile {args.profile}...")

    try:
        if args.source == "merrjep":
            adapter = MerrjepAdapter()
        else:
            print(f"Error: Unknown source {args.source}")
            sys.exit(1)

        # Execute search
        raw_listings = adapter.search({"profile_id": args.profile})
        print(f"Found {len(raw_listings)} listings from {adapter.name}\n")

        # Parse listings
        parsed_listings = []
        for i, raw in enumerate(raw_listings, 1):
            parsed = adapter.parse(raw)
            parsed_listings.append(parsed)
            print(f"{i}. {parsed['title']}")
            print(f"   Make: {parsed['make']} {parsed['model']} ({parsed['year']})")
            print(f"   Price: €{parsed['price']}")
            print(f"   Mileage: {parsed['mileage']:,} km")
            print(f"   Location: {parsed['location_text']}")
            print(f"   URL: {parsed['source_url']}")
            print()

        # Persist to database
        print(f"Persisting listings to database...")
        inserted, skipped = persist_listings(adapter.name, parsed_listings)
        print(f"✓ Inserted {inserted} new listings")
        if skipped > 0:
            print(f"✓ Skipped {skipped} duplicate listings")
        print(f"✓ Done!")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
