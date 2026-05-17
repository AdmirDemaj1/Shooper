"""
mobile.al source adapter — Albania's largest general classifieds site.
Cars live under: https://www.mobile.al/category/makina-automjete/
"""
from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from crawler.sources.base import SourceAdapter

BASE_URL = "https://www.mobile.al"
SEARCH_PATH = "/category/makina-automjete/"

_YEAR_RE = re.compile(r"\b(19[5-9]\d|20[012]\d)\b")
_KM_RE = re.compile(r"([\d\s.,]+)\s*km", re.IGNORECASE)
_PRICE_RE = re.compile(r"([\d\s.,]+)\s*(eur|€|lek|all|lekë)", re.IGNORECASE)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "sq-AL,sq;q=0.9,en;q=0.8",
}


def _clean_int(text: str | None) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", str(text))
    return int(digits) if digits else None


class MobileAlAdapter(SourceAdapter):
    name = "mobile_al"
    country = "AL"
    min_request_interval_seconds = 2.5

    def _build_url(self, profile: dict[str, Any], page: int) -> str:
        params: dict[str, Any] = {"page": page}
        if profile.get("make"):
            params["marka"] = profile["make"]
        if profile.get("model"):
            params["model"] = profile["model"]
        if profile.get("price_max"):
            params["cmimi_max"] = int(profile["price_max"])
        if profile.get("year_min"):
            params["viti_min"] = profile["year_min"]
        if profile.get("year_max"):
            params["viti_max"] = profile["year_max"]
        if profile.get("mileage_max"):
            params["km_max"] = profile["mileage_max"]
        return f"{BASE_URL}{SEARCH_PATH}?{urlencode(params)}"

    def _fetch(self, url: str) -> BeautifulSoup:
        self._throttle()
        resp = httpx.get(url, headers=_HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")

    def _parse_card(self, card) -> dict[str, Any] | None:
        link = card.select_one("a[href]")
        if not link:
            return None
        href = link["href"]
        if not href.startswith("http"):
            href = BASE_URL + href

        id_match = re.search(r"/(\d{4,})", href)
        source_listing_id = id_match.group(1) if id_match else href.split("/")[-1]

        title_el = card.select_one(".title, h2, h3, [class*='title']")
        title = title_el.get_text(strip=True) if title_el else ""

        price_el = card.select_one(".price, [class*='price']")
        price_text = price_el.get_text(strip=True) if price_el else ""
        pm = _PRICE_RE.search(price_text)
        price_digits = re.sub(r"[^\d]", "", pm.group(1)) if pm else None
        currency_raw = (pm.group(2).lower() if pm else "eur")
        currency = "EUR" if currency_raw in ("eur", "€") else "ALL"

        location_el = card.select_one(".location, [class*='location'], [class*='city']")
        location_text = location_el.get_text(strip=True) if location_el else "AL"

        details = card.get_text(" ", strip=True)
        year_m = _YEAR_RE.search(details)
        year = int(year_m.group(1)) if year_m else None
        km_m = _KM_RE.search(details)
        mileage = _clean_int(km_m.group(1)) if km_m else None

        img = card.select_one("img[src]")
        image_url = img["src"] if img else None

        return {
            "source": self.name,
            "source_listing_id": source_listing_id,
            "source_url": href,
            "title": title,
            "make": None,
            "model": None,
            "year": year,
            "price": price_digits,
            "currency": currency,
            "mileage": mileage,
            "location_text": location_text,
            "description": None,
            "image_url": image_url,
        }

    def search(self, profile: dict[str, Any]) -> list[dict[str, Any]]:
        use_mock = os.getenv("MOBILE_AL_USE_MOCK", "true").lower() == "true"
        if use_mock:
            return self._mock_results()

        def _impl() -> list[dict[str, Any]]:
            results: list[dict[str, Any]] = []
            max_pages = int(os.getenv("MOBILE_AL_MAX_PAGES", "3"))
            for page in range(1, max_pages + 1):
                url = self._build_url(profile, page)
                soup = self._fetch(url)
                cards = (
                    soup.select(".listing-item")
                    or soup.select(".ad-item")
                    or soup.select("article")
                    or soup.select("[class*='listing']")
                )
                if not cards:
                    break
                for card in cards:
                    raw = self._parse_card(card)
                    if raw:
                        results.append(raw)
                if not soup.select_one("a[rel='next'], .next-page:not(.disabled)"):
                    break
            return results

        return self._run_with_retry(_impl)

    def parse(self, raw: dict[str, Any]) -> dict[str, Any]:
        title = raw.get("title") or ""
        make = raw.get("make")
        model = raw.get("model")
        if not make and title:
            parts = title.split()
            make = parts[0] if parts else None
            model = " ".join(parts[1:3]) if len(parts) > 1 else None
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
        try:
            resp = httpx.get(BASE_URL, headers=_HEADERS, timeout=10, follow_redirects=True)
            return resp.status_code == 200
        except Exception:
            return False

    def _mock_results(self) -> list[dict[str, Any]]:
        return [
            {
                "source": self.name, "source_listing_id": "mal_001",
                "source_url": "https://www.mobile.al/listing/mal_001",
                "title": "2020 Toyota Corolla", "make": "Toyota", "model": "Corolla",
                "year": 2020, "price": "14500", "currency": "EUR",
                "mileage": 68000, "location_text": "Tirane, AL",
                "description": "Petrol, automatic, first owner",
            },
            {
                "source": self.name, "source_listing_id": "mal_002",
                "source_url": "https://www.mobile.al/listing/mal_002",
                "title": "2016 Audi A4 Diesel", "make": "Audi", "model": "A4",
                "year": 2016, "price": "11000", "currency": "EUR",
                "mileage": 189000, "location_text": "Durres, AL",
                "description": "Diesel, manual, well maintained",
            },
        ]
