# AutoScout Implementation Status

## Sprint 2 — Search Profile Creation ✅ COMPLETE (Backend)

### What Works End-to-End (Verified)
1. ✅ **Search Profile CRUD**:
   - `POST /profiles` — create profile (max 10 active per user enforced)
   - `GET /profiles` — list user's profiles (newest first)
   - `GET /profiles/{id}` — read single profile
   - `PATCH /profiles/{id}` — partial update
   - `DELETE /profiles/{id}` — hard delete (cascades to matches), 204
   - `POST /profiles/{id}/toggle` — flip `is_active`
   - All endpoints user-scoped via `get_db_user` — no cross-tenant leaks

2. ✅ **Natural Language Parser**:
   - `POST /profiles/parse` — parses Albanian/English free text into structured `SearchProfileCreate`
   - Uses Claude Sonnet 4.6 with forced tool use (`tool_choice: {type: "tool", name: "create_search_profile"}`)
   - Returns `confidence_scores` per field, `low_confidence_fields` list, and `needs_review` flag
   - Nominatim geocoding: place name ("Tiranë") → lat/lng, falls back without "Albania" qualifier
   - System prompt versioned at `autoscout-prompts/profile_parser/v1.md`

3. ✅ **Database**:
   - Migration 0003 applied: all search profile fields added (make, model, year range, price range, currency, mileage, location lat/lng, radius, body_type, transmission, fuel_type, free_text_criteria, delivery_time_local, timezone)
   - PostGIS deferred to Sprint 4 — location stored as plain Float (sufficient for Sprint 2–3)

### ✅ Implemented in Sprint 2

#### Backend
- [x] `autoscout/profiles/schemas.py` — `SearchProfileCreate`, `SearchProfileUpdate`, `SearchProfileRead`, `ParseRequest`, `ParseResponse` with Pydantic v2 validation
- [x] `autoscout/profiles/router.py` — 7 endpoints (CRUD + toggle + parse)
- [x] Claude Sonnet 4.6 tool-use integration for NL parsing
- [x] Nominatim geocoding with Albania-first fallback
- [x] Alembic migration 0003 (PostGIS line removed — installed separately in prod)
- [x] Versioned system prompt: `autoscout-prompts/profile_parser/v1.md`

### ⏳ Remaining for Sprint 2
- [ ] **Mobile — Searches tab UI**:
  - List view: profile cards with name, summary, active toggle, edit/delete swipe
  - Create flow: "Form" entry point and "Describe in words" (NL) entry point
  - Form: make picker, model field, year/price/mileage sliders, body/transmission/fuel chips, location picker + radius
  - NL flow: text input → parse → pre-fill form → highlight low-confidence fields in yellow
  - Edit flow reuses form components
- [ ] **Location picker**: Mapbox or Google Maps RN component (default center Tiranë, radius circle overlay)
- [ ] **Prompt regression harness**: 30+ Albanian/English test cases in `autoscout-prompts/` with CI job

---

## Sprint 1 — Dev Mode ✅ COMPLETE

### What Works End-to-End (Verified)
1. ✅ **Mobile Auth Flow**:
   - User enters phone number on signup screen
   - Mock OTP code `123456` appears in alert
   - User enters code on OTP screen
   - Mock Firebase token generated and stored in SecureStore
   - App navigates to Searches tab
   - Reopen app → persisted session takes you directly to Searches
   - Sign out button clears session and redirects to signup

2. ✅ **Backend API**:
   - `/health` endpoint verifies DB + Redis connectivity
   - `/auth/sync` endpoint accepts mock Firebase tokens in dev mode
   - `/me` endpoint returns authenticated user
   - Backend logs structured JSON to stdout
   - Sentry integration configured (not yet verified with errors)

3. ✅ **Database**:
   - PostgreSQL running locally with Alembic migrations applied
   - Users table populated when signup occurs
   - Listings table populated when crawler runs
   - FK constraints in place for referential integrity

4. ✅ **Crawler**:
   - CLI: `python -m crawler --source=merrjep --profile=<test_id>`
   - Merrjep source adapter returns mock listings
   - Listings parsed into normalized schema
   - Persisted to database with deduplication
   - Duplicate detection prevents re-inserting same listings

### ✅ Implemented in Development

