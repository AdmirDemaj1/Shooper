"""LLM relevance scoring with Redis cache, Anthropic prompt caching, and deterministic fallback."""
from __future__ import annotations

import hashlib
import json
import logging
import pathlib
from typing import Any

import anthropic
from redis import Redis
from sqlalchemy.orm import Session

from autoscout.db.models import Listing, LlmCall, SearchProfile
from autoscout.settings import settings

logger = logging.getLogger(__name__)

SCORE_CACHE_TTL = 7 * 24 * 3600  # 7 days in seconds
BATCH_SIZE = 20

_PROMPT_PATH = (
    pathlib.Path(__file__).parent.parent.parent.parent
    / "autoscout-prompts"
    / "ranking"
    / "v1.md"
)
_SYSTEM_PROMPT: str | None = None

RANKING_TOOL: dict[str, Any] = {
    "name": "rank_listings",
    "description": "Score each car listing for relevance to the user's search profile.",
    "input_schema": {
        "type": "object",
        "properties": {
            "scores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "listing_id": {"type": "string"},
                        "score": {"type": "integer", "minimum": 0, "maximum": 100},
                        "reasoning": {"type": "string", "maxLength": 250},
                        "summary": {"type": "string", "maxLength": 100},
                    },
                    "required": ["listing_id", "score", "reasoning", "summary"],
                },
            }
        },
        "required": ["scores"],
    },
}


def _load_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        try:
            _SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            _SYSTEM_PROMPT = (
                "You are a car-buying assistant. Score listings 0-100 for the buyer and call rank_listings."
            )
    return _SYSTEM_PROMPT


def _profile_hash(profile: SearchProfile) -> str:
    """Stable 16-char hash covering only the fields that affect LLM scoring."""
    data = {
        "make": profile.make,
        "model": profile.model,
        "free_text": profile.free_text_criteria,
        "price_min": str(profile.price_min) if profile.price_min else None,
        "price_max": str(profile.price_max) if profile.price_max else None,
        "year_min": profile.year_min,
        "year_max": profile.year_max,
        "mileage_max": profile.mileage_max,
        "fuel_type": profile.fuel_type,
        "transmission": profile.transmission,
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


def _deterministic_score(listing: Listing, profile: SearchProfile) -> int:
    """Rule-based fallback score (0-100) when Claude is unavailable."""
    score = 60
    current_year = 2026

    # Year: reward newer cars
    if listing.year:
        age = current_year - listing.year
        if age <= 3:
            score += 20
        elif age <= 7:
            score += 10
        elif age >= 15:
            score -= 15

    # Mileage: reward lower mileage
    if listing.mileage:
        if listing.mileage < 50_000:
            score += 15
        elif listing.mileage < 100_000:
            score += 7
        elif listing.mileage > 200_000:
            score -= 15

    # Price: small reward for being well under budget
    if listing.price and profile.price_max:
        try:
            price = float(listing.price)
            price_max = float(profile.price_max)
            ratio = price / price_max
            if ratio < 0.75:
                score += 10
            elif ratio > 0.95:
                score -= 5
        except (ValueError, TypeError):
            pass

    # Description: reward non-empty descriptions
    if listing.description and len(listing.description) > 50:
        score += 5

    return max(0, min(100, score))


def score_listings(
    profile: SearchProfile,
    listings: list[Listing],
    redis_client: Redis | None = None,
    db: Session | None = None,
) -> list[dict[str, Any]]:
    """
    Score listings for relevance to profile.

    Checks Redis cache first for each listing, calls Claude for the rest in
    batches of up to BATCH_SIZE (with Anthropic prompt caching on the stable
    prefix), falls back to deterministic scoring on error.

    Returns a list of dicts: {listing_id, score, reasoning, summary, score_source}.
    Logs token usage to the llm_calls table when a db session is provided.
    """
    if not listings:
        return []

    profile_hash = _profile_hash(profile)
    results: list[dict[str, Any]] = []
    to_score: list[Listing] = []

    # ── Cache lookup ─────────────────────────────────────────────────────────
    for listing in listings:
        cache_key = f"match_score:{profile_hash}:{listing.id}"
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    results.append(json.loads(cached))
                    continue
            except Exception:
                pass  # Redis unavailable — proceed without cache
        to_score.append(listing)

    if not to_score:
        return results

    # ── LLM scoring ──────────────────────────────────────────────────────────
    try:
        llm_results, usage = _score_with_llm(profile, to_score)
        for item in llm_results:
            if redis_client:
                try:
                    cache_key = f"match_score:{profile_hash}:{item['listing_id']}"
                    redis_client.setex(cache_key, SCORE_CACHE_TTL, json.dumps(item))
                except Exception:
                    pass
        results.extend(llm_results)
        _log_llm_call(db, usage)
    except Exception as exc:
        logger.warning("LLM scoring failed, using deterministic fallback: %s", exc)
        for listing in to_score:
            results.append(
                {
                    "listing_id": str(listing.id),
                    "score": _deterministic_score(listing, profile),
                    "reasoning": "Scored by deterministic fallback (LLM unavailable).",
                    "summary": _default_summary(listing),
                    "score_source": "fallback",
                }
            )

    return results


def _score_with_llm(
    profile: SearchProfile,
    listings: list[Listing],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Call Claude to score listings. Uses Anthropic prompt caching on the stable
    system prompt + profile description prefix to reduce token costs.

    Returns (scores, usage) where usage = {input_tokens, output_tokens,
    cache_creation_input_tokens, cache_read_input_tokens}.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system_prompt = _load_system_prompt()
    profile_desc = _build_profile_description(profile)
    all_scores: list[dict[str, Any]] = []
    total_usage: dict[str, int] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }

    for i in range(0, len(listings), BATCH_SIZE):
        batch = listings[i : i + BATCH_SIZE]
        batch_data = [_listing_to_dict(l) for l in batch]

        response = client.beta.prompt_caching.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            # Cache the system prompt — large and constant across all scoring calls.
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[RANKING_TOOL],
            tool_choice={"type": "tool", "name": "rank_listings"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        # Cache the profile description — stable across all batches
                        # within the same profile run.
                        {
                            "type": "text",
                            "text": f"SEARCH PROFILE:\n{profile_desc}\n\n",
                            "cache_control": {"type": "ephemeral"},
                        },
                        # Listings vary per batch — not cached.
                        {
                            "type": "text",
                            "text": f"LISTINGS (JSON):\n{json.dumps(batch_data, ensure_ascii=False)}",
                        },
                    ],
                }
            ],
        )

        usage = response.usage
        total_usage["input_tokens"] += usage.input_tokens
        total_usage["output_tokens"] += usage.output_tokens
        total_usage["cache_creation_input_tokens"] += getattr(
            usage, "cache_creation_input_tokens", 0
        ) or 0
        total_usage["cache_read_input_tokens"] += getattr(
            usage, "cache_read_input_tokens", 0
        ) or 0

        for block in response.content:
            if block.type == "tool_use" and block.name == "rank_listings":
                for s in block.input.get("scores", []):
                    all_scores.append(
                        {
                            "listing_id": s["listing_id"],
                            "score": int(s["score"]),
                            "reasoning": s.get("reasoning", ""),
                            "summary": s.get("summary", ""),
                            "score_source": "llm",
                        }
                    )
                break
        else:
            raise ValueError("Claude did not return rank_listings tool output for this batch")

    logger.info(
        "scorer: input=%d output=%d cache_created=%d cache_read=%d",
        total_usage["input_tokens"],
        total_usage["output_tokens"],
        total_usage["cache_creation_input_tokens"],
        total_usage["cache_read_input_tokens"],
    )

    return all_scores, total_usage


