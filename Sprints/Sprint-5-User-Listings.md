# Sprint 5 — User Listings (Two-Sided Marketplace)

**Duration:** Weeks 9–10
**Theme:** Let sellers post directly on AutoScout. Platform-native listings go through the same AI matching pipeline as scraped listings, and buyers are notified immediately when a match is posted.

---

## Goals

- Any authenticated user can post a car listing with photos directly in the app.
- Platform listings appear in matching results alongside scraped listings — no pipeline changes needed.
- When a new listing is posted, the matching pipeline runs immediately for all active profiles that could match.
- A Browse tab lets anyone scroll all active platform listings with filters.
- Photos are stored on Cloudflare R2 with signed URLs.
- The platform is no longer fully dependent on external scrapers for inventory.

## Out of Scope

- In-app messaging between buyer and seller (WhatsApp is the contact channel — Sprint 6).
- Paid promotion / featured listings (V2).
- Seller reviews / trust badges (V2).
- Video uploads (V2).

---

## Data Model

### `listings` table — additions

```sql
ALTER TABLE listings
  ADD COLUMN seller_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active',
  -- status: active | sold | expired | removed
  ADD COLUMN photo_urls JSONB NOT NULL DEFAULT '[]',
  -- ordered array of R2 public URLs e.g. ["https://r2.autoscout.al/listings/uuid/1.jpg"]
  ADD COLUMN contact_phone VARCHAR(30),
  ADD COLUMN views_count INTEGER NOT NULL DEFAULT 0;
```

`source_id = 'autoscout'` for platform listings (existing column, no migration needed).

New index: `(seller_user_id)` for "my listings" query.

### New migration: `0008_listing_seller_fields.py`

---

## Workstreams

### Backend — Listing CRUD API

#### `POST /listings` — create a platform listing

- Requires auth (`get_db_user`).
- Accepts JSON body (no photos yet — photos uploaded separately via presigned URL).
- Sets `source_id = 'autoscout'`, `seller_user_id = current_user.id`, `status = 'active'`.
- After DB insert → fires background task `trigger_immediate_matching(listing_id)`.
- Returns created listing.

Request body:
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
  "description": "Single owner, full service history, no accidents.",
  "contact_phone": "+355691234567"
}
```

#### `GET /listings` — browse all active platform listings

- Public (no auth required).
- Query params: `make`, `model`, `year_min`, `year_max`, `price_min`, `price_max`, `mileage_max`, `fuel_type`, `transmission`, `body_type`, `limit` (default 20), `cursor` (ISO datetime for keyset pagination).
- Only returns `source_id = 'autoscout'` AND `status = 'active'` listings.
- Newest first.

#### `GET /listings/{id}` — listing detail

- Public.
- Increments `views_count` (fire-and-forget background update, don't block response).
- Returns full listing including `photo_urls`, seller contact phone.

#### `PATCH /listings/{id}` — edit listing

- Auth required. Must be `seller_user_id == current_user.id` (403 otherwise).
- Allowed fields: title, price, mileage, description, contact_phone, status.
- If `status` changes to `sold` → update `is_active = false`.

#### `DELETE /listings/{id}` — remove listing

- Auth required. Owner only (403 otherwise).
- Soft delete: sets `status = 'removed'`, `is_active = false`.

#### `GET /me/listings` — seller's own listings

- Auth required.
- Returns all listings posted by the current user, any status, newest first.

---

### Backend — Photo Upload (Cloudflare R2)

#### Flow

```
Mobile app                     Backend                       Cloudflare R2
    │                              │                               │
    │  POST /listings/{id}/photos  │                               │
    │  ──────────────────────────► │  PutObject presigned URL      │
    │                              │  ──────────────────────────► │
    │  { upload_url, final_url }   │                               │
    │  ◄────────────────────────── │                               │
    │                              │                               │
    │  PUT {upload_url} (binary)   │                               │
    │  ──────────────────────────────────────────────────────────►│
    │                              │                               │
    │  POST /listings/{id}/photos/confirm                          │
    │  ──────────────────────────► │  Append final_url to          │
    │                              │  photo_urls JSONB column      │
