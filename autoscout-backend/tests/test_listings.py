"""Tests for the platform listings API — CRUD, ownership, photo upload, browse."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, mock_open, patch

import pytest
from fastapi.testclient import TestClient

from autoscout.main import app
from autoscout.db.models import Listing, User
from tests.conftest import make_listing, make_user


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(user: User):
    from autoscout.auth.dependencies import get_db_user
    from autoscout.db.session import get_db

    mock_db = MagicMock()
    app.dependency_overrides[get_db_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app, raise_server_exceptions=False), mock_db


def _public_client():
    from autoscout.db.session import get_db

    mock_db = MagicMock()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app, raise_server_exceptions=False), mock_db


def _platform_listing(**kwargs) -> Listing:
    """A Listing with all platform marketplace fields set."""
    defaults = dict(
        source_id="autoscout",
        seller_user_id=uuid.uuid4(),
        status="active",
        photo_urls=[],
        contact_phone="+355691234567",
        views_count=0,
    )
    defaults.update(kwargs)
    return make_listing(**defaults)


def _make_refresh_set_created_at(mock_db):
    """Make db.refresh set created_at so Pydantic serialisation doesn't fail."""
    def _refresh(obj):
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)
    mock_db.refresh.side_effect = _refresh


VALID_CREATE_BODY = {
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
    "description": "Single owner, full service history, no accidents anywhere.",
    "contact_phone": "+355691234567",
}


# ── Create listing ────────────────────────────────────────────────────────────

class TestCreateListing:
    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_create_returns_201(self):
        user = make_user()
        client, mock_db = _make_client(user)
        _make_refresh_set_created_at(mock_db)
        # match_new_listing.delay failure is silently caught in the router
        resp = client.post("/listings", json=VALID_CREATE_BODY)
        assert resp.status_code == 201

    def test_create_requires_auth(self):
        app.dependency_overrides.clear()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/listings", json=VALID_CREATE_BODY)
        assert resp.status_code in (401, 403, 422)

    def test_create_blank_title_rejected(self):
        user = make_user()
        client, mock_db = _make_client(user)
        _make_refresh_set_created_at(mock_db)
        resp = client.post("/listings", json={**VALID_CREATE_BODY, "title": "   "})
        assert resp.status_code == 422

    def test_create_short_description_rejected(self):
        user = make_user()
        client, mock_db = _make_client(user)
        _make_refresh_set_created_at(mock_db)
        resp = client.post("/listings", json={**VALID_CREATE_BODY, "description": "Too short"})
        assert resp.status_code == 422

    def test_create_invalid_year_rejected(self):
        user = make_user()
        client, _ = _make_client(user)
        resp = client.post("/listings", json={**VALID_CREATE_BODY, "year": 1800})
        assert resp.status_code == 422

    def test_create_invalid_currency_rejected(self):
        user = make_user()
        client, _ = _make_client(user)
        resp = client.post("/listings", json={**VALID_CREATE_BODY, "currency": "USD"})
        assert resp.status_code == 422


# ── Browse (public) ───────────────────────────────────────────────────────────

class TestBrowseListings:
    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def _setup_browse(self, rows: list):
        client, mock_db = _public_client()
        q = MagicMock()
        mock_db.query.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = rows
        return client

    def test_browse_public_no_auth_needed(self):
        client = self._setup_browse([])
        resp = client.get("/listings")
        assert resp.status_code == 200

    def test_browse_returns_envelope_shape(self):
        listing = _platform_listing()
        client = self._setup_browse([listing])
        resp = client.get("/listings")
        assert resp.status_code == 200
        data = resp.json()
        assert "listings" in data
        assert "has_more" in data

    def test_browse_has_more_false_under_limit(self):
        rows = [_platform_listing() for _ in range(3)]
        client = self._setup_browse(rows)
        assert client.get("/listings?limit=20").json()["has_more"] is False

    def test_browse_has_more_true_over_limit(self):
        # limit=2 but backend returns 3 rows → has_more=True
        rows = [_platform_listing() for _ in range(3)]
        client = self._setup_browse(rows)
        assert client.get("/listings?limit=2").json()["has_more"] is True

    def test_browse_invalid_cursor_returns_400(self):
        client = self._setup_browse([])
        resp = client.get("/listings?cursor=not-a-datetime")
        assert resp.status_code == 400

    def test_browse_limit_above_50_rejected(self):
        client, mock_db = _public_client()
        resp = client.get("/listings?limit=999")
        assert resp.status_code == 422


