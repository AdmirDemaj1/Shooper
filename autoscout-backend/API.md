# AutoScout Backend — API Reference

Base URL (local dev): `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

---

## Auth

### `POST /auth/sync`
Called by the mobile app immediately after Firebase OTP verification succeeds. Verifies the Firebase token and creates the user in the database if they don't exist yet.

**No auth header required.**

**Body:**
```json
{ "firebase_token": "eyJhbGci..." }
```

**Response:**
```json
{ "user_id": "uuid", "message": "User synced" }
```

---

### `GET /me`
Returns the currently authenticated user's profile.

**Requires:** `Authorization: Bearer <firebase-token>`

**Response:**
```json
{
  "id": "uuid",
  "phone_number": "+355691234567",
  "whatsapp_opt_in": false,
  "country": "AL",
  "locale": "sq",
  "created_at": "2026-05-18T10:00:00"
}
```

---

## Search Profiles

All profile endpoints require `Authorization: Bearer <firebase-token>`. Users can only see and modify their own profiles. Maximum 10 active profiles per user.

### `POST /profiles/parse`
Takes a free-text car description, calls Claude to extract structured search criteria, and returns a pre-filled profile object ready to be saved. Does **not** save anything — the mobile app shows the result to the user for confirmation, then calls `POST /profiles`.

**Body:**
```json
{ "text": "Dua nje Golf 7 2018-2020 manual, max 10000 euro, jo me shume se 150k km" }
```

**Response:**
```json
{
  "profile": {
    "name": "Golf 7 manual",
    "make": "Volkswagen",
    "model": "Golf",
    "year_min": 2018,
    "year_max": 2020,
    "price_max": 10000,
    "currency": "EUR",
    "mileage_max": 150000,
    "transmission": "manual"
  },
  "needs_review": false,
  "low_confidence_fields": []
}
```

If Claude is not confident about a field (e.g. location was ambiguous), `needs_review` is `true` and `low_confidence_fields` lists which ones the user should double-check.

---

### `POST /profiles`
Saves a new search profile. You typically call this after `/profiles/parse` — take the returned `profile` object and POST it here.

**Body:** Same shape as `profile` in the parse response above. All fields except `name` are optional.

**Response:** The created profile with its `id` and timestamps. **Status 201.**

---

### `GET /profiles`
Lists all of the current user's profiles, newest first.

**Response:** Array of profile objects.

---

### `GET /profiles/{profile_id}`
Returns a single profile.

---

### `PATCH /profiles/{profile_id}`
Updates specific fields on a profile. Only include the fields you want to change.

**Body (example — update max price only):**
```json
{ "price_max": 12000 }
```

---

### `DELETE /profiles/{profile_id}`
Deletes a profile and all its matches (cascade). **Status 204, no body.**

---

### `POST /profiles/{profile_id}/toggle`
Flips `is_active` on a profile. Active profiles are crawled daily; inactive ones are paused. Returns the updated profile.

---

### `GET /profiles/{profile_id}/matches`
Lists matches for a profile, newest first. Supports cursor-based pagination.

**Query params:**
| Param | Default | Description |
|-------|---------|-------------|
| `limit` | 20 | Results per page (max 100) |
| `cursor` | — | ISO datetime from the previous page's `next_cursor` |

**Response:**
```json
{
  "matches": [ ...match objects... ],
  "has_more": true,
  "next_cursor": "2026-05-17T08:43:11.123456"
}
```

---

## Matches

### `GET /matches/{match_id}`
Returns full detail for a single match including the listing data and the LLM's reasoning for why it matched.

**Response:**
```json
{
  "id": "uuid",
  "search_profile_id": "uuid",
  "relevance_score": 84,
  "score_source": "llm",
  "llm_reasoning": "Matches all criteria — manual transmission confirmed, single owner, within radius.",
  "summary": "2019 VW Golf 7 — €9,800 · 72 000 km · Tiranë",
  "selected_for_delivery": true,
  "delivery_status": "pending",
  "user_action": null,
  "listing": {
    "title": "VW Golf 7 2019 manual",
    "make": "Volkswagen",
    "model": "Golf",
    "year": 2019,
    "price": "9800",
    "currency": "EUR",
    "mileage": 72000,
    "location_text": "Tiranë",
    "source_url": "https://merrjep.al/...",
    "description": "One owner, full history..."
  }
}
```

---

### `POST /matches/{match_id}/action`
Records what the user did with a match. Used to track engagement and will feed the ranking improvement loop in V2.

**Body:**
```json
{ "action": "clicked" }
```

Valid actions: `clicked`, `dismissed`, `saved`.

**Response:**
```json
{ "status": "ok", "match_id": "uuid", "action": "clicked" }
```

---

## Listings

Platform listings posted by sellers. `source_id = 'autoscout'` on all rows.

### `POST /listings`
Creates a new listing. Immediately triggers AI matching against active search profiles (capped at 50 profiles).

**Requires:** `Authorization: Bearer <firebase-token>`

**Body:**
```json
{
  "title": "VW Golf 7 2019 Manual",
  "make": "Volkswagen",
  "model": "Golf",
  "year": 2019,
  "price": "9800",
  "currency": "EUR",
  "mileage": 72000,
  "location_text": "Tiranë",
  "transmission": "manual",
  "fuel_type": "petrol",
  "body_type": "hatchback",
  "description": "One owner, full service history...",
  "contact_phone": "+355691234567"
}
```

`title` and `description` (min 30 chars) are required. All other fields are optional. `currency` defaults to `EUR`.

**Response:** `ListingRead` object. **Status 201.**

---

### `GET /listings`
Browse active platform listings. Public — no auth required.

**Query params:**
| Param | Description |
|-------|-------------|
| `make` | Case-insensitive partial match |
| `model` | Case-insensitive partial match |
| `year_min` / `year_max` | Year range |
| `price_min` / `price_max` | Price range (float) |
| `mileage_max` | Max mileage in km |
| `fuel_type` | Exact match (case-insensitive) |
| `transmission` | Exact match (case-insensitive) |
| `body_type` | Exact match (case-insensitive) |
| `limit` | 1–50, default 20 |
| `cursor` | ISO datetime from previous page's `next_cursor` |

**Response:**
```json
{
  "listings": [ ...ListingRead objects... ],
  "has_more": true,
  "next_cursor": "2026-05-17T08:43:11.123456"
}
```

---

### `GET /listings/{listing_id}`
Get full detail for one listing. Increments `views_count`. Public.

**Response:** `ListingRead` object.

---

### `PATCH /listings/{listing_id}`
Update fields on a listing. Owner only.

**Requires:** `Authorization: Bearer <firebase-token>`

**Body:** Any subset of listing fields. Setting `status` to `sold` or `removed` also sets `is_active = false`.

Valid statuses: `active`, `sold`, `removed`.

---

### `DELETE /listings/{listing_id}`
Soft-deletes a listing (`status=removed`, `is_active=false`). Owner only. **Status 204.**

**Requires:** `Authorization: Bearer <firebase-token>`

---

### `GET /me/listings`
Returns all listings posted by the authenticated user, newest first (all statuses).

**Requires:** `Authorization: Bearer <firebase-token>`

**Response:** Array of `ListingRead` objects.

---

### `POST /listings/{listing_id}/photos`
Generates a presigned PUT URL for direct R2 upload. Returns the final public URL. Owner only.

**Requires:** `Authorization: Bearer <firebase-token>`

**Response:**
```json
{
  "upload_url": "https://...",
  "final_url": "https://pub.r2.dev/listings/uuid/photo.jpg"
}
```

Upload flow: `PUT upload_url` with `Content-Type: image/jpeg`, then call `/photos/confirm` with `final_url`. Presigned URL expires in 10 minutes. Maximum 10 photos per listing. Returns 503 if R2 credentials are not configured.

---

### `POST /listings/{listing_id}/photos/confirm`
Appends a confirmed photo URL to the listing's `photo_urls` array. Call this after the direct R2 PUT succeeds. Owner only.

**Body:**
```json
{ "url": "https://pub.r2.dev/listings/uuid/photo.jpg" }
```

**Response:** Updated `ListingRead`.

---

### `DELETE /listings/{listing_id}/photos`
Removes one photo URL from `photo_urls`. Does **not** delete from R2. Owner only. **Status 204.**

**Body:**
```json
{ "url": "https://pub.r2.dev/listings/uuid/photo.jpg" }
```

---

### `ListingRead` schema

```json
{
  "id": "uuid",
  "seller_user_id": "uuid or null",
  "source_id": "autoscout",
  "title": "VW Golf 7 2019 Manual",
  "make": "Volkswagen",
  "model": "Golf",
  "year": 2019,
  "price": "9800",
  "currency": "EUR",
  "mileage": 72000,
  "location_text": "Tiranë",
  "transmission": "manual",
  "fuel_type": "petrol",
  "body_type": "hatchback",
  "description": "One owner...",
  "contact_phone": "+355691234567",
  "photo_urls": ["https://..."],
  "status": "active",
  "views_count": 14,
  "is_active": true,
  "created_at": "2026-05-18T10:00:00"
}
```

---

## Health

### `GET /health`
Checks DB and Redis connectivity. Returns `200` if both are up, `503` if either is down.

```json
{ "status": "ok", "db": true, "redis": true, "environment": "dev" }
```

### `GET /ready`
Lightweight readiness probe — just checks the DB. Used by Docker healthchecks.

---

## Admin (no auth — internal network only)

These endpoints are for QA and ops. They have no authentication — they should never be exposed to the public internet.

### `POST /admin/profiles/{profile_id}/run-match-now`
Manually triggers the full matching pipeline for one profile right now, without waiting for the scheduled 7:00 UTC run. Useful for testing and debugging.

**Response:**
```json
{
  "status": "ok",
  "profile_id": "uuid",
  "candidates": 18,
  "inserted": 12,
  "skipped": 6,
  "top_n": 5
}
```

| Field | Meaning |
|-------|---------|
| `candidates` | Listings that passed all filters |
| `inserted` | New match records written to DB |
| `skipped` | Listings already matched to this profile (30-day cool-down) |
| `top_n` | How many were marked `selected_for_delivery` |

---

### `GET /admin/matches/{match_id}/debug`
Returns the full pipeline trace for a match — what score it got, which step assigned it, the raw LLM reasoning, and the full listing details. Useful when a user says "why did I get this car?"

**Response:**
```json
{
  "match_id": "uuid",
  "profile_id": "uuid",
  "listing_id": "uuid",
  "score": 84,
  "score_source": "llm",
  "selected_for_delivery": true,
  "reasoning": "Manual transmission confirmed...",
  "summary": "2019 VW Golf 7 — €9,800 · 72 000 km · Tiranë",
  "delivery_status": "pending",
  "user_action": null,
  "listing": { ...full listing fields... }
}
```

---

### `GET /admin/costs/summary`
Shows LLM token usage and estimated USD cost for a rolling time window. Raises `budget_alert: true` if the total exceeds $50/day.

**Query params:**
| Param | Default | Description |
|-------|---------|-------------|
| `days` | 1 | How many days back to aggregate |

**Response:**
```json
{
  "period_days": 1,
  "total_estimated_cost_usd": 0.0031,
  "budget_alert": false,
  "breakdown": [
    {
      "endpoint": "matching/ranking",
      "calls": 3,
      "input_tokens": 8241,
      "output_tokens": 874,
      "estimated_cost_usd": 0.0025
    },
    {
      "endpoint": "/profiles/parse",
      "calls": 2,
      "input_tokens": 1402,
      "output_tokens": 310,
      "estimated_cost_usd": 0.0006
    }
  ]
}
```

---

## Summary Table

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/sync` | None | Sync Firebase user to DB |
| GET | `/me` | Bearer | Get current user |
| POST | `/profiles/parse` | Bearer | NL text → structured profile (preview only) |
| POST | `/profiles` | Bearer | Save a new search profile |
| GET | `/profiles` | Bearer | List all my profiles |
| GET | `/profiles/{id}` | Bearer | Get one profile |
| PATCH | `/profiles/{id}` | Bearer | Update profile fields |
| DELETE | `/profiles/{id}` | Bearer | Delete profile + its matches |
| POST | `/profiles/{id}/toggle` | Bearer | Pause / resume a profile |
| GET | `/profiles/{id}/matches` | Bearer | Paginated match history for a profile |
| GET | `/matches/{id}` | Bearer | Full match detail + listing |
| POST | `/matches/{id}/action` | Bearer | Record clicked / dismissed / saved |
| GET | `/health` | None | DB + Redis health check |
| GET | `/ready` | None | DB readiness probe |
| POST | `/admin/profiles/{id}/run-match-now` | None | Manually trigger pipeline |
| GET | `/admin/matches/{id}/debug` | None | Full pipeline trace for a match |
| GET | `/admin/costs/summary` | None | LLM token usage + cost estimate |
| POST | `/listings` | Bearer | Create a platform listing |
| GET | `/listings` | None | Browse active listings (paginated) |
| GET | `/listings/{id}` | None | Listing detail (increments views) |
| PATCH | `/listings/{id}` | Bearer | Update listing (owner only) |
| DELETE | `/listings/{id}` | Bearer | Soft-delete listing (owner only) |
| GET | `/me/listings` | Bearer | My listings (all statuses) |
| POST | `/listings/{id}/photos` | Bearer | Get presigned R2 upload URL |
| POST | `/listings/{id}/photos/confirm` | Bearer | Confirm photo after R2 PUT |
| DELETE | `/listings/{id}/photos` | Bearer | Remove a photo URL |
