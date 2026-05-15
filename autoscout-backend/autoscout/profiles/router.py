from __future__ import annotations

import pathlib
from typing import Any
from uuid import UUID

import anthropic
import structlog
from fastapi import APIRouter, Depends, HTTPException, Response
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError
from sqlalchemy.orm import Session

from autoscout.auth.dependencies import get_db_user
from autoscout.db.models import LlmCall, SearchProfile, User
from autoscout.db.session import get_db
from autoscout.settings import settings

from .schemas import (
    ParseRequest,
    ParseResponse,
    SearchProfileCreate,
    SearchProfileRead,
    SearchProfileUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/profiles", tags=["profiles"])

_PROMPT_PATH = pathlib.Path(__file__).parent.parent.parent.parent / "autoscout-prompts" / "profile_parser" / "v1.md"
_SYSTEM_PROMPT: str | None = None

_PARSE_TOOL: dict[str, Any] = {
    "name": "create_search_profile",
    "description": "Extract structured car search criteria from the user's text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Short descriptive profile name"},
            "make": {"type": "string", "description": "Car manufacturer (e.g. Volkswagen, BMW)"},
            "model": {"type": "string", "description": "Car model (e.g. Golf 6, Seria 3)"},
            "year_min": {"type": "integer", "description": "Minimum production year"},
            "year_max": {"type": "integer", "description": "Maximum production year"},
            "price_min": {"type": "number", "description": "Minimum price"},
            "price_max": {"type": "number", "description": "Maximum price"},
            "currency": {"type": "string", "enum": ["EUR", "ALL"], "description": "Price currency"},
            "mileage_max": {"type": "integer", "description": "Maximum odometer reading in km"},
            "location_name": {"type": "string", "description": "Place name to geocode (e.g. Tiranë, Durrës)"},
            "radius_km": {"type": "integer", "description": "Search radius in km around location (max 200)"},
            "body_type": {"type": "string", "enum": ["sedan", "hatchback", "estate", "suv", "coupe", "convertible", "van", "pickup"]},
            "transmission": {"type": "string", "enum": ["manual", "automatic"]},
            "fuel_type": {"type": "string", "enum": ["petrol", "diesel", "electric", "hybrid", "lpg"]},
            "free_text_criteria": {"type": "string", "description": "Any remaining criteria that don't fit structured fields"},
            "confidence_scores": {
                "type": "object",
                "description": "Confidence score 0.0–1.0 for each populated field",
                "additionalProperties": {"type": "number"},
            },
        },
        "required": ["name", "confidence_scores"],
    },
}

_CONFIDENCE_THRESHOLD = 0.5


def _load_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        try:
            _SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            _SYSTEM_PROMPT = "Extract structured car search criteria from user text and call create_search_profile."
    return _SYSTEM_PROMPT


def _geocode(place_name: str) -> tuple[float, float] | None:
    try:
        geolocator = Nominatim(user_agent="autoscout/1.0")
        location = geolocator.geocode(place_name + ", Albania", timeout=5)
        if location:
            return location.latitude, location.longitude
        # Retry without "Albania" qualifier
        location = geolocator.geocode(place_name, timeout=5)
        if location:
            return location.latitude, location.longitude
    except GeocoderServiceError as e:
        logger.warning("geocode_failed", place=place_name, error=str(e))
    return None


