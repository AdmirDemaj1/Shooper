# Sprint 4 — Not Implemented (Deferred)

Items from the Sprint 4 spec that were deliberately skipped and why.

---

## Embedding-Based Soft Dedup (Pipeline Step 4)

**What the sprint asked for:** Generate embeddings for each listing (Voyage AI or OpenAI), store them in a `listings.embedding` vector column, and on each matching run do an ANN cosine similarity query against listings already matched to that profile. Drop duplicates above 0.92 similarity; send borderline pairs (0.85–0.92) to an LLM tiebreaker.

**Why skipped:** The use case — same physical car listed on two different Albanian sites — is valid but rare at V1 scale with 4 sources. The existing hash-based dedup from Sprint 3 handles exact duplicates. Showing the same car twice from two different sources is acceptable behaviour for V1 (the user sees two prices and two source links, which is actually useful).

Adding embeddings would require:
- A third external API service (Voyage AI or OpenAI embeddings)
- A new `pgvector` migration
- Ongoing cost per listing ingested

**When to revisit:** V2, once user feedback shows duplicate listings are a significant complaint. At that point, OpenAI `text-embedding-3-small` is the recommended provider since an OpenAI key will likely already exist for other features.

---

## PostGIS `ST_DWithin` Geo Filter

**What the sprint asked for:** Replace the Python Haversine geo filter with a proper PostGIS `ST_DWithin` SQL query.

**Why skipped:** The app operates in Albania only. All 30+ relevant cities have hardcoded coordinates in `filters.py`. The Haversine implementation is accurate to within 0.1% for the distances involved (~500km country max). PostGIS is not in the current postgres image (`postgres:16`) and adding it adds deployment complexity.

**When to revisit:** If the app expands to a second country where hardcoding city coordinates is impractical. At that point, switch postgres image to `postgis/postgis:16` and migrate to `ST_DWithin`.

---

## Grafana Cost Dashboard

**What the sprint asked for:** A Grafana dashboard with panels for LLM tokens/day/feature, average cost per active user, and cache hit rate.

**Why skipped:** Grafana requires a separate infrastructure service (Grafana + Prometheus or Loki). At V1 beta scale (≤500 users) the `GET /admin/costs/summary` endpoint provides sufficient visibility. Grafana adds significant ops overhead for marginal benefit at this scale.

**What exists instead:** `GET /admin/costs/summary?days=N` endpoint aggregates token usage and estimated cost from the `llm_calls` table, with a `budget_alert` flag when daily spend exceeds $50.

**When to revisit:** Sprint 6 (Polish & Hardening) when load testing and monitoring infrastructure is being set up anyway. Wire `llm_calls` counts into Prometheus metrics at that point.

---

## LLM Cost Alerts

**What the sprint asked for:** Automated alerts when LLM spend exceeds $50/day during dev or 1.5× per-user budget once live.

**What exists:** A `budget_alert: true` flag in the cost summary endpoint, and a warning log line when a single scoring run exceeds 100k tokens.

**What's missing:** Push alerting (email/Slack/PagerDuty) when the threshold is crossed.

**When to revisit:** Sprint 6 alongside the broader observability and alerting setup.

---

## Ranking Prompt CI Gate

**What the sprint asked for:** The regression test suite integrated into CI (GitHub Actions), blocking merges if MAE > 8 points.

**What exists:** The test harness runs manually (`python autoscout-prompts/test_harness.py`). The 50 test cases and MAE gate logic are fully implemented.

**What's missing:** A GitHub Actions workflow that runs the harness on PRs touching `autoscout-prompts/ranking/`.

**When to revisit:** Sprint 6 when CI/CD hardening is in scope. The harness is already a standalone script — wiring it into Actions is a 20-line YAML file.