```

#### `POST /listings/{id}/photos` — get presigned upload URL

- Auth required, owner only.
- Max 10 photos per listing.
- Generates a presigned PUT URL (valid 10 min) for key `listings/{listing_id}/{uuid}.jpg`.
- Returns `{ upload_url, final_url }`.

#### `POST /listings/{id}/photos/confirm` — confirm upload complete

- Auth required, owner only.
- Body: `{ "url": "https://r2.autoscout.al/..." }`
- Appends URL to `photo_urls` JSONB array.

#### `DELETE /listings/{id}/photos` — remove a photo

- Auth required, owner only.
- Body: `{ "url": "..." }`
- Removes from array; optionally deletes from R2 (best-effort).

#### Settings additions (`settings.py`)

```python
R2_ACCOUNT_ID: str
R2_ACCESS_KEY_ID: str
R2_SECRET_ACCESS_KEY: str
R2_BUCKET_NAME: str = "autoscout-listings"
R2_PUBLIC_URL: str  # e.g. https://r2.autoscout.al
```

Uses `boto3` with R2's S3-compatible endpoint: `https://{account_id}.r2.cloudflarestorage.com`.

---

### Backend — Immediate Matching on Post

When `POST /listings` succeeds, enqueue a background Celery task:

```python
@celery_app.task(name="autoscout.matching.worker.match_new_listing")
def match_new_listing(listing_id: str):
    """
    For a newly posted platform listing, run the pipeline for every active
    profile whose hard bounds the listing passes.
    """
    db = SessionLocal()
    try:
        listing = db.query(Listing).filter_by(id=listing_id).first()
        if not listing:
            return

        profiles = db.query(SearchProfile).filter_by(is_active=True).all()
        triggered = 0
        for profile in profiles:
            if _passes_hard_bounds(listing, profile) and _passes_geo_filter(listing, profile):
                run_pipeline(str(profile.id), db=db)
                triggered += 1

        logger.info("[match_new_listing] listing=%s triggered=%d pipelines", listing_id, triggered)
    finally:
        db.close()
```

- Runs on the `backend` queue.
- `run_pipeline` already handles already-seen suppression, so duplicate matches are impossible.
- The WhatsApp notification (Sprint 6) hooks into `selected_for_delivery=true` matches — no changes needed here.

---

### Mobile — Post a Listing

#### New screen: `/post-listing`