# ── Get listing detail ────────────────────────────────────────────────────────

class TestGetListing:
    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_get_existing_listing_200(self):
        listing = _platform_listing()
        client, mock_db = _public_client()
        mock_db.query.return_value.filter.return_value.first.return_value = listing
        assert client.get(f"/listings/{listing.id}").status_code == 200

    def test_get_missing_listing_404(self):
        client, mock_db = _public_client()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert client.get(f"/listings/{uuid.uuid4()}").status_code == 404

    def test_get_increments_views(self):
        listing = _platform_listing(views_count=5)
        client, mock_db = _public_client()
        mock_db.query.return_value.filter.return_value.first.return_value = listing
        client.get(f"/listings/{listing.id}")
        assert listing.views_count == 6

    def test_get_invalid_uuid_422(self):
        client, _ = _public_client()
        assert client.get("/listings/not-a-uuid").status_code == 422


# ── Update listing ────────────────────────────────────────────────────────────

class TestUpdateListing:
    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_owner_can_update(self):
        user = make_user()
        listing = _platform_listing(seller_user_id=user.id)
        client, mock_db = _make_client(user)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        resp = client.patch(f"/listings/{listing.id}", json={"price": "8500"})
        assert resp.status_code == 200
        assert listing.price == "8500"

    def test_non_owner_gets_403(self):
        owner = make_user()
        attacker = make_user(id=uuid.uuid4(), phone_number="+355699999999")
        listing = _platform_listing(seller_user_id=owner.id)

        client, mock_db = _make_client(attacker)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        assert client.patch(f"/listings/{listing.id}", json={"price": "1"}).status_code == 403

    def test_mark_sold_sets_inactive(self):
        user = make_user()
        listing = _platform_listing(seller_user_id=user.id, status="active", is_active=True)
        client, mock_db = _make_client(user)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        client.patch(f"/listings/{listing.id}", json={"status": "sold"})
        assert listing.is_active is False
        assert listing.status == "sold"

    def test_invalid_status_rejected(self):
        user = make_user()
        listing = _platform_listing(seller_user_id=user.id)
        client, mock_db = _make_client(user)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        assert client.patch(f"/listings/{listing.id}", json={"status": "hacked"}).status_code == 422

    def test_update_requires_auth(self):
        app.dependency_overrides.clear()
        client = TestClient(app, raise_server_exceptions=False)
        assert client.patch(f"/listings/{uuid.uuid4()}", json={"price": "1"}).status_code in (401, 403, 422)


# ── Delete listing ────────────────────────────────────────────────────────────

class TestDeleteListing:
    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_owner_can_delete_returns_204(self):
        user = make_user()
        listing = _platform_listing(seller_user_id=user.id)
        client, mock_db = _make_client(user)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        assert client.delete(f"/listings/{listing.id}").status_code == 204

    def test_delete_is_soft_delete(self):
        user = make_user()
        listing = _platform_listing(seller_user_id=user.id, status="active", is_active=True)
        client, mock_db = _make_client(user)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        client.delete(f"/listings/{listing.id}")
        assert listing.status == "removed"
        assert listing.is_active is False

    def test_non_owner_cannot_delete(self):
        owner = make_user()
        attacker = make_user(id=uuid.uuid4(), phone_number="+355699999999")
        listing = _platform_listing(seller_user_id=owner.id)

        client, mock_db = _make_client(attacker)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        assert client.delete(f"/listings/{listing.id}").status_code == 403

    def test_delete_requires_auth(self):
        app.dependency_overrides.clear()
        client = TestClient(app, raise_server_exceptions=False)
        assert client.delete(f"/listings/{uuid.uuid4()}").status_code in (401, 403, 422)


