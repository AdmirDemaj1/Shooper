# Sprint 4 — Matching and Ranking ✅

**Duration:** Weeks 7–8
**Theme:** From a river of normalized listings, produce a small ranked set of good matches per user per day.

---

## What Was Implemented

### ✅ Matching Pipeline (`autoscout/matching/`)

Full 4-step pipeline in `pipeline.py`:

1. **Strict filter** (`filters.py`) — drops listings outside hard bounds before any LLM call
   - Price min/max (handles string prices and currency gracefully)
   - Year min/max
   - Mileage max
   - Transmission, fuel type, body type (only filtered when both profile and listing have values)

2. **Geo filter** (`filters.py`) — Albanian city coordinate lookup + Haversine distance
   - Covers 30+ Albanian cities with lat/lon coordinates
   - Listings with unrecognised location pass through (LLM penalises them)
   - Skipped entirely if profile has no location set

3. **Already-seen suppression** (`filters.py`) — 30-day cool-down per (profile, listing) pair
   - Prevents the same listing resurfacing in daily digests
   - Implemented as a DB join, not in-memory

4. **LLM relevance scoring** (`scorer.py`) — Claude Sonnet with deterministic fallback
   - Batched up to 20 listings per API call
   - **Anthropic prompt caching** on system prompt + profile description prefix (reduces cost on repeated runs)
   - **Redis cache** with 7-day TTL keyed on `(profile_hash, listing_id)`
   - **Deterministic fallback** when Claude is unavailable — scores by year, mileage, price ratio
   - Token usage logged to `llm_calls` table after every call

5. **Top-N selection** — default 5, configurable 3–10 per profile
   - Tie-break: higher score → lower price → newer listing
   - All scored candidates persisted; only top-N marked `selected_for_delivery`

### ✅ Database Schema

Migration `0006` — matches table extended with:
- `score_source` — `'llm'` | `'fallback'`
- `summary` — one-line WhatsApp card caption (max 100 chars)
- `selected_for_delivery` — boolean flag for top-N
- `delivery_channel`, `delivery_status`, `user_action`
- Unique constraint `(search_profile_id, listing_id)`
- Indexes on `(search_profile_id, delivered_at)` and `(search_profile_id, created_at)`

Migration `0007` — listings table extended with:
- `transmission`, `fuel_type`, `body_type` — used by hard-bounds filter

### ✅ Match History API (`autoscout/matches/router.py`)

- `GET /profiles/{id}/matches` — cursor-paginated match list, newest first
- `GET /matches/{id}` — full match detail with listing fields + LLM reasoning
- `POST /matches/{id}/action` — records `clicked` / `dismissed` / `saved`
- All endpoints enforce ownership (users can only see their own matches)

### ✅ Admin / QA Endpoints (`main.py`)

- `POST /admin/profiles/{id}/run-match-now` — manually triggers full pipeline
- `GET /admin/matches/{id}/debug` — full pipeline trace for a match
- `GET /admin/costs/summary?days=N` — LLM token usage + estimated USD cost, budget alert at $50/day

### ✅ Ranking Prompt (`autoscout-prompts/ranking/v1.md`)

5-tier scoring guide (0–29 poor → 90–100 excellent) covering:
- Free-text criteria matching
- Listing quality signals
- Make/model precision
- Location preference
- Price positioning
- Mileage/age ratio

### ✅ Ranking Regression Test Suite (`autoscout-prompts/`)

- `ranking/test_cases.json` — 50 hand-graded (profile, listing) pairs covering excellent/good/adequate/weak/poor cases across diverse scenarios
- `test_harness.py` — CLI runner with MAE gate (≤ 8 points), `--verbose` and `--fail-fast` flags

### ✅ Mobile — Match Viewing (`autoscout-mobile/`)

- History tab — matches grouped by date (Today / Yesterday / Earlier this week), score chips colour-coded green/orange/red, pull-to-refresh
- Match detail screen — specs card, collapsible LLM reasoning, dismiss/save actions, "Open original listing" button
- API client methods for `listForProfile`, `get`, `recordAction`

### ✅ Infrastructure Fixes

- Celery queue collision resolved — crawler uses `crawler` queue, backend-worker uses `backend` queue; `task_default_queue` set in both worker configs and `-Q` flags added to docker-compose
- Postgres image switched to `postgres:16` (native ARM64 on Apple Silicon, no Rosetta)
- `API.md` created and fully documented

---

## Definition of Done — Status

| Criterion | Status |
|---|---|
| Pipeline produces deduplicated, ranked matches | ✅ |
| Top 5 per profile visible in History tab with scores + reasoning | ✅ |
| Re-running next day doesn't re-surface old matches | ✅ |
| LLM cost tracked and visible | ✅ via `/admin/costs/summary` |
| Fallback scoring works when Claude unavailable | ✅ deterministic scorer + `score_source='fallback'` |

---

## What Was Deliberately Skipped

See `NotImplemented/Sprint-4-NotImplemented.md`.

---

## Quick Test Commands

```bash
# Trigger pipeline for a profile
curl -X POST http://localhost:8000/admin/profiles/<profile-id>/run-match-now

# Check LLM cost
curl http://localhost:8000/admin/costs/summary

# Debug a specific match
curl http://localhost:8000/admin/matches/<match-id>/debug

# Run ranking regression tests (~$0.05 one-time)
ANTHROPIC_API_KEY=sk-... python autoscout-prompts/test_harness.py --verbose
```

---

## Next Sprint

[Sprint 5 — WhatsApp Integration](../Sprints/Sprint-5-WhatsApp-Integration.md): wire the `selected_for_delivery` matches to the WhatsApp Business Cloud API, get templates approved, and handle inbound opt-outs.