#### Backend
- [x] FastAPI skeleton with structured logging (JSON to stdout)
- [x] Sentry integration for error tracking
- [x] `/health` endpoint with DB + Redis health checks
- [x] `/auth/sync` endpoint with Firebase token verification
- [x] `/me` endpoint for authenticated users
- [x] Database models with FK constraints and relationships
- [x] Alembic migrations (0001 initial schema, 0002 FK + JSONB)
- [x] `.env` configuration with all required variables

#### Mobile App
- [x] Expo router with auth guards (`onAuthStateChanged` redirect)
- [x] Signup screen with phone number input
- [x] **Dev Mode OTP**: Mock confirmation result (code: `123456`)
- [x] OTP verification screen (6-digit input)
- [x] Zustand auth store for user/token/confirmationResult
- [x] Axios client with auth header injection
- [x] Firebase initialization with AsyncStorage persistence
- [x] SecureStore token persistence
- [x] Error handling for dev mode (allows mock tokens)
- [x] App redirects to signup if logged out, tabs if logged in


---

## Production Requirements 🔴 TODO

### Mobile App — Production
- [ ] **Real Firebase Phone Auth**
  - Remove mock confirmation result from signup
  - Implement proper `signInWithPhoneNumber` with reCAPTCHA
  - Options:
    - Build a dev build with `@react-native-firebase` native modules
    - OR use Firebase REST API directly (no native modules needed)
    - OR use `react-native-firebase-recaptcha` (needs different package than broken expo-firebase-recaptcha)

- [ ] **Remove Dev Mode Fallback**
  - Currently OTP screen allows mock tokens
  - Production must validate real Firebase tokens

- [ ] **Bottom-Tab Navigation**
  - [ ] Searches tab (empty state for now)
  - [ ] History tab (empty state for now)
  - [ ] Settings tab (empty state + sign-out button)

- [ ] **EAS Build**
  - [ ] Set up EAS project (eas.json)
  - [ ] Build for iOS TestFlight
  - [ ] Build for Android Play Internal Testing

- [ ] **Real Firebase Credentials**
  - [ ] Get from Firebase Console (already done locally in .env)
  - [ ] Store in EAS secrets, not in code

### Backend — Production
- [ ] **Database**
  - [ ] Set up PostgreSQL in production (Railway, AWS RDS, etc.)
  - [ ] Run Alembic migrations on production database
  - [ ] Set up backups

- [ ] **Redis**
  - [ ] Set up Redis instance (Railway, AWS ElastiCache, etc.)
  - [ ] Configure connection pooling

- [ ] **Environment Variables**
  - [ ] Set all `DATABASE_URL`, `REDIS_URL`, `FIREBASE_PROJECT_ID` in production
  - [ ] Set `SENTRY_DSN` for error tracking
  - [ ] Secure all secrets (never commit)

- [ ] **Deployment**
  - [ ] Deploy to Railway via GitHub integration
  - [ ] Configure domain: `api.dev.autoscout.al` (or production domain)
  - [ ] Set up SSL/HTTPS

- [ ] **Monitoring**
  - [ ] Verify Sentry is capturing errors
  - [ ] Set up dashboards for logs and metrics
  - [ ] Configure alerts for critical errors

#### Crawler
- [x] Implement first source adapter (merrjep.al with mock data)
- [x] CLI: `python -m crawler --source=merrjep --profile=<id>`
- [x] Persist listings to database with deduplication
- [ ] Celery worker setup with Redis (next phase)
- [ ] Add Prometheus metrics (next phase)

---

## Next Steps (Priority Order)

### Sprint 2 — Remaining (Mobile UI)
1. **Searches tab list view**
   - Profile cards with name, summary line, active toggle, edit/delete swipe actions
   - Empty state: "Create your first search" CTA

2. **Search profile create flow**
   - "Form" entry point — make/model/year/price/mileage/body/fuel/transmission/location pickers
   - "Describe in words" entry point — text input → `POST /profiles/parse` → pre-fill form
   - Highlight low-confidence fields (`needs_review: true`) in yellow

3. **Location picker screen**
   - Mapbox or Google Maps RN; default center Tiranë; radius circle overlay

### Sprint 3 — Multi-Source Crawling
4. Add real merrjep.al scraping (replace mock adapter)
5. Add second source (njoftime.com or similar)
6. Celery worker + Redis scheduler for daily crawl jobs
7. Prometheus metrics on crawler

