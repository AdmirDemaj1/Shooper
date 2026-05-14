# Sprint 6 — Polish, Hardening, Internal Dogfood

**Duration:** Weeks 11–12
**Theme:** Take the working end-to-end system and harden it. Load test, security review, run unattended for 7 days, get every internal staffer using it daily.

---

## Goals

- The system survives 10x V1 expected load without falling over.
- Security audit and privacy review complete; no critical findings open.
- Internal staff (~20 dogfood users) receive daily digests for 7 consecutive days with zero ops interventions.
- All known P0/P1 bugs from prior sprints closed.
- Onboarding, app store assets, and support process ready for Sprint 7 beta.

## Out of Scope

- Any new features beyond polish (V1 scope is now frozen).
- External beta users (Sprint 7).

---

## Workstreams

### Reliability & Error Handling

- [ ] **Error handling sweep** through every backend endpoint:
  - All exceptions caught and mapped to structured error responses.
  - User-facing error messages localized (sq + en).
  - No 500s without a Sentry alert.
- [ ] **Crawler graceful degradation:**
  - One source failing must never block the others.
  - Per-source timeout (90s hard cap).
  - Listing-level isolation: a single malformed listing doesn't kill the batch.
- [ ] **LLM service degradation:**
  - Claude API down → fallback ranking + Sentry alert.
  - Rate limited → exponential backoff + fallback.
  - Token budget exceeded → suspend non-essential calls (summarization first, ranking second, parsing last).
- [ ] **WhatsApp delivery degradation:**
  - Provider 5xx → retry queue with 1h cap.
  - Provider 4xx (template issue) → page on-call immediately.
  - User suppressed mid-batch → skip cleanly.

### Rate Limiting & Abuse Prevention

- [ ] Public API rate limits (per user, sliding window):
  - `POST /profiles/parse` — 30/hour (LLM cost).
  - `POST /profiles` — 20/day.
  - `POST /auth/sync` — 10/min.
  - Default — 100/min.
- [ ] IP-level rate limit on `/auth/*` to mitigate enumeration.
- [ ] Captcha (hCaptcha) on signup if the same IP exceeds 5 OTP requests in an hour.

### Load Testing

Target: handle **10x V1 launch load** without degradation.

- [ ] Define V1 baseline: 500 users × 2 profiles × 4 sources = 4,000 crawl jobs/day. 10x = 40,000/day.
- [ ] Load test plan (k6 or Locust scripts in a new `perf/` directory or as part of CI):
  - **Scenario A:** 5,000 concurrent profile reads via API.
  - **Scenario B:** 40,000 crawl jobs enqueued in 1 hour; verify queue drains within 4 hours.
  - **Scenario C:** 5,000 WhatsApp dispatch jobs in 30 min; verify provider rate limits respected.
- [ ] Identify bottlenecks: DB CPU, Redis memory, proxy bandwidth, LLM rate limits.
- [ ] Tune: DB connection pool sizes, worker concurrency, Celery prefetch counts.
- [ ] Document the maximum supported load and the next-bottleneck triggers.

### Security Audit

- [ ] **Auth flow review:**
  - Firebase token verification on every protected route (not just middleware happy path).
  - Token replay window minimized.
  - No PII in logs (phone numbers hashed in structured logs).
- [ ] **Data access review:**
  - Every `search_profiles` and `matches` query filtered by `user_id`.
  - Admin endpoints behind a separate Firebase admin claim, not just network ACL.
  - SQL injection scan (sqlmap or equivalent) against the public API.
- [ ] **Secrets handling review:**
  - No secrets in code, env files, or container images (verify with `gitleaks`).
  - Secrets manager rotation policy documented; rotated at least once before launch.
- [ ] **Webhook signature verification:** WhatsApp webhook signature checked on every request; reject unsigned.
- [ ] **Mobile app:**
  - API keys in `expo-secure-store`, not in code.
  - Deep link validation (no open-redirect via `?next=`).
  - Certificate pinning evaluated (V2 candidate; documented decision).
- [ ] **Dependency scan:** `pip-audit`, `npm audit` — no critical CVEs unresolved.

### Privacy & Compliance Review