Form fields:
- Make (text input with autocomplete suggestions)
- Model (text input)
- Year (picker 1990–current year)
- Price (numeric, currency toggle ALL/EUR)
- Mileage (numeric, km)
- Transmission (picker: Manual / Automatic / Any)
- Fuel type (picker: Petrol / Diesel / Electric / Hybrid / Any)
- Body type (picker: Sedan / Hatchback / SUV / Combi / Coupe / Convertible / Any)
- Location (text — city name)
- Description (multiline, min 30 chars)
- Contact phone (pre-filled from user's phone, editable)

Photo upload:
- Up to 10 photos, minimum 1 required.
- Use expo-image-picker to select from camera roll or camera.
- Upload each photo via presigned URL flow.
- Show thumbnails with delete X.

Submit → `POST /listings` → on success navigate to listing detail.

#### New screen: `/listing/[id]` — listing detail (public)

Displays:
- Photo carousel (horizontal scroll of `photo_urls`)
- Title, price, year, mileage, location chip
- Specs row: transmission · fuel · body type
- Description
- "Contact seller on WhatsApp" button → `whatsapp://send?phone={contact_phone}&text=...` deep link
- If viewer is the owner: Edit and Mark as Sold buttons

#### Updated tab: Browse

New tab in `(tabs)/_layout.tsx`:
- Name: "Browse"
- Icon: `storefront` (MaterialIcons)
- Fetches `GET /listings` with infinite scroll (cursor pagination).
- Filter bar at top: Make / Price Max / Fuel Type (3 quick filters, expandable).
- Each row: first photo thumbnail, title, price chip, mileage, location.
- Tap → `/listing/[id]`.
- Pull-to-refresh.

#### New screen: `/my-listings`

Accessible from Settings tab:
- Lists all the user's own listings (any status).
- Status badge on each card: Active (green) / Sold (grey) / Removed (red).
- Tap → `/listing/[id]` with owner controls visible.
- "Post a listing" FAB at bottom.

---

### API additions to `lib/api.ts`

```typescript
export interface PlatformListing {
  id: string;
  seller_user_id: string;
  title: string;
  make?: string;
  model?: string;
  year?: number;
  price?: string;
  currency: string;
  mileage?: number;
  location_text?: string;
  transmission?: string;
  fuel_type?: string;
  body_type?: string;
  description?: string;
  contact_phone?: string;
  photo_urls: string[];
  status: 'active' | 'sold' | 'expired' | 'removed';
  views_count: number;
  created_at: string;
}

export interface ListingCreateInput {
  title: string;
  make?: string;
  model?: string;
  year?: number;
  price?: string;
  currency?: string;
  mileage?: number;
  location_text?: string;
  transmission?: string;
  fuel_type?: string;
  body_type?: string;
  description?: string;
  contact_phone?: string;
}

export const platformListingsApi = {
  browse: (params?: Record<string, any>): Promise<{ listings: PlatformListing[]; has_more: boolean; next_cursor?: string }> =>
    apiClient.get('/listings', { params }).then(r => r.data),

  get: (id: string): Promise<PlatformListing> =>
    apiClient.get(`/listings/${id}`).then(r => r.data),

  create: (data: ListingCreateInput): Promise<PlatformListing> =>
    apiClient.post('/listings', data).then(r => r.data),

  update: (id: string, data: Partial<ListingCreateInput & { status: string }>): Promise<PlatformListing> =>
    apiClient.patch(`/listings/${id}`, data).then(r => r.data),

  remove: (id: string): Promise<void> =>
    apiClient.delete(`/listings/${id}`).then(() => undefined),

  myListings: (): Promise<PlatformListing[]> =>
    apiClient.get('/me/listings').then(r => r.data),

  getPhotoUploadUrl: (id: string): Promise<{ upload_url: string; final_url: string }> =>
    apiClient.post(`/listings/${id}/photos`).then(r => r.data),

  confirmPhotoUpload: (id: string, url: string): Promise<PlatformListing> =>
    apiClient.post(`/listings/${id}/photos/confirm`, { url }).then(r => r.data),
};
```

---

## Definition of Done

1. A user can post a car listing with at least 1 photo from the mobile app. The listing appears in the Browse tab within seconds.
2. A second user with a matching search profile — where the new listing passes hard bounds — has a new match created automatically within 60 seconds of the listing being posted.
3. The Browse tab loads all active platform listings with basic filters working.
4. The listing detail screen shows the photo carousel and a working "Contact on WhatsApp" deep link.
5. The seller can edit price/description and mark the listing as sold; sold listings disappear from Browse.
6. Photos are stored on Cloudflare R2 and served via the public URL (not base64, not local disk).
7. A seller cannot edit or delete another user's listing (403).
8. All new endpoints are covered by tests and documented in `API.md`.

---

## Risks & Watch-Outs

- **R2 CORS for presigned uploads.** Configure R2 bucket CORS policy to allow PUT from the app's origin before testing uploads; this is a 5-minute config step that's easy to forget.
- **Image size on mobile.** Use `expo-image-manipulator` to resize to max 1600px and compress to ~80% JPEG before upload. Don't upload full 12MP photos.
- **immediate matching fanout cost.** If 500 profiles are active and a listing passes many bounds, `match_new_listing` could trigger 500 LLM calls. Mitigate: only trigger profiles whose `make` matches (or is null) before running full pipeline. Add a `max_profiles_per_listing = 50` safety cap for V1.
- **expo-image-picker permissions.** iOS requires camera and photo library permission strings in `app.json`. Easy to miss; breaks the upload flow entirely in TestFlight.

---

## Dependencies

- Sprint 4 matching pipeline working end-to-end.
- Cloudflare R2 bucket created with public access enabled and CORS configured.
- `boto3` added to backend `pyproject.toml`.
- `expo-image-picker` and `expo-image-manipulator` added to mobile `package.json`.

---

## Next Sprint Preview

[Sprint 6 — WhatsApp Integration](Sprint-6-WhatsApp-Integration.md): wire the daily digest and immediate-match notifications to WhatsApp. Platform listings now give the "someone just posted your car" real-time alert its full value.
