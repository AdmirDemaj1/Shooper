import argparse
import sys
from crawler.persistence import persist_listings
from crawler.sources.registry import get_adapter


def main():
    parser = argparse.ArgumentParser(description="AutoScout Crawler")
    parser.add_argument("--source", default="merrjep", help="Source to crawl")
    parser.add_argument("--profile", default="test", help="Profile ID to search for")
    args = parser.parse_args()

    print(f"Crawling {args.source} for profile {args.profile}...")

    try:
        adapter = get_adapter(args.source)

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
        inserted, updated, skipped = persist_listings(adapter.name, parsed_listings)
        print(f"✓ Inserted {inserted} new listings")
        if updated > 0:
            print(f"✓ Updated {updated} existing listings")
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