def _log_llm_call(db: Session | None, usage: dict[str, int]) -> None:
    """Persist token usage to llm_calls for cost tracking."""
    if db is None:
        return
    try:
        record = LlmCall(
            endpoint="matching/ranking",
            model="claude-sonnet-4-5",
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )
        db.add(record)
        db.flush()

        # Warn if daily LLM spend looks high (rough estimate).
        total_tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        if total_tokens > 100_000:
            logger.warning(
                "scorer: high token usage in single run — %d tokens. "
                "Check LLM cost dashboard.",
                total_tokens,
            )
    except Exception as exc:
        logger.warning("scorer: failed to log LLM call: %s", exc)


def _build_profile_description(profile: SearchProfile) -> str:
    parts: list[str] = []
    if profile.name:
        parts.append(f"Profile name: {profile.name}")
    if profile.make:
        parts.append(f"Make: {profile.make}")
    if profile.model:
        parts.append(f"Model: {profile.model}")
    if profile.year_min or profile.year_max:
        parts.append(f"Year range: {profile.year_min or '?'} – {profile.year_max or '?'}")
    if profile.price_min or profile.price_max:
        parts.append(
            f"Price range: {profile.price_min or 0} – {profile.price_max or '?'} {profile.currency}"
        )
    if profile.mileage_max:
        parts.append(f"Max mileage: {profile.mileage_max:,} km")
    if profile.fuel_type:
        parts.append(f"Fuel type: {profile.fuel_type}")
    if profile.transmission:
        parts.append(f"Transmission: {profile.transmission}")
    if profile.free_text_criteria:
        parts.append(f"Additional criteria: {profile.free_text_criteria}")
    return "\n".join(parts) or "No specific criteria."


def _listing_to_dict(listing: Listing) -> dict[str, Any]:
    return {
        "id": str(listing.id),
        "title": listing.title,
        "make": listing.make,
        "model": listing.model,
        "year": listing.year,
        "price": listing.price,
        "currency": listing.currency,
        "mileage": listing.mileage,
        "location": listing.location_text,
        "description": listing.description,
    }


def _default_summary(listing: Listing) -> str:
    parts = []
    if listing.year:
        parts.append(str(listing.year))
    if listing.make:
        parts.append(listing.make)
    if listing.model:
        parts.append(listing.model)
    price_part = f"€{listing.price}" if listing.price else ""
    km_part = f"{listing.mileage:,} km" if listing.mileage else ""
    location = listing.location_text or ""
    detail = " · ".join(filter(None, [price_part, km_part, location]))
    title = " ".join(parts)
    return f"{title} — {detail}".strip(" —") if detail else title