### Sprint 4+ — Matching, Ranking, WhatsApp
8. Match listings against search profiles
9. LLM relevance scoring
10. WhatsApp delivery via Twilio

---

## Dev vs Production Checklist

| Feature | Dev Mode | Production |
|---------|----------|------------|
| Phone Auth | ✅ Mock (code: 123456) | ⏳ Real Firebase |
| Backend Calls | ⚠️ Allows mock tokens | ✅ Validates real tokens |
| Token Storage | ✅ SecureStore | ✅ SecureStore (same) |
| Auth Persistence | ✅ AsyncStorage | ✅ AsyncStorage (same) |
| Database | ✅ Local PostgreSQL | ⏳ Production RDS/Railway |
| Redis | ✅ Local | ⏳ Production Redis |
| Deployment | ✅ Expo Go | ⏳ App Store/Play Store |
| Logging | ✅ Console + structlog | ✅ Sentry |

---

## Files Structure Summary

```
autoscout-backend/
├── autoscout/
│   ├── main.py          (FastAPI app, endpoints)
│   ├── settings.py      (Config from env)
│   ├── auth/
│   │   ├── firebase.py  (Token verification)
│   │   └── schemas.py   (Request/response models)
│   └── db/
│       ├── models.py    (SQLAlchemy ORM)
│       └── session.py   (DB connection)
├── migrations/          (Alembic migrations)
├── alembic.ini
├── pyproject.toml
└── .env

autoscout-mobile/
├── app/
│   ├── _layout.tsx      (Root layout with auth guard)
│   ├── (auth)/
│   │   ├── _layout.tsx
│   │   ├── signup.tsx   (Phone number entry)
│   │   └── otp.tsx      (Code verification)
│   └── (tabs)/          (TODO: Implement tabs)
├── lib/
│   ├── firebase.ts      (Firebase init)
│   └── api.ts           (Axios + syncUser)
├── store/
│   └── authStore.ts     (Zustand auth state)
├── app.json
├── .env                 (Firebase credentials)
└── package.json
```

---

## Known Limitations / Technical Debt

1. **Phone Auth**: Currently using mock verifier in dev mode
   - Will need proper Firebase phone auth for production
   - reCAPTCHA handling is complex in Expo Go

2. **Models**: FK constraints added but no ORM relationships in all queries
   - Can improve by using SQLAlchemy relationships consistently

3. **Error Handling**: Dev mode allows mock tokens to bypass backend validation
   - Needs to be removed for production

4. **Tab Screens**: Currently empty stubs
   - Need proper implementation

5. **Logging**: Structured logging working but not yet aggregated to external service
   - Sentry is configured but needs verification

---

## How to Run Locally

### Prerequisites
- PostgreSQL running on localhost:5432 (default: user=postgres, password=postgres)
- Redis running on localhost:6379 (for Celery, optional for now)
- Node.js for mobile app

### Backend
```bash
cd autoscout-backend
poetry install
poetry run alembic upgrade head  # Apply migrations
poetry run uvicorn autoscout.main:app --reload
# Runs on http://localhost:8000
```

### Mobile
```bash
cd autoscout-mobile
npm install
npm start
# Scan QR code with Expo Go or press 'i' for iOS simulator
```

### Crawler
```bash
cd autoscout-crawlers
poetry install
poetry run python -m crawler --source=merrjep --profile=<profile_id>
# Lists and persists 3 mock listings to database
```

### Testing Complete Flow
1. **Start backend**: `poetry run uvicorn autoscout.main:app --reload`
2. **Start mobile app**: `npm start` and scan with Expo Go
3. **In app**:
   - Enter phone number (e.g., +355 69 123 4567)
   - Code alert shows: "A test code will be: 123456"
   - Enter `123456` on OTP screen
   - Navigate to Searches tab
   - Check backend logs for auth events
4. **Verify data**:
   - Backend: `SELECT * FROM users;` → finds your user
   - Run crawler: `poetry run python -m crawler --source=merrjep --profile=test`
   - Backend: `SELECT * FROM listings;` → finds 3 mock listings
5. **Sign out**: Press Settings tab → Sign Out button
6. **Persist session**: Kill app and restart → goes directly to Searches (if you had signed in)
