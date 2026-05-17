from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from crawler.sources.base import SourceAdapter

BASE_URL = "https://www.merrjep.al"
SEARCH_PATH = "/category/vehicles/cars"

# merrjep uses ALL (Albanian Lek) and EUR
_CURRENCY_RE = re.compile(r"(eur|€|lekë|lek|all)", re.IGNORECASE)
_DIGITS_RE = re.compile(r"[\d\s.,]+")
_YEAR_RE = re.compile(r"\b(19[5-9]\d|20[012]\d)\b")
_KM_RE = re.compile(r"([\d\s.,]+)\s*km", re.IGNORECASE)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "sq-AL,sq;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _clean_int(text: str | None) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _extract_currency(text: str) -> str:
    m = _CURRENCY_RE.search(text or "")
    if m:
        v = m.group(1).lower()
        if v in ("eur", "€"):
            return "EUR"
        return "ALL"
    return "EUR"


class MerrjepAdapter(SourceAdapter):
    name = "merrjep"
    country = "AL"
    # Merrjep is well-behaved; 2s interval is enough
    min_request_interval_seconds = 2.0

    def _build_search_url(self, profile: dict[str, Any], page: int = 1) -> str:
        params: dict[str, Any] = {"page": page}
        if profile.get("make"):
            params["make"] = profile["make"]
        if profile.get("model"):
            params["model"] = profile["model"]
        if profile.get("price_max"):
            params["priceMax"] = int(profile["price_max"])
        if profile.get("price_min"):
            params["priceMin"] = int(profile["price_min"])
        if profile.get("year_min"):
            params["yearFrom"] = profile["year_min"]
        if profile.get("year_max"):
            params["yearTo"] = profile["year_max"]
        if profile.get("mileage_max"):
            params["mileageMax"] = profile["mileage_max"]
        if profile.get("fuel_type"):
            params["fuelType"] = profile["fuel_type"]
        if profile.get("transmission"):
            params["transmission"] = profile["transmission"]
        return f"{BASE_URL}{SEARCH_PATH}?{urlencode(params)}"

    def _fetch_page(self, url: str) -> BeautifulSoup:
        self._throttle()
        resp = httpx.get(url, headers=_HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")

    def _parse_listing_card(self, card) -> dict[str, Any] | None:
        """Extract raw data from a single listing card element."""
        # --- URL + ID ---
        link = card.select_one("a[href]")
        if not link:
            return None
        href = link["href"]
        if not href.startswith("http"):
            href = BASE_URL + href

        # listing ID from URL slug: last numeric segment
        id_match = re.search(r"/(\d{5,})", href)
        source_listing_id = id_match.group(1) if id_match else href.split("/")[-1]

        # --- Title ---
        title_el = card.select_one(".listing-title, h2, h3, .ad-title, [class*='title']")
        title = title_el.get_text(strip=True) if title_el else ""

        # --- Price ---
        price_el = card.select_one(".price, .listing-price, [class*='price']")
        price_text = price_el.get_text(strip=True) if price_el else ""
        price_digits = re.sub(r"[^\d]", "", price_text) or None
        currency = _extract_currency(price_text)

        # --- Location ---
        location_el = card.select_one(".location, .city, [class*='location'], [class*='city']")
        location_text = location_el.get_text(strip=True) if location_el else ""

        # --- Details block (year, mileage, fuel) ---
        details_text = card.get_text(" ", strip=True)
        year_match = _YEAR_RE.search(details_text)
        year = int(year_match.group(1)) if year_match else None
        km_match = _KM_RE.search(details_text)
        mileage = _clean_int(km_match.group(1)) if km_match else None

        # --- Image ---
        img = card.select_one("img[src]")
        image_url = img["src"] if img else None

        return {
            "source": self.name,
            "source_listing_id": source_listing_id,
            "source_url": href,
            "title": title,
            "make": None,   # extracted in parse() from title
            "model": None,
            "year": year,
            "price": price_digits,
            "currency": currency,
            "mileage": mileage,
            "location_text": location_text or "AL",
            "description": None,
            "image_url": image_url,
            "_raw_text": details_text,
        }

    def search(self, profile: dict[str, Any]) -> list[dict[str, Any]]:
        use_mock = os.getenv("MERRJEP_USE_MOCK", "true").lower() == "true"
        if use_mock:
            return self._mock_results()

        def _search_impl() -> list[dict[str, Any]]:
            results: list[dict[str, Any]] = []
            max_pages = int(os.getenv("MERRJEP_MAX_PAGES", "3"))

            for page in range(1, max_pages + 1):
                url = self._build_search_url(profile, page)
                soup = self._fetch_page(url)

                # merrjep listing cards – multiple possible selectors
                cards = (
                    soup.select(".listing-item")
                    or soup.select(".ad-item")
                    or soup.select("[class*='listing-card']")
                    or soup.select("article")
                )
                if not cards:
                    break

                for card in cards:
                    raw = self._parse_listing_card(card)
                    if raw:
                        results.append(raw)

                # Stop if last page
                next_btn = soup.select_one("a[rel='next'], .pagination-next:not(.disabled)")
                if not next_btn:
                    break

            return results

        return self._run_with_retry(_search_impl)

    def parse(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalise a raw listing dict into the canonical schema."""
        title = raw.get("title") or ""

        # Attempt to split make/model from title (e.g. "VW Golf 6 2018")
        make = raw.get("make")
        model = raw.get("model")
        if not make and title:
            parts = title.split()
            if parts:
                make = parts[0]
            if len(parts) > 1:
                model = " ".join(parts[1:3])

        return {
            "source": raw.get("source"),
            "source_listing_id": raw.get("source_listing_id"),
            "source_url": raw.get("source_url"),
            "title": title,
            "make": make,
            "model": model,
            "year": raw.get("year"),
            "price": raw.get("price"),
            "currency": raw.get("currency") or "EUR",
            "mileage": raw.get("mileage"),
            "location_text": raw.get("location_text"),
            "description": raw.get("description"),
        }

    def health_check(self) -> bool:
        def _check() -> bool:
            resp = httpx.get(BASE_URL, headers=_HEADERS, timeout=10, follow_redirects=True)
            return resp.status_code == 200

        try:
            return self._run_with_retry(_check)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Mock data — kept here so dev/test flows work without network access
    # ------------------------------------------------------------------
    def _mock_results(self) -> list[dict[str, Any]]:
        return [
            {
                "source": self.name, "source_listing_id": "mock_001",
                "source_url": "https://merrjep.al/listing/mock_001",
                "title": "2019 Honda Civic", "make": "Honda", "model": "Civic",
                "year": 2019, "price": "9500", "currency": "EUR",
                "mileage": 145000, "location_text": "Tirane, AL",
                "description": "Clean title, well maintained, single owner",
            },
            {
                "source": self.name, "source_listing_id": "mock_002",
                "source_url": "https://merrjep.al/listing/mock_002",
                "title": "2018 Volkswagen Golf", "make": "Volkswagen", "model": "Golf 7",
                "year": 2018, "price": "8900", "currency": "EUR",
                "mileage": 167000, "location_text": "Durres, AL",
                "description": "Manual transmission, good condition",
            },
            {
                "source": self.name, "source_listing_id": "mock_003",
                "source_url": "https://merrjep.al/listing/mock_003",
                "title": "2017 Fiat 500", "make": "Fiat", "model": "500",
                "year": 2017, "price": "6500", "currency": "EUR",
                "mileage": 89000, "location_text": "Vlore, AL",
                "description": "City car, compact, perfect for urban driving",
            },
        ]
