# Sprint 2 — Search Profile Creation

**Duration:** Weeks 3–4
**Theme:** The user can describe what car they want, either with a form or in plain Albanian/English, and the system stores it as a structured `search_profile`.

---

## Goals

- Users can create, edit, list, delete, and toggle search profiles from the mobile app.
- Natural-language input ("kërkoj Golf 6 nën 8000 euro afër Tiranës") is reliably parsed into structured fields via Claude tool use.
- Geographic search (location + radius) is supported end-to-end.

## Out of Scope

- Crawling against multiple sources (Sprint 3)
- Matching and ranking (Sprint 4)
- Sending results anywhere (Sprint 5)

---

## Workstreams

### Backend — Search Profile CRUD

- [ ] Complete `search_profiles` migration:
  ```
  id, user_id, name,
  make, model,                    -- nullable, null = any
  year_min, year_max,
  price_min, price_max, currency, -- ALL/EUR primarily for Albania
  mileage_max,
  location_lat, location_lng, radius_km,
  body_type, transmission, fuel_type,  -- enums, nullable
  free_text_criteria,
  is_active,
  delivery_time_local,            -- hour 0-23 in user's timezone
  timezone,                       -- IANA string, e.g. 'Europe/Tirane'
  created_at, updated_at
  ```
- [ ] **PostGIS extension** enabled in PostgreSQL; `location` stored as `geography(POINT, 4326)`.
- [ ] Pydantic schemas: `SearchProfileCreate`, `SearchProfileUpdate`, `SearchProfileRead`.
- [ ] Endpoints:
  - `POST /profiles` — create
  - `GET /profiles` — list current user's profiles
  - `GET /profiles/{id}` — read
  - `PATCH /profiles/{id}` — update (partial)
  - `DELETE /profiles/{id}` — soft delete
  - `POST /profiles/{id}/toggle` — flip `is_active`
- [ ] Validation: price/year/mileage ranges sane; radius capped at 200 km (Albania-wide); max 10 active profiles per user.
- [ ] Authorization: every endpoint scoped to the authenticated user's profiles only (no cross-tenant leaks).

### Backend — Natural Language Parser

- [ ] New endpoint: `POST /profiles/parse`
  - Input: `{ "text": "kërkoj Golf 6 nën 8000 euro afër Tiranës, max 200 mijë km" }`
  - Output: structured `SearchProfileCreate` payload + `confidence` score per field.
- [ ] Claude API integration with **tool use** for structured extraction:
  - Define a `create_search_profile` tool with the exact schema fields.
  - Force `tool_choice` to that tool so output is always structured JSON.
  - Use Claude Sonnet 4.6 (latest at this date).
- [ ] System prompt versioned in `autoscout-prompts/profile_parser/v1.md`.
- [ ] **Albanian-language coverage** — prompt with examples in Albanian (numbers, common car terms: "vit", "kilometra", "manuale", "automatike", "nafte", "benzine").
- [ ] Geocoding step: if the model returns a place name ("Tiranë", "Durrës"), call a geocoder (Google Geocoding API or Nominatim) to resolve to lat/lng.
- [ ] Fallback: if parsing fails or confidence is low (<0.5 on key fields), return a partial result with `needs_review: true` so the mobile app can prompt the user to confirm.
- [ ] Regression test suite in `autoscout-prompts`: 30+ Albanian + English example inputs with expected outputs.

### Mobile — Search Profile UX

- [ ] **Create flow** with two entry points on the Searches tab:
  - "+ Quick create" (form-based)
  - "+ Describe in words" (natural language)
- [ ] **Form flow:**
  - Make picker (dropdown of common makes + "Any")
  - Model field (free text, filtered by make if available)
  - Year range (dual slider, 1990–current)
  - Price range (dual slider, ALL or EUR toggle)
  - Mileage cap (slider, 0–500,000 km)
  - Body type, transmission, fuel type (chip selectors)
  - Location picker (map screen) + radius slider
  - Free-text criteria field
  - Delivery time picker (hour of day)
  - "Save" button
- [ ] **Natural language flow:**
  - Multi-line text input with placeholder example
  - "Parse" button → calls `POST /profiles/parse`
  - Result shown in the same form pre-filled; user reviews and saves.
  - If `needs_review: true`, fields needing confirmation are highlighted in yellow.
- [ ] **List view** on Searches tab: cards with profile name, summary line, active toggle, edit / delete swipe actions.
- [ ] **Edit flow** reuses the form components.
- [ ] **Location picker:** Mapbox or Google Maps RN component; default center on Tiranë; long-press to drop pin; radius circle overlay.

### AI/ML

- [ ] Build the prompt regression harness in `autoscout-prompts`:
  - Each test case is a YAML file with `input`, `expected`, `tolerance` (allows fuzzy match on numeric fields).
  - CI job runs the harness on every PR to the prompts repo.
- [ ] Cost telemetry: log token usage per `/profiles/parse` call to a `llm_calls` table for the Sprint 4 cost dashboard.

### Design

- [ ] Form and natural-language flow high-fidelity screens.
- [ ] Map location picker mocks.
- [ ] Empty-state illustration for "no profiles yet."

---

## Definition of Done

A user can:

1. Open the app, sign in.
2. Tap "Describe in words," type *"VW Golf 6 ose 7, viti 2010 deri 2015, çmim deri 8000 euro, kilometra max 200 mijë, afër Tiranës 50 km"*.
3. See the form pre-filled with: make=VW, model=Golf 6 or Golf 7, year 2010–2015, price 0–8000 EUR, mileage_max=200000, location=Tirane, radius=50 km.
4. Adjust any field, save.
5. See it in the Searches list with an active toggle.
6. Edit, deactivate, delete it from the same screen.

End-to-end latency for the parse call: **under 4 seconds at p95.**

---

## Risks & Watch-Outs

- **Albanian language model performance** — Claude handles it but proper nouns (place names, model variants) can drift. Bias toward locking key vocabulary in the system prompt with examples.
- **Geocoding quotas** — Google Geocoding is paid past free tier; Nominatim has strict rate limits. Cache results aggressively.
- **PostGIS migration on existing dev DB** — extension needs `superuser` to create; coordinate with infra so the dev DB role has the right grants.

---

## Dependencies

- Sprint 1 backend skeleton with auth working.
- Claude API account from Sprint 0 with sufficient quota.
- Geocoder API key (Google Maps Platform or self-hosted Nominatim).

---

## Next Sprint Preview

[Sprint 3 — Multi-Source Crawling](Sprint-3-Multi-Source-Crawling.md): expand from one source to four, add the daily scheduler, and start deduplicating listings.