# ── My listings ───────────────────────────────────────────────────────────────

class TestMyListings:
    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_returns_own_listings(self):
        user = make_user()
        listings = [_platform_listing(seller_user_id=user.id) for _ in range(3)]
        client, mock_db = _make_client(user)
        (mock_db.query.return_value
         .filter.return_value
         .order_by.return_value
         .all.return_value) = listings

        resp = client.get("/me/listings")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_my_listings_requires_auth(self):
        app.dependency_overrides.clear()
        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/me/listings").status_code in (401, 403, 422)


# ── Photo upload (local dev endpoint) ────────────────────────────────────────

class TestPhotoUploadLocal:
    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_upload_appends_url_and_returns_200(self):
        user = make_user()
        listing = _platform_listing(seller_user_id=user.id, photo_urls=[])
        client, mock_db = _make_client(user)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        with patch("autoscout.listings.router.os.makedirs"), \
             patch("builtins.open", mock_open()):
            resp = client.post(
                f"/listings/{listing.id}/photos/upload",
                files={"file": ("photo.jpg", BytesIO(b"fake-image-data"), "image/jpeg")},
            )

        assert resp.status_code == 200
        assert len(listing.photo_urls) == 1

    def test_upload_max_10_photos_enforced(self):
        user = make_user()
        listing = _platform_listing(
            seller_user_id=user.id,
            photo_urls=[f"http://localhost/img{i}.jpg" for i in range(10)],
        )
        client, mock_db = _make_client(user)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        resp = client.post(
            f"/listings/{listing.id}/photos/upload",
            files={"file": ("photo.jpg", BytesIO(b"data"), "image/jpeg")},
        )
        assert resp.status_code == 400

    def test_upload_non_owner_403(self):
        owner = make_user()
        attacker = make_user(id=uuid.uuid4(), phone_number="+355699999999")
        listing = _platform_listing(seller_user_id=owner.id, photo_urls=[])

        client, mock_db = _make_client(attacker)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        resp = client.post(
            f"/listings/{listing.id}/photos/upload",
            files={"file": ("photo.jpg", BytesIO(b"data"), "image/jpeg")},
        )
        assert resp.status_code == 403

    def test_upload_requires_auth(self):
        app.dependency_overrides.clear()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            f"/listings/{uuid.uuid4()}/photos/upload",
            files={"file": ("photo.jpg", BytesIO(b"data"), "image/jpeg")},
        )
        assert resp.status_code in (401, 403, 422)


# ── Photo confirm / remove ────────────────────────────────────────────────────

class TestPhotoConfirmRemove:
    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_confirm_appends_url(self):
        user = make_user()
        listing = _platform_listing(seller_user_id=user.id, photo_urls=[])
        client, mock_db = _make_client(user)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        url = "https://r2.example.com/listings/test.jpg"
        resp = client.post(f"/listings/{listing.id}/photos/confirm", json={"url": url})
        assert resp.status_code == 200
        assert url in listing.photo_urls

    def test_confirm_no_duplicate(self):
        url = "https://r2.example.com/listings/test.jpg"
        user = make_user()
        listing = _platform_listing(seller_user_id=user.id, photo_urls=[url])
        client, mock_db = _make_client(user)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        client.post(f"/listings/{listing.id}/photos/confirm", json={"url": url})
        assert listing.photo_urls.count(url) == 1

    def test_remove_deletes_url_only(self):
        url = "https://r2.example.com/listings/test.jpg"
        other = "https://r2.example.com/listings/other.jpg"
        user = make_user()
        listing = _platform_listing(seller_user_id=user.id, photo_urls=[url, other])
        client, mock_db = _make_client(user)
        mock_db.query.return_value.filter.return_value.first.return_value = listing

        resp = client.request("DELETE", f"/listings/{listing.id}/photos", json={"url": url})
        assert resp.status_code == 204
        assert url not in listing.photo_urls
        assert other in listing.photo_urls
