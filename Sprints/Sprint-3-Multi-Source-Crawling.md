# Sprint 3 — Multi-Source Crawling

**Duration:** Weeks 5–6
**Theme:** Go from one source to four. Run crawls daily on a schedule. Deduplicate listings so we never store the same car twice.

---

## Goals

- 3 additional source adapters added (4 total), spanning Albanian classifieds and at least one regional source.
- Daily scheduler enqueues one job per `(active_profile × source)` combination.
- Hash-based deduplication prevents duplicate listings across sources.
- Per-source success rates visible in Grafana.
- Listings are normalized to a canonical schema regardless of source.

## Out of Scope

- LLM-based matching or ranking (Sprint 4)
- WhatsApp delivery (Sprint 5)
- Soft / embedding-based dedup (Sprint 4)

---

## Workstreams

### Source Adapters — Target List (Albania)

Implement 3 new adapters in addition to the Sprint 1 source. Final list to be confirmed with legal review from Sprint 0; suggested:

| # | Source | Tier | Strategy | Notes |
|---|--------|------|----------|-------|
| 1 | merrjep.al (from Sprint 1) | 1 | HTML parse | Already done |
| 2 | mobile.al | 1/2 | HTML parse | Largest Albanian classifieds for cars |
| 3 | gjirafa.com (autot section) | 2 | HTML parse | Big regional aggregator |
| 4 | njoftime.com / njoftime.al | 2 | HTML parse | Long-tail seller listings |

Stretch (if capacity): **autoscout24.com** for cross-border listings.

For each adapter:
- [ ] Implement `search(profile)` — translate search profile into the source's query params, paginate.
- [ ] Implement `parse(raw)` — return a `NormalizedListing` with all canonical fields.
- [ ] Unit tests with fixture HTML (committed to repo) — protect against silent regressions when the site changes.
- [ ] Integration test in CI that hits a recorded HTTP cassette (VCR.py).
- [ ] `health_check()` — fetch a known-good URL and return 200/HTML-shape check.

### Crawler — Anti-Blocking & Reliability

- [ ] Proxy rotation via Bright Data residential pool — random IP per request, sticky session optional per source.
- [ ] Playwright stealth plugin configured (`playwright-stealth` or equivalent) for JS-heavy sources.
- [ ] User-agent rotation from a curated list.
- [ ] Retry logic with exponential backoff: 3 tries, 2s/8s/30s base + jitter.
- [ ] Circuit breaker per source: after 5 consecutive failures, mark the source `unhealthy` for 1 hour and skip in scheduler.
- [ ] Respectful rate limit: max 1 request per source per 3 seconds per IP.
- [ ] Honor `robots.txt` where it does not block the whole site (defensive).

### Backend — Listing Normalization Service

- [ ] Finalize `listings` table schema (per Planner section 5.1):
  ```
  id, source_id, source_listing_id (unique with source_id),
  source_url, title, description,
  make, model, year, mileage, price, currency,
  location_lat, location_lng, location_text,
  photos (jsonb),
  seller_name, seller_phone, seller_type,
  raw_payload (jsonb),
  embedding (vector(384)),  -- nullable, populated in Sprint 4
  dedup_hash (string, indexed),
  first_seen_at, last_seen_at, is_active
  ```
- [ ] Pgvector extension installed (column added now, populated Sprint 4).
- [ ] **Currency normalization** — convert ALL ↔ EUR using a daily exchange-rate cron pulling from a stable source (ECB or Bank of Albania).
- [ ] **Mileage normalization** — km only; reject listings with miles in V1 (Albanian market is km-native).
- [ ] **Make/model canonicalization** — small lookup table (`VW`, `Volkswagen`, `Volks` → `Volkswagen`); seeded with top 30 makes.
- [ ] **Photo handling** — record source URLs; do NOT download yet (deferred to Sprint 5 when WhatsApp needs them).
- [ ] Upsert logic: on `(source_id, source_listing_id)` conflict, update `last_seen_at` and any changed fields; keep `first_seen_at` stable.

### Backend — Deduplication v1 (Hash-Based)

- [ ] `dedup_hash` composition:
  ```
  sha256(lower(make) | lower(model) | year | round(price / 50) | round(lat, 2) | round(lng, 2))
  ```
  The rounding tolerates small price/location drift while still catching obvious reposts.
- [ ] Listings ingestion: if `dedup_hash` already exists on a recent (last 30 days) active listing, mark new arrival as `duplicate_of=<existing_id>` and do not create a new row.
- [ ] Cross-source dedup: same hash from a different source → keep both rows but link via `duplicate_of` (we'll need both for source-attribution analytics).

### Backend — Scheduler

- [ ] Celery Beat schedule: every hour, check for profiles whose `delivery_time_local` window opens in the next 4 hours; enqueue one crawl job per `(profile, source)`.
- [ ] **Jitter:** randomize each job's execution time within a 30-minute window to spread proxy load and avoid hammering sources.
- [ ] Job idempotency: dedupe by `(profile_id, source_id, run_date)` so re-running the scheduler doesn't double-enqueue.
- [ ] Per-source concurrency cap (Celery routing): max 5 concurrent workers per source.

### Ops Dashboard

- [ ] Internal-only admin endpoint: `GET /admin/sources` — returns per-source health, last 24h success rate, last successful crawl, listings ingested.
- [ ] Internal-only admin endpoint: `GET /admin/crawl-runs?profile_id=...` — full crawl run history for a profile.
- [ ] Grafana dashboard:
  - Crawl success rate per source (target: >80%)
  - Listings ingested per source per day
  - Dedup rate (% of incoming listings rejected as duplicates)
  - Proxy bandwidth consumed per source
  - Circuit-breaker trips per source

### Monitoring & Alerts

- [ ] Alert: source success rate < 80% over 1 hour → page on-call.
- [ ] Alert: crawler queue depth > 1000 → page on-call.
- [ ] Alert: zero listings ingested from any source in 24h → email ops.

---

## Definition of Done

1. At 06:00 UTC on a weekday, the scheduler enqueues jobs for the 3 test profiles created by the team.
2. Within 4 hours, all 4 source adapters have run for each profile.
3. The `listings` table has hundreds of new rows, deduplicated by hash.
4. Grafana shows per-source success rate >80% over the past 24h.
5. Admin endpoint shows the latest crawl run per source with a green health badge.

---

## Risks & Watch-Outs

- **Sources will fight back.** Expect at least one adapter to break or get blocked during the sprint. Plan a half-day of buffer per source for selector updates.
- **Proxy bandwidth burn during dev.** Set a hard cap on the proxy account ($300/month) and alert at 75%.
- **PostGIS distance queries can be slow** without indexes. Confirm a GiST index on the `geography` column ships with the migration.
- **Cross-source dedup conflicts with source attribution.** Decide upfront: when the same car shows on two sources, which gets shown to the user? Default: lower-tier-id wins (i.e., the more permissive source).

---

## Dependencies

- Sprint 2 search profiles in place — needed as crawl input.
- Proxy provider quota provisioned in Sprint 0.

---

## Next Sprint Preview

[Sprint 4 — Matching and Ranking](Sprint-4-Matching-and-Ranking.md): take the river of normalized, deduplicated listings and turn them into a ranked match list per user, using a mix of deterministic filters and LLM scoring.
