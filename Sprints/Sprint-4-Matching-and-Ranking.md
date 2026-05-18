# Sprint 4 — Matching and Ranking

**Duration:** Weeks 7–8
**Theme:** From a river of normalized listings, produce a small ranked set of *good* matches per user per day. Deterministic filters do the bulk of the work; the LLM scores ambiguous candidates.

---

## Goals

- Strict filters remove listings outside hard bounds (price, year, mileage, location radius).
- LLM relevance scoring produces a 0–100 score and short reasoning per candidate.
- Embedding-based soft dedup catches near-duplicates the hash dedup misses.
- Matches are persisted with score + reasoning, ready for delivery in Sprint 5.
- Cost per active user per day is tracked and within the $0.10–$0.15 LLM budget.
- Mobile users can browse their match history before WhatsApp delivery exists.

## Out of Scope

- WhatsApp delivery (Sprint 5)
- User feedback signals on matches (V2)

---

## Workstreams

### Backend — Matching Pipeline

The pipeline runs after a crawl batch completes for a profile:

```
crawled listings
   │
   ▼
[1] strict filter   ──► drop listings outside hard bounds
   │
   ▼
[2] geo filter      ──► drop listings outside radius
   │
   ▼
[3] already-seen    ──► drop listings already in `matches` for this profile
   │
   ▼
[4] soft dedup      ──► embedding similarity vs recent listings; pick canonical
   │
   ▼
[5] LLM ranking     ──► batched scoring + reasoning + summary
   │
   ▼
[6] top-N selection ──► default N=5, configurable per profile
   │
   ▼
matches table       ──► ready for Sprint 5 delivery
```

#### [1] Strict Filter

- [ ] Filter out listings where `price > price_max` or `price < price_min` (per currency conversion).
- [ ] Filter out listings where `year < year_min` or `year > year_max`.
- [ ] Filter out listings where `mileage > mileage_max`.
- [ ] Filter out body_type / transmission / fuel_type mismatches when the profile specifies them.
- [ ] Implement as a single SQL query for speed.

#### [2] Geo Filter

- [ ] PostGIS `ST_DWithin` query on the profile's location point + radius.
- [ ] Listings with missing/unparseable location are kept but flagged `location_uncertain=true`; the LLM step uses that flag in scoring.

#### [3] Already-Seen Suppression

- [ ] Join against `matches(search_profile_id, listing_id)` and exclude any pair already present.
- [ ] Configurable "cool-down": even if the listing re-appears from another source, suppress for 30 days from last delivery.

#### [4] Soft Dedup via Embeddings

- [ ] Embedding service: call Voyage AI `voyage-3-lite` (or OpenAI `text-embedding-3-small`) on `title + description` for each new listing during ingestion. Store in `listings.embedding`.
- [ ] On match candidate selection: for each candidate, ANN query (pgvector cosine distance) against listings already matched to this profile in the last 30 days.
- [ ] If similarity > 0.92, treat as duplicate and drop.
- [ ] If 0.85 < similarity ≤ 0.92, send pair to LLM tiebreaker prompt: "Are these the same car?" with structured yes/no/uncertain output.

#### [5] LLM Relevance Scoring

- [ ] Endpoint inside the backend: `score_listings(profile, listings) -> List[Score]`.
- [ ] Batch up to 20 listings per Claude call.
- [ ] Tool-use schema:
  ```json
  {
    "scores": [
      {"listing_id": "...", "score": 0-100, "reasoning": "...", "summary": "..."}
    ]
  }
  ```
- [ ] Prompt versioned at `autoscout-prompts/ranking/v1.md`.
- [ ] **Caching:** cache `(profile_hash, listing_id) -> score` for 7 days in Redis. Profile hash includes only fields the LLM considers (free_text_criteria + bounds).
- [ ] **Fallback:** if Claude is unavailable or rate-limited, use a deterministic score = `100 - normalized_distance_from_profile_centroid` (price + year + mileage Euclidean distance). Mark match with `score_source='fallback'`.

#### [6] Top-N Selection

- [ ] Default N=5, configurable per profile (3–10).
- [ ] Tie-break by: (1) higher LLM score, (2) lower price, (3) more recent listing.
- [ ] Persist all candidates that survived filters into `matches`, but mark `selected_for_delivery` only on the top N.

### Backend — `matches` Table

Finalize the schema:

