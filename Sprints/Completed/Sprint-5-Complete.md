# Sprint 5 Complete — User Listings (Two-Sided Marketplace)

**Completed:** 2026-05-18  
**Tests:** 73/73 passing

---

## What was built

Users can now post cars for sale directly in AutoScout. Their listings flow through the same AI matching pipeline as scraped listings — buyers are immediately notified if a new post matches their search profile.

---

## Backend changes

**Model** (`autoscout/db/models.py`)
- Added to `Listing`: `seller_user_id`, `status`, `photo_urls` (JSONB), `contact_phone`, `views_count`
- New `seller` relationship to `User`

**Migrations**
- `0006_matches_schema.py` — match schema updates (prior sprint)
- `0007_listing_vehicle_attrs.py` — vehicle attribute columns (prior sprint)
- `0008_listing_seller_fields.py` — all 5 new seller/marketplace columns with server defaults

**Listings module** (`autoscout/listings/`)
- `schemas.py` — `ListingCreate`, `ListingUpdate`, `ListingRead`, `ListingBrowseResponse`, `PhotoUploadResponse`, `PhotoConfirmRequest`, `PhotoDeleteRequest`
- `router.py` — 9 endpoints (see API.md for full reference)

**Celery task** (`autoscout/matching/worker.py`)
- `match_new_listing(listing_id)` — triggered on every new platform listing; scores against up to 50 active profiles to control LLM cost

**Dependencies**
- Added `boto3 ^1.34.0` for Cloudflare R2 presigned URL generation

**Settings** (`autoscout/settings.py`)
- Added: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`

---

## Mobile changes

**New screens**
- `app/(tabs)/browse.tsx` — infinite-scroll browse feed with make filter, listing cards, FAB → post
- `app/post-listing.tsx` — full listing form with photo picker, expo-image-manipulator resize, presigned R2 upload
- `app/listing/[id].tsx` — detail view: photo carousel, specs table, WhatsApp contact button, owner CRUD controls
- `app/my-listings.tsx` — seller's own listings with status badges + view counts

**Updated**
- `app/(tabs)/_layout.tsx` — added Browse tab between History and Settings
- `app/(tabs)/settings.tsx` — added "Selling" section with My Listings + Post a Car links
- `lib/api.ts` — added `platformListingsApi` and `PlatformListing` type

---

## Architecture notes

- Platform listings use `source_id = 'autoscout'` — they enter the existing listing table and matching pipeline unchanged
- Photo upload is a three-step flow: `POST /listings/{id}/photos` (get presigned URL) → `PUT` direct to R2 → `POST /listings/{id}/photos/confirm`
- Soft delete only: `status='removed', is_active=False`; no hard deletes
- Browse endpoint is cursor-paginated on `created_at` DESC

---

## R2 credentials needed for photos to work

Set these in docker-compose or `.env` before testing photo upload:
```
R2_ACCOUNT_ID=<cloudflare-account-id>
R2_ACCESS_KEY_ID=<key>
R2_SECRET_ACCESS_KEY=<secret>
R2_BUCKET_NAME=autoscout-listings
R2_PUBLIC_URL=https://<bucket>.<account>.r2.dev
```

Without these, `POST /listings/{id}/photos` returns 503 (by design).

---

## Known limitations

- `price_min`/`price_max` browse filters cast a string column — unparseable prices pass through silently
- iOS requires `NSPhotoLibraryUsageDescription` in `app.json` before TestFlight submission
