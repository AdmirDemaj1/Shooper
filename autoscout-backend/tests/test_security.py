"""Security tests — ownership enforcement, auth gates, input validation."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autoscout.main import app
from autoscout.db.models import Match, SearchProfile, User
from tests.conftest import make_listing, make_match, make_profile, make_user


# ── Test client helpers ───────────────────────────────────────────────────────

def _make_client(user: User):
    """Return a TestClient with auth dependency overridden to return `user`."""
    from autoscout.auth.dependencies import get_db_user
    from autoscout.db.session import get_db

    mock_db = MagicMock()

    app.dependency_overrides[get_db_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: mock_db

    client = TestClient(app, raise_server_exceptions=False)
    return client, mock_db


def _clear_overrides():
    app.dependency_overrides.clear()


# ── Auth gate — unauthenticated requests ──────────────────────────────────────

class TestAuthGate:
    def setup_method(self):
        app.dependency_overrides.clear()

    def test_get_profiles_requires_auth(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/profiles")
        assert resp.status_code in (401, 403, 422)

    def test_get_matches_requires_auth(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(f"/matches/{uuid.uuid4()}")
        assert resp.status_code in (401, 403, 422)

    def test_post_match_action_requires_auth(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(f"/matches/{uuid.uuid4()}/action", json={"action": "clicked"})
        assert resp.status_code in (401, 403, 422)


# ── Profile ownership ─────────────────────────────────────────────────────────

class TestProfileOwnership:
    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_cannot_get_another_users_profile(self):
        owner = make_user(id=uuid.uuid4())
        attacker = make_user(id=uuid.uuid4(), phone_number="+355699999999")
        profile = make_profile(id=uuid.uuid4(), user_id=owner.id)

        client, mock_db = _make_client(attacker)

        # DB returns nothing (profile doesn't belong to attacker)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        resp = client.get(f"/profiles/{profile.id}")
        assert resp.status_code == 404

    def test_cannot_delete_another_users_profile(self):
        owner = make_user(id=uuid.uuid4())
        attacker = make_user(id=uuid.uuid4(), phone_number="+355699999999")
        profile = make_profile(id=uuid.uuid4(), user_id=owner.id)

        client, mock_db = _make_client(attacker)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        resp = client.delete(f"/profiles/{profile.id}")
        assert resp.status_code == 404

    def test_cannot_toggle_another_users_profile(self):
        owner = make_user(id=uuid.uuid4())
        attacker = make_user(id=uuid.uuid4(), phone_number="+355699999999")
        profile = make_profile(id=uuid.uuid4(), user_id=owner.id)

        client, mock_db = _make_client(attacker)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        resp = client.post(f"/profiles/{profile.id}/toggle")
        assert resp.status_code == 404

    def test_cannot_patch_another_users_profile(self):
        owner = make_user(id=uuid.uuid4())
        attacker = make_user(id=uuid.uuid4(), phone_number="+355699999999")
        profile = make_profile(id=uuid.uuid4(), user_id=owner.id)

        client, mock_db = _make_client(attacker)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        resp = client.patch(f"/profiles/{profile.id}", json={"name": "Hacked"})
        assert resp.status_code == 404


# ── Match ownership ───────────────────────────────────────────────────────────

class TestMatchOwnership:
    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_cannot_get_another_users_match(self):
        owner = make_user(id=uuid.uuid4())
        attacker = make_user(id=uuid.uuid4(), phone_number="+355699999999")
        match = make_match(id=uuid.uuid4())

        client, mock_db = _make_client(attacker)

        def query_side_effect(model):
            m = MagicMock()
            if model == Match:
                m.options.return_value.filter.return_value.first.return_value = match
            elif model == SearchProfile:
                # Ownership check fails — profile not found for attacker
                m.filter.return_value.first.return_value = None
            return m

        mock_db.query.side_effect = query_side_effect

        resp = client.get(f"/matches/{match.id}")
        assert resp.status_code == 403

    def test_cannot_record_action_on_another_users_match(self):
        owner = make_user(id=uuid.uuid4())
        attacker = make_user(id=uuid.uuid4(), phone_number="+355699999999")
        match = make_match(id=uuid.uuid4())

        client, mock_db = _make_client(attacker)

        def query_side_effect(model):
            m = MagicMock()
            if model == Match:
                m.filter.return_value.first.return_value = match
            elif model == SearchProfile:
                m.filter.return_value.first.return_value = None
            return m

        mock_db.query.side_effect = query_side_effect

        resp = client.post(f"/matches/{match.id}/action", json={"action": "saved"})
        assert resp.status_code == 403


# ── Input validation ──────────────────────────────────────────────────────────

class TestInputValidation:
    def setup_method(self):
        app.dependency_overrides.clear()

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_invalid_match_action_rejected(self):
        user = make_user()
        match = make_match(id=uuid.uuid4())
        profile = make_profile(user_id=user.id)

        client, mock_db = _make_client(user)

        def query_side_effect(model):
            m = MagicMock()
            if model == Match:
                m.filter.return_value.first.return_value = match
            elif model == SearchProfile:
                m.filter.return_value.first.return_value = profile
            return m

        mock_db.query.side_effect = query_side_effect

        resp = client.post(f"/matches/{match.id}/action", json={"action": "hacked"})
        assert resp.status_code == 422

    def test_invalid_cursor_format_rejected(self):
        user = make_user()
        profile = make_profile(user_id=user.id)

        client, mock_db = _make_client(user)
        mock_db.query.return_value.filter.return_value.first.return_value = profile

        resp = client.get(f"/profiles/{profile.id}/matches?cursor=not-a-date")
        assert resp.status_code == 400

    def test_profile_limit_enforced(self):
        user = make_user()
        client, mock_db = _make_client(user)

        # Simulate 10 active profiles already
        mock_db.query.return_value.filter.return_value.count.return_value = 10

        resp = client.post("/profiles", json={"name": "Too Many"})
        assert resp.status_code == 400

    def test_invalid_uuid_in_path_returns_422(self):
        user = make_user()
        client, mock_db = _make_client(user)

        resp = client.get("/profiles/not-a-uuid")
        assert resp.status_code == 422
