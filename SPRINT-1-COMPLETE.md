# Sprint 1 — Complete ✅

AutoScout now has a fully functional development environment with mobile app, backend, and crawler.

## What's Implemented

### ✅ Mobile App (React Native + Expo)
- **Signup Screen**: Phone number input with dev-mode alert showing test code `123456`
- **OTP Screen**: 6-digit code verification with mock Firebase flow
- **Tabs**: Searches, History, and Settings screens with sign-out functionality
- **Auth Persistence**: SecureStore for tokens + AsyncStorage for user session
- **Auth Guard**: Root layout redirects to signup if logged out, tabs if logged in
- **Dev Mode**: Mock tokens bypass backend validation for local testing

### ✅ Backend (FastAPI)
- **Health Check**: `/health` endpoint verifies PostgreSQL + Redis connectivity
- **Auth Sync**: `/auth/sync` endpoint accepts Firebase tokens and creates/updates users
- **User Profile**: `/me` endpoint returns authenticated user data
- **Database**: PostgreSQL with SQLAlchemy ORM, Alembic migrations, and FK constraints
- **Logging**: Structured JSON logging via structlog (to stdout)
- **Monitoring**: Sentry integration configured (error tracking when enabled)

### ✅ Crawler (Python)
- **CLI**: `python -m crawler --source=merrjep --profile=<profile_id>`
- **Merrjep Source**: Mock adapter returns 3 sample car listings
- **Database Persistence**: Listings stored with deduplication by source + listing_id
- **Duplicate Detection**: Running crawler twice skips already-persisted listings

### ✅ Database (PostgreSQL)
- **Migrations**: Alembic setup with 2 migrations applied
  - Initial schema: users, search_profiles, listings, matches
  - FK constraints + JSONB raw_payload field
- **Data**: Users created via mobile signup, listings created via crawler
- **Indexes**: On phone_number, source_listing_id, dedup_hash, foreign keys

## Quick Start

### 1. Terminal 1 — Backend
```bash
cd autoscout-backend
poetry run uvicorn autoscout.main:app --reload
# Runs on http://localhost:8000
```

### 2. Terminal 2 — Mobile
```bash
cd autoscout-mobile
npm start
# Scan QR code with Expo Go
```

### 3. Terminal 3 — Crawler (optional)
```bash
cd autoscout-crawlers
poetry run python -m crawler --source=merrjep --profile=test
# Lists 3 mock cars and persists to DB
```

## Testing the Flow

1. **Mobile**:
   - Open app in Expo Go
   - Enter phone: `+355 69 123 4567`
   - Alert shows: "A test code will be: 123456"
   - Enter `123456` on OTP screen
   - Navigate to Searches tab ✓

2. **Database**:
   - Check users: `SELECT * FROM users WHERE phone_number LIKE '%123%';`
   - Check listings: `SELECT COUNT(*) FROM listings;`

3. **Crawler**:
   - Run: `poetry run python -m crawler --source=merrjep --profile=test`
   - Should insert 3 listings (or skip if already there)
   - Check DB: `SELECT title, price FROM listings ORDER BY created_at DESC LIMIT 3;`

4. **Sign Out**:
   - In app: Settings tab → Sign Out button
   - App returns to signup screen
   - Session cleared from SecureStore

5. **Persistence**:
   - Kill app and restart
   - If you were signed in, goes directly to Searches ✓
   - If you signed out, goes to signup

## What's NOT Included (Production Only)

- **Real Firebase Phone Auth**: Currently mock tokens in dev mode
- **EAS Build**: Mobile builds for iOS/Android (TestFlight/Play Store)
- **Railway Deployment**: Backend hosting (still localhost only)
- **Celery Workers**: Async crawler tasks (manual CLI for now)
- **Real Crawler**: merrjep.al scraping (mock data for now)
- **LLM Matching**: Anthropic Claude API integration (stub)
- **Monitoring**: Sentry configured but not verified with errors

## Architecture

```
autoscout-backend/           → FastAPI + SQLAlchemy + Sentry
├── /auth                    → Firebase token verification
├── /db                      → PostgreSQL session, ORM models
├── /main.py                 → API endpoints: /health, /auth/sync, /me

autoscout-mobile/            → React Native + Expo Router
├── app/(auth)/              → Signup + OTP screens
├── app/(tabs)/              → Searches, History, Settings tabs
├── lib/                      → Firebase init, Axios API client
├── store/                    → Zustand auth state management

autoscout-crawlers/          → Python + Click CLI
├── crawler/sources/         → SourceAdapter base class, MerrjepAdapter
├── crawler/__main__.py      → CLI entry point with DB persistence
├── crawler/db.py            → SQLAlchemy session for crawler
```

## Database Schema

```sql
-- Users (from mobile signup)
users (id, phone_number, country, created_at, ...)

-- Search Profiles (users can create multiple searches)
search_profiles (id, user_id, name, is_active, ...)

-- Listings (from crawler)
listings (id, source_id, source_listing_id, title, make, model, 
          year, price, mileage, location_text, raw_payload, dedup_hash, ...)

-- Matches (LLM will create these for user searches)
matches (id, search_profile_id, listing_id, relevance_score, ...)
```

## Verified Features

- ✅ Mobile signup flow with mock OTP
- ✅ Backend creates user records
- ✅ Auth token persistence + session restore
- ✅ Sign-out clears session
- ✅ Crawler persists listings with deduplication
- ✅ Database health checks working
- ✅ Structured logging from backend
- ✅ Auth guard redirects to correct screen

## Known Limitations

1. **Mock Authentication**: Tokens start with `mock-` and bypass backend validation
2. **No Real Firebase**: Phone auth is simulated, not using Firebase API
3. **Mock Crawler Data**: merrjep source returns static test data, not real listings
4. **No LLM Matching**: Match creation not implemented yet
5. **No Worker Queue**: Crawler runs synchronously, not via Celery

## Next Steps

1. **Real Firebase Auth** (Production):
   - Set up proper phone verification via Firebase REST API
   - Remove dev-mode token bypass in backend

2. **Real Crawler** (Production):
   - Implement HTTP scraping for merrjep.al
   - Add mobile.al source adapter
   - Set up Celery workers with Redis

3. **LLM Matching** (Feature):
   - Create `/search-profiles` CRUD endpoints
   - Integrate Anthropic Claude for matching listings to profiles
   - Persist matches to database

4. **Deployment** (Production):
   - Deploy backend to Railway
   - Build + distribute mobile app via EAS to TestFlight/Play Store
   - Set up production database and Redis

---

**Status**: Sprint 1 development complete. All core systems functional locally.
