"""Tests for matching/pipeline.py — end-to-end pipeline with mocked dependencies."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from autoscout.matching.pipeline import run_pipeline, TOP_N_DEFAULT
from tests.conftest import make_listing, make_match, make_profile


def _mock_db_with_profile(profile=None):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = profile
    db.query.return_value.filter.return_value.all.return_value = []
    db.flush.return_value = None
    db.commit.return_value = None
    db.rollback.return_value = None
    db.add.return_value = None
    db.close.return_value = None
    return db


class TestRunPipeline:
    def test_returns_skipped_when_profile_not_found(self):
        db = _mock_db_with_profile(profile=None)
        result = run_pipeline("nonexistent-id", db=db)
        assert result["status"] == "skipped"

    def test_returns_ok_with_zero_candidates(self):
        profile = make_profile()
        db = _mock_db_with_profile(profile=profile)

        with patch("autoscout.matching.pipeline.get_candidate_listings", return_value=[]):
            result = run_pipeline(str(profile.id), db=db)

        assert result["status"] == "ok"
        assert result["candidates"] == 0
        assert result["inserted"] == 0

    def test_scores_and_persists_candidates(self):
        profile = make_profile()
        listings = [make_listing() for _ in range(3)]
        db = _mock_db_with_profile(profile=profile)

        scores = [
            {"listing_id": str(l.id), "score": 80 - i * 5, "reasoning": "ok", "summary": "...", "score_source": "llm"}
            for i, l in enumerate(listings)
        ]

        with patch("autoscout.matching.pipeline.get_candidate_listings", return_value=listings), \
             patch("autoscout.matching.pipeline.score_listings", return_value=scores):
            result = run_pipeline(str(profile.id), db=db)

        assert result["status"] == "ok"
        assert result["candidates"] == 3
        assert result["inserted"] == 3
        # top_n should be min(TOP_N_DEFAULT, inserted)
        assert result["top_n"] == min(TOP_N_DEFAULT, 3)

    def test_top_n_selection(self):
        profile = make_profile()
        # 10 listings, only top 5 should be selected_for_delivery
        listings = [make_listing(id=uuid.uuid4()) for _ in range(10)]
        db = _mock_db_with_profile(profile=profile)

        scores = [
            {"listing_id": str(l.id), "score": 90 - i, "reasoning": "ok", "summary": "...", "score_source": "llm"}
            for i, l in enumerate(listings)
        ]

        added_matches = []
        db.add.side_effect = lambda obj: added_matches.append(obj)

        with patch("autoscout.matching.pipeline.get_candidate_listings", return_value=listings), \
             patch("autoscout.matching.pipeline.score_listings", return_value=scores):
            result = run_pipeline(str(profile.id), db=db)

        selected = [m for m in added_matches if m.selected_for_delivery]
        assert len(selected) == TOP_N_DEFAULT

    def test_custom_top_n(self):
        profile = make_profile()
        listings = [make_listing(id=uuid.uuid4()) for _ in range(8)]
        db = _mock_db_with_profile(profile=profile)

        scores = [
            {"listing_id": str(l.id), "score": 80, "reasoning": "ok", "summary": "...", "score_source": "llm"}
            for l in listings
        ]

        added_matches = []
        db.add.side_effect = lambda obj: added_matches.append(obj)

        with patch("autoscout.matching.pipeline.get_candidate_listings", return_value=listings), \
             patch("autoscout.matching.pipeline.score_listings", return_value=scores):
            result = run_pipeline(str(profile.id), db=db, top_n=3)

        selected = [m for m in added_matches if m.selected_for_delivery]
        assert len(selected) == 3

    def test_handles_scoring_error_gracefully(self):
        profile = make_profile()
        listings = [make_listing()]
        db = _mock_db_with_profile(profile=profile)

        with patch("autoscout.matching.pipeline.get_candidate_listings", return_value=listings), \
             patch("autoscout.matching.pipeline.score_listings", side_effect=Exception("LLM down")):
            result = run_pipeline(str(profile.id), db=db)

        assert result["status"] == "error"
        assert "error" in result

    def test_fallback_score_used_when_listing_not_in_scores(self):
        profile = make_profile()
        listing = make_listing(id=uuid.uuid4())
        db = _mock_db_with_profile(profile=profile)

        # score_listings returns empty list — no score for the listing
        added_matches = []
        db.add.side_effect = lambda obj: added_matches.append(obj)

        with patch("autoscout.matching.pipeline.get_candidate_listings", return_value=[listing]), \
             patch("autoscout.matching.pipeline.score_listings", return_value=[]):
            run_pipeline(str(profile.id), db=db)

        assert len(added_matches) == 1
        assert added_matches[0].relevance_score == 50  # default fallback
        assert added_matches[0].score_source == "fallback"
