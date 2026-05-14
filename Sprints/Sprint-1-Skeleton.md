# Sprint 1 — Skeleton

**Duration:** Weeks 1–2
**Theme:** Stand up the minimum scaffold across all components so the team can work in parallel from Sprint 2 onward.

---

## Goals

- A user can sign up on the mobile app via phone OTP and their record lands in PostgreSQL.
- A manual crawler trigger pulls listings from one Tier 1 Albanian source into the dev database.
- Every component (mobile, backend, crawler) is deployed to `dev` and visible end-to-end.

## Out of Scope

- Search profile creation (Sprint 2)
- Multi-source crawling (Sprint 3)
- Any matching, ranking, or LLM work (Sprint 4)
- WhatsApp delivery (Sprint 5)

---

## Workstreams

### Backend — FastAPI Service

- [ ] FastAPI project skeleton with structured logging (JSON to stdout), Sentry, and Datadog APM hooks.
- [ ] `/health` endpoint returning DB + Redis ping status.
- [ ] Pydantic settings module reading from env / Secrets Manager.
- [ ] Alembic migrations baseline with initial tables:
  - `users` (id, phone_number, whatsapp_opt_in, country, locale, created_at, updated_at)
  - `search_profiles` (skeleton only — full schema in Sprint 2)
  - `listings` (skeleton only — full schema in Sprint 3)
  - `matches` (skeleton only — full schema in Sprint 4)
- [ ] Firebase Auth integration: middleware that verifies the Firebase ID token from `Authorization: Bearer <token>`.
- [ ] `POST /auth/sync` — called by mobile after OTP; upserts user row from Firebase claims.
- [ ] `GET /me` — returns the current user.
- [ ] Deploy to Railway via GitHub integration; reachable at `https://api.dev.autoscout.al`.

### Mobile — React Native + Expo

- [ ] Expo SDK initialized; iOS + Android builds green on EAS.
- [ ] Environment config: `dev` / `staging` / `prod` API URLs via Expo config.
- [ ] **Onboarding flow:**
  - Welcome screen
  - Phone number entry (country prefix locked to +355 for V1)
  - OTP entry (6-digit input, autofill on iOS/Android where supported)
  - Loading + error states
- [ ] Firebase Auth SDK integrated for phone OTP.
- [ ] On successful OTP, call `POST /auth/sync` with the Firebase token.
- [ ] **Bottom-tab navigation** (post-auth):
  - **Searches** — empty state: "Create your first search"
  - **History** — empty state: "Matches will appear here"
  - **Settings** — placeholder with sign-out button
- [ ] Zustand store for auth state; React Query client configured with auth header injection.
- [ ] Build a TestFlight + Play Internal Testing track for the team.

### Crawler — Worker Template

- [ ] Worker container base image (Python 3.12 + Playwright + httpx + Celery).
- [ ] Celery worker connecting to Redis (dev) and picking from a `crawl` queue.
- [ ] **Source adapter interface** (abstract base):
  ```python
  class SourceAdapter:
      name: str
      country: str
      def search(self, profile: SearchProfileDTO) -> Iterator[RawListing]: ...
      def parse(self, raw: RawListing) -> NormalizedListing: ...
      def health_check(self) -> bool: ...
  ```
- [ ] First Tier 1 Albanian source adapter implemented end-to-end (target: **merrjep.al** or **mobile.al** — pick whichever has the cleaner HTML/API). Persist normalized listings to the `listings` table.
- [ ] CLI command: `python -m crawler.run --source=<name> --profile=<id>` for manual triggers.
- [ ] Basic Prometheus counters: `crawl_attempted_total`, `crawl_succeeded_total`, `listings_persisted_total`.

### DevOps / Infrastructure

- [ ] Railway project connected to GitHub repos (auto-deploys on merge to main).
- [ ] Environment variables configured in Railway dashboard for each service.
- [ ] DNS records for `api.dev.autoscout.al` pointing to Railway's DNS.
- [ ] Sentry SDK wired in all three services.
- [ ] (Optional) Sentry dashboards stubbed (one per service).

### Design

- [ ] Final design system tokens (color, type, spacing) exported to a shared `design-tokens` package consumable by RN.
- [ ] High-fidelity onboarding screens.
- [ ] Empty-state illustrations for Searches / History tabs.

---

## Definition of Done

A demo on Friday of Week 2 shows the following live in `dev`:

1. Engineer opens the Expo dev build on a real phone.
2. Enters Albanian phone number, receives OTP via SMS, signs in.
3. Sees the empty Searches / History / Settings tabs.
4. Backend logs show the `/auth/sync` and `/me` calls.
5. Engineer runs `python -m crawler.run --source=merrjep --profile=<test_profile_id>` locally; listings appear in the dev `listings` table.
6. `kubectl logs` shows structured JSON logs from all three services.

---

## Risks & Watch-Outs

- **Firebase phone OTP in Albania** — verify SMS delivery actually works for +355 numbers; some carriers have spotty support. Have a test SIM on hand.
- **Expo SDK + Firebase native modules** — config plugins can be fiddly. Budget a half-day for a dev build that includes the native Firebase pieces.
- **The first source adapter is a learning exercise** — expect to throw away v1 selectors when the site updates. Keep the adapter narrow and well-tested.

---

## Dependencies

- All Sprint 0 deliverables complete.
- Firebase Auth phone provider verified for +355.

---

## Next Sprint Preview

[Sprint 2 — Search Profile Creation](Sprint-2-Search-Profile-Creation.md): build the core flow where a user defines what car they're looking for, both via form and via natural-language input.