def _get_owned_profile(profile_id: UUID, user: User, db: Session) -> SearchProfile:
    profile = (
        db.query(SearchProfile)
        .filter(SearchProfile.id == profile_id, SearchProfile.user_id == user.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# ---------------------------------------------------------------------------
# NL Parse — registered first so /parse doesn't get swallowed by /{profile_id}
# ---------------------------------------------------------------------------

@router.post("/parse", response_model=ParseResponse)
def parse_profile(
    body: ParseRequest,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> ParseResponse:
    """Parse free-text car description into a structured SearchProfileCreate."""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="LLM service not configured")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=_load_system_prompt(),
            tools=[_PARSE_TOOL],
            tool_choice={"type": "tool", "name": "create_search_profile"},
            messages=[{"role": "user", "content": body.text}],
        )
    except anthropic.APIError as e:
        logger.error("claude_parse_failed", error=str(e), user_id=str(user.id))
        raise HTTPException(status_code=502, detail="LLM service error")

    tool_block = next((b for b in response.content if b.type == "tool_use"), None)
    if not tool_block:
        raise HTTPException(status_code=502, detail="LLM returned no structured output")

    extracted: dict[str, Any] = tool_block.input
    confidence_scores: dict[str, float] = extracted.pop("confidence_scores", {})
    location_name: str | None = extracted.pop("location_name", None)

    # Geocode place name if provided
    if location_name:
        coords = _geocode(location_name)
        if coords:
            extracted["location_lat"], extracted["location_lng"] = coords
        else:
            logger.warning("geocode_no_result", place=location_name)

    # Clamp radius
    if extracted.get("radius_km") and extracted["radius_km"] > 200:
        extracted["radius_km"] = 200

    # Build create payload — name is required, use a fallback if Claude omitted it
    extracted.setdefault("name", body.text[:80])

    try:
        profile_create = SearchProfileCreate(**extracted)
    except Exception as e:
        logger.error("parse_schema_validation_failed", error=str(e))
        raise HTTPException(status_code=422, detail=f"Parsed data invalid: {e}")

    low_confidence_fields = [
        field for field, score in confidence_scores.items() if score < _CONFIDENCE_THRESHOLD
    ]
    needs_review = bool(low_confidence_fields)

    logger.info(
        "profile_parsed",
        user_id=str(user.id),
        needs_review=needs_review,
        low_confidence_fields=low_confidence_fields,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )

    try:
        db.add(LlmCall(
            user_id=user.id,
            endpoint="/profiles/parse",
            model="claude-sonnet-4-6",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        ))
        db.commit()
    except Exception as e:
        logger.warning("llm_call_log_failed", error=str(e))

    return ParseResponse(
        profile=profile_create,
        needs_review=needs_review,
        low_confidence_fields=low_confidence_fields,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=SearchProfileRead, status_code=201)
def create_profile(
    body: SearchProfileCreate,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> SearchProfile:
    active_count = (
        db.query(SearchProfile)
        .filter(SearchProfile.user_id == user.id, SearchProfile.is_active.is_(True))
        .count()
    )
    if active_count >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 active profiles reached")

    profile = SearchProfile(user_id=user.id, **body.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    logger.info("profile_created", user_id=str(user.id), profile_id=str(profile.id))
    return profile


@router.get("", response_model=list[SearchProfileRead])
def list_profiles(
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> list[SearchProfile]:
    return (
        db.query(SearchProfile)
        .filter(SearchProfile.user_id == user.id)
        .order_by(SearchProfile.created_at.desc())
        .all()
    )


@router.get("/{profile_id}", response_model=SearchProfileRead)
def get_profile(
    profile_id: UUID,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> SearchProfile:
    return _get_owned_profile(profile_id, user, db)


@router.patch("/{profile_id}", response_model=SearchProfileRead)
def update_profile(
    profile_id: UUID,
    body: SearchProfileUpdate,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> SearchProfile:
    profile = _get_owned_profile(profile_id, user, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    logger.info("profile_updated", profile_id=str(profile_id))
    return profile


@router.delete("/{profile_id}")
def delete_profile(
    profile_id: UUID,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> Response:
    profile = _get_owned_profile(profile_id, user, db)
    db.delete(profile)
    db.commit()
    logger.info("profile_deleted", profile_id=str(profile_id))
    return Response(status_code=204)


@router.post("/{profile_id}/toggle", response_model=SearchProfileRead)
def toggle_profile(
    profile_id: UUID,
    user: User = Depends(get_db_user),
    db: Session = Depends(get_db),
) -> SearchProfile:
    profile = _get_owned_profile(profile_id, user, db)
    profile.is_active = not profile.is_active
    db.commit()
    db.refresh(profile)
    logger.info("profile_toggled", profile_id=str(profile_id), is_active=profile.is_active)
    return profile
