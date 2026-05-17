"""
gjirafa.com source adapter — large regional Albanian aggregator.
Cars section: https://gjirafa.com/autot/makina
"""
from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from crawler.sources.base import SourceAdapter

BASE_URL = "https://gjirafa.com"
SEARCH_PATH = "/autot/makina"

_YEAR_RE = re.compile(r"\b(19[5-9]\d|20[012]\d)\b")
_KM_RE = re.compile(r"([\d\s.,]+)\s*km", re.IGNORECASE)
_PRICE_RE = re.compile(r"([\d\s.,]+)\s*(eur|€|lek|all|lekë)", re.IGNORECASE)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
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


class GjirafaAdapter(SourceAdapter):
    name = "gjirafa"
    country = "AL"
    min_request_interval_seconds = 2.5

    def _build_url(self, profile: dict[str, Any], page: int) -> str:
        params: dict[str, Any] = {"fq": 1, "page": page}
        if profile.get("make"):
            params["marka"] = profile["make"]
        if profile.get("model"):
            params["modeli"] = profile["model"]
        if profile.get("price_max"):
            params["cmimi_deri"] = int(profile["price_max"])
        if profile.get("year_min"):
            params["viti_nga"] = profile["year_min"]
        if profile.get("year_max"):
            params["viti_deri"] = profile["year_max"]
        if profile.get("mileage_max"):
            params["km_deri"] = profile["mileage_max"]
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
        source_listing_id = id_match.group(1) if id_match else href.rstrip("/").split("/")[-1]

        title_el = card.select_one("h2, h3, .title, [class*='title']")
        title = title_el.get_text(strip=True) if title_el else ""

        price_el = card.select_one(".price, [class*='cmimi'], [class*='price']")
        price_text = price_el.get_text(strip=True) if price_el else ""
        pm = _PRICE_RE.search(price_text)
        price_digits = re.sub(r"[^\d]", "", pm.group(1)) if pm else None
        currency_raw = (pm.group(2).lower() if pm else "eur")
        currency = "EUR" if currency_raw in ("eur", "€") else "ALL"

        location_el = card.select_one(".location, [class*='qyteti'], [class*='location']")
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
        use_mock = os.getenv("GJIRAFA_USE_MOCK", "true").lower() == "true"
        if use_mock:
            return self._mock_results()

        def _impl() -> list[dict[str, Any]]:
            results: list[dict[str, Any]] = []
            max_pages = int(os.getenv("GJIRAFA_MAX_PAGES", "3"))
            for page in range(1, max_pages + 1):
                url = self._build_url(profile, page)
                soup = self._fetch(url)
                cards = (
                    soup.select(".product-item")
                    or soup.select(".listing-item")
                    or soup.select("article")
                    or soup.select("[class*='card']")
                )
                if not cards:
                    break
                for card in cards:
                    raw = self._parse_card(card)
                    if raw:
                        results.append(raw)
                if not soup.select_one("a[rel='next'], .next:not(.disabled)"):
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
                "source": self.name, "source_listing_id": "gjf_001",
                "source_url": "https://gjirafa.com/autot/makina/gjf_001",
                "title": "2017 BMW 320d", "make": "BMW", "model": "320d",
                "year": 2017, "price": "13500", "currency": "EUR",
                "mileage": 210000, "location_text": "Tirane, AL",
                "description": "Diesel, automatic, panoramic roof",
            },
            {
                "source": self.name, "source_listing_id": "gjf_002",
                "source_url": "https://gjirafa.com/autot/makina/gjf_002",
                "title": "2015 Skoda Octavia", "make": "Skoda", "model": "Octavia",
                "year": 2015, "price": "7800", "currency": "EUR",
                "mileage": 155000, "location_text": "Elbasan, AL",
                "description": "Diesel, manual, full service history",
            },
        ]
