import argparse
import sys
from crawler.sources.merrjep import MerrjepAdapter


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

        # Parse and display
        for i, raw in enumerate(raw_listings, 1):
            parsed = adapter.parse(raw)
            print(f"{i}. {parsed['title']}")
            print(f"   Make: {parsed['make']} {parsed['model']} ({parsed['year']})")
            print(f"   Price: €{parsed['price']}")
            print(f"   Mileage: {parsed['mileage']:,} km")
            print(f"   Location: {parsed['location_text']}")
            print(f"   URL: {parsed['source_url']}")
            print()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