- [ ] **Privacy policy v1** published at `autoscout.al/privacy`, linked from app + onboarding.
- [ ] **Data retention:**
  - `users` — retained while account active; 30 days post-deletion request.
  - `listings` — 90 days from `last_seen_at`, then archived.
  - `matches` — 180 days from delivery.
  - `whatsapp_messages` — 30 days from sent.
  - LLM call logs (`llm_calls`) — 30 days.
- [ ] **DSAR flow:** documented internal process for "give me my data" and "delete my data" (manual for V1, automated in V2).
- [ ] **Albania DPA (Law 9887) compliance check:**
  - Lawful basis for processing documented (consent for WhatsApp, contract for service).
  - Data controller contact info in privacy policy.
  - Cross-border transfers (Claude API → US) documented with standard contractual clauses if needed.
- [ ] **GDPR alignment** (Albania is on the EU accession track — get ahead of it).

### Observability Maturity

- [ ] Every service has a `/health` and `/ready` endpoint (Kubernetes liveness/readiness probes).
- [ ] Single Grafana "Mission Control" dashboard combining:
  - Daily active users
  - Crawl success rate per source
  - LLM cost per user per day
  - WhatsApp delivery rate
  - Error rate per service
- [ ] SLO definitions (track but don't alert in V1):
  - API p95 latency < 500ms
  - Daily digest sent within 30 min of scheduled time, 99% of the time
- [ ] On-call rotation activated; runbooks for every alert linked from the page.

### Internal Dogfood Program

- [ ] Onboard ~20 internal staff (engineers + extended team + friends) as dogfood users.
- [ ] Each creates at least one real search profile.
- [ ] **Daily standup question:** "Did you get a digest, and was it useful?"
- [ ] Feedback channel: dedicated Slack channel `#autoscout-dogfood` + a Typeform after day 3 and day 7.
- [ ] **Track explicitly:**
  - % of digests rated useful
  - Top complaints (listing freshness, relevance, photo quality, etc.)
  - Bugs reproduced and filed
- [ ] **7-day unattended run:** starting day 8 of the sprint, no manual interventions allowed. Anything that requires ops attention = a bug to file, not a manual fix.

### App Store Preparation

- [ ] App store listing copy (en + sq).
- [ ] Screenshots (iPhone + iPad + Android, multiple sizes per store guidelines).
- [ ] Privacy nutrition labels (Apple) and Data Safety form (Google) filled out — must match actual data handling.
- [ ] App review notes prepared explaining scraping and data use clearly (preempt rejection).
- [ ] Support email + URL live: `support@autoscout.al`.
- [ ] **Submit to TestFlight + Play Internal Testing track refreshed** for Sprint 7 beta users.

### Support & Documentation

- [ ] Public FAQ + help center pages (auth issues, WhatsApp not received, pausing, deleting account).
- [ ] Internal support runbook: how to look up a user, common issue triage, escalation paths.
- [ ] Status page set up at `status.autoscout.al` (BetterStack or similar).

---

## Definition of Done

1. **The system runs unattended for 7 consecutive days** with no human intervention required. Any intervention during this window resets the clock.
2. **All internal dogfood users** receive daily digests; >70% report the digests are meaningfully relevant.
3. **Load test scenarios A, B, C** all pass without manual scaling.
4. **Security audit** complete; zero critical findings open; medium findings have agreed remediation plans.
5. **Privacy policy live**, data retention enforced via cron jobs.
6. **App store assets** ready; review notes drafted.
7. **All P0/P1 bugs** from prior sprints closed.

---

## Risks & Watch-Outs

- **Dogfood reveals fundamental relevance issues.** Be ready to spend mid-sprint time on prompt tweaks. The Sprint 4 cost dashboard makes this safe to iterate on.
- **A source breaks during the 7-day unattended run.** That's a test failure, not "expected." It means the circuit breaker / monitoring isn't doing its job. Treat as P0.
- **Scope creep from internal feedback.** Anything beyond bug fixes goes to V2. Be ruthless — the buffer in week 15–16 is for *unknown unknowns*, not feature requests.
- **Security audit finds something gnarly.** Have a half-engineer of buffer reserved for unplanned hardening work.

---

## Dependencies

- All prior sprints complete.
- Apple Developer + Google Play accounts provisioned (Sprint 0).

---

## Next Sprint Preview

[Sprint 7 — Beta Launch](Sprint-7-Beta-Launch.md): 50–100 external users in Albania, real money on the line, daily monitoring, prompt and adapter iteration based on actual usage.
