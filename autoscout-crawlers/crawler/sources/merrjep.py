from typing import List, Dict, Any
from crawler.sources.base import SourceAdapter


class MerrjepAdapter(SourceAdapter):
    name = "merrjep"
    country = "AL"

    def search(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search merrjep.al for listings matching the profile.
        For Sprint 1, return mock data.
        """
        return [
            {
                "source": self.name,
                "source_listing_id": "mock_001",
                "source_url": "https://merrjep.al/listing/mock_001",
                "title": "2019 Honda Civic",
                "make": "Honda",
                "model": "Civic",
                "year": 2019,
                "price": "9500",
                "currency": "EUR",
                "mileage": 145000,
                "location_text": "Tiranë, AL",
                "description": "Clean title, well maintained, single owner",
            },
            {
                "source": self.name,
                "source_listing_id": "mock_002",
                "source_url": "https://merrjep.al/listing/mock_002",
                "title": "2018 Volkswagen Golf",
                "make": "Volkswagen",
                "model": "Golf 7",
                "year": 2018,
                "price": "8900",
                "currency": "EUR",
                "mileage": 167000,
                "location_text": "Durrës, AL",
                "description": "Manual transmission, good condition",
            },
            {
                "source": self.name,
                "source_listing_id": "mock_003",
                "source_url": "https://merrjep.al/listing/mock_003",
                "title": "2017 Fiat 500",
                "make": "Fiat",
                "model": "500",
                "year": 2017,
                "price": "6500",
                "currency": "EUR",
                "mileage": 89000,
                "location_text": "Vlorë, AL",
                "description": "City car, compact, perfect for urban driving",
            },
        ]

    def parse(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw listing into normalized schema."""
        return {
            "source": raw.get("source"),
            "source_listing_id": raw.get("source_listing_id"),
            "source_url": raw.get("source_url"),
            "title": raw.get("title"),
            "make": raw.get("make"),
            "model": raw.get("model"),
            "year": raw.get("year"),
            "price": raw.get("price"),
            "currency": raw.get("currency"),
            "mileage": raw.get("mileage"),
            "location_text": raw.get("location_text"),
            "description": raw.get("description"),
        }

    def health_check(self) -> bool:
        """Check if the source is reachable."""
        # For Sprint 1, always return True
        return True