```
id (uuid, pk)
search_profile_id (fk)
listing_id (fk)
relevance_score (int 0-100)
score_source ('llm' | 'fallback' | 'tiebreaker')
llm_reasoning (text)
summary (text)                 -- short blurb for the WhatsApp card
selected_for_delivery (bool)
delivered_at (timestamp, nullable)
delivery_channel (string, nullable)  -- 'whatsapp' in Sprint 5
delivery_status (enum: pending|sent|delivered|read|failed)
user_action (enum: null|clicked|dismissed|saved)
created_at, updated_at
```

Indexes:
- `(search_profile_id, delivered_at)`
- `(search_profile_id, created_at desc)` for history view
- `(listing_id)` for back-references

### Backend — Match History API

- [ ] `GET /profiles/{id}/matches?limit=20&cursor=...` — paginated list of matches for a profile, newest first.
- [ ] `GET /matches/{id}` — full match detail (listing fields + score + reasoning + summary).
- [ ] `POST /matches/{id}/action` — record `clicked` / `dismissed` / `saved` (for V2 feedback loop).

### Mobile — Match Viewing

- [ ] **History tab** redesigned:
  - Grouped by date ("Today," "Yesterday," "Earlier this week").
  - Each row: top match's photo, profile name, "5 new matches" subtitle, score chip.
  - Tap row → drills into profile-level match list.
- [ ] **Match detail screen:**
  - Photo carousel
  - Title, price, year, mileage, location
  - Score chip + LLM reasoning (collapsible)
  - "Open original listing" button (external browser deep link)
  - "Save" and "Dismiss" actions (write `user_action`)
- [ ] React Query caching with stale-while-revalidate; pull-to-refresh.

### AI/ML — Quality & Cost

- [ ] **Ranking prompt regression suite:** 50 hand-graded (profile, listing) pairs with expected score ranges. CI gate: any change must keep MAE within 8 points of the baseline.
- [ ] **Cost dashboard** (Grafana):
  - LLM tokens per day per feature (parsing, ranking, dedup tiebreaker, summary)
  - Average LLM cost per active user per day (target: <$0.15)
  - Cache hit rate per feature (target: >40% on ranking after 7 days)
- [ ] **Prompt caching** via Anthropic prompt caching API on the system prompt + profile description (large stable prefix); cache the small variable suffix per batch.
- [ ] Alert: LLM spend >$50/day during dev or >1.5x budget per user once live.

### Internal Tools

- [ ] Admin endpoint: `POST /admin/profiles/{id}/run-match-now` — manually trigger the full pipeline for QA.
- [ ] Admin endpoint: `GET /admin/matches/{id}/debug` — full pipeline trace: which filters passed, which step assigned the score, raw LLM response.

---

## Definition of Done

For each of 5 internal test profiles:

1. After the daily crawl, the pipeline produces a deduplicated, ranked list of matches.
2. Top 5 matches per profile are visible in the mobile History tab with photos, scores, and the LLM's reasoning visible.
3. Re-running the pipeline the next day does NOT re-surface yesterday's matches.
4. LLM cost per profile per day, averaged across the 5 profiles, is **under $0.15**.
5. The fallback (rule-based) path is exercised in a chaos test (deliberately disabled Claude key) and still produces a sensible ranking.

---

## Risks & Watch-Outs

- **LLM cost blowup if caching misconfigured.** Confirm prompt cache hit rate is >40% by end of week 1.
- **Embedding quality on car-listing text.** If `voyage-3-lite` underperforms, fall back to OpenAI `text-embedding-3-small`. Don't try to fine-tune anything in V1.
- **Bias in LLM scoring** — the model may overweight free-text fluff over hard specs. Mitigate by emphasizing in the prompt that strict-filter bounds are *already enforced*, so it should focus on free-text criteria + listing quality signals.
- **Pgvector ANN at scale** — fine at V1, but make sure the IVFFlat or HNSW index is created with parameters tuned for ~100k vectors.

---

## Dependencies

- Sprint 3 crawler delivering normalized listings reliably.
- Sprint 2 search profiles with `free_text_criteria` populated.
- Claude API quota raised if needed (request limit increases early in the sprint).

---

## Next Sprint Preview

[Sprint 5 — User Listings](Sprint-5-User-Listings.md): let sellers post directly on AutoScout; platform listings feed the same AI pipeline and trigger immediate matching for buyers.
