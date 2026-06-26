"""Tests for the review-themes endpoint.

The endpoint reads classifications from the sidecar cache and never calls the model, so
these tests populate a temporary cache with the deterministic FakeClassifier (seed is fixed,
so the labels are stable) and assert the aggregation on top of it. The point is two-fold:
Riverside's milk cluster must surface as a real concentration, and Campus must stay scattered,
which is the guard against turning the classifier into a cause-finder for the sales decline.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from ai.cache import ClassificationCache, classify_reviews
from ai.classifier import FakeClassifier
from db import DB_PATH
from main import app

client = TestClient(app)

FULL_FROM = "2025-04-19"
FULL_TO = "2026-04-19"
MODEL = "test-fake"
PROMPT_VERSION = "v1"


def get_json(path, **params):
    resp = client.get(path, params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture
def populated_cache(tmp_path, monkeypatch):
    """Point the cache at a temp file and fill it with deterministic fake labels."""
    cache_path = tmp_path / "cache.db"
    monkeypatch.setenv("CLASSIFICATION_CACHE_DB", str(cache_path))
    monkeypatch.setenv("AI_MODEL", MODEL)
    monkeypatch.setenv("AI_PROMPT_VERSION", PROMPT_VERSION)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    reviews = [
        (r["id"], r["text"])
        for r in conn.execute("SELECT id, text FROM reviews WHERE rating <= 3")
    ]
    conn.close()

    cache = ClassificationCache(cache_path)
    classify_reviews(reviews, FakeClassifier(), MODEL, PROMPT_VERSION, cache=cache)
    cache.close()
    return cache_path


def test_riverside_milk_cluster_surfaces_as_a_concentration(populated_cache):
    d = get_json("/api/analytics/review-themes", date_from=FULL_FROM, date_to=FULL_TO)
    assert d["totals"]["classified"] == d["totals"]["negative_reviews"]
    riverside = next(s for s in d["shops"] if s["name"] == "Riverside Coffee")
    assert riverside["top_theme"] == "dairy"
    # dairy is a real majority-ish share of Riverside complaints, not one of many scattered themes
    assert riverside["themes"][0]["theme"] == "dairy"
    assert riverside["themes"][0]["share_pct"] >= 40


def test_campus_has_no_dominant_complaint_cluster(populated_cache):
    # The Campus decline has no qualitative signal: its negative reviews are scattered. The
    # classifier labels what was written and must not be pushed into a cause for the sales drop.
    # Encoding that as a test: no single theme owns a Riverside-like share, and Campus is not a
    # dairy story (that cluster belongs to Riverside).
    d = get_json("/api/analytics/review-themes", date_from=FULL_FROM, date_to=FULL_TO)
    campus = next(s for s in d["shops"] if s["name"] == "Campus Grounds")
    assert campus["themes"][0]["share_pct"] < 40
    assert campus["top_theme"] != "dairy"


def test_unclassified_reviews_are_reported_not_hidden(tmp_path, monkeypatch):
    empty = tmp_path / "empty.db"
    monkeypatch.setenv("CLASSIFICATION_CACHE_DB", str(empty))
    monkeypatch.setenv("AI_MODEL", "no-labels-here")
    d = get_json("/api/analytics/review-themes", date_from=FULL_FROM, date_to=FULL_TO)
    assert d["totals"]["negative_reviews"] > 0
    assert d["totals"]["classified"] == 0
    assert d["totals"]["unclassified"] == d["totals"]["negative_reviews"]
    assert all(s["classified"] == 0 and s["themes"] == [] for s in d["shops"])


def test_shop_filter_restricts_to_one_shop(populated_cache):
    d = get_json("/api/analytics/review-themes", shop_id=2, date_from=FULL_FROM, date_to=FULL_TO)
    assert len(d["shops"]) == 1
    assert d["shops"][0]["shop_id"] == 2
