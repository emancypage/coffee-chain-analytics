"""Tests for the deterministic analytics layer.

The seed is fixed (RANDOM_SEED=42), so the seeded database has stable values. Tests assert
a few exact anchors plus structural invariants that must hold for any period. Where an exact
figure is used it was read straight from the seeded database, not guessed.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from db import DB_PATH
from main import app

client = TestClient(app)

FULL_FROM = "2025-04-19"
FULL_TO = "2026-04-19"


def get(path, **params):
    resp = client.get(path, params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- overview ---------------------------------------------------------------

def test_overview_full_range_anchors():
    d = get("/api/analytics/overview", date_from=FULL_FROM, date_to=FULL_TO)
    c = d["chain"]
    assert c["tx"] == 52056
    assert c["revenue"] == pytest.approx(398755.0, abs=0.01)
    assert c["gross_margin"] == pytest.approx(317510.35, abs=0.01)
    # revenue must reconcile to cogs + margin
    assert c["cogs"] + c["gross_margin"] == pytest.approx(c["revenue"], abs=0.05)


def test_overview_chain_equals_sum_of_shops():
    d = get("/api/analytics/overview", date_from=FULL_FROM, date_to=FULL_TO)
    assert sum(s["revenue"] for s in d["shops"]) == pytest.approx(d["chain"]["revenue"], abs=0.05)
    assert sum(s["tx"] for s in d["shops"]) == d["chain"]["tx"]
    # shops are returned ranked by revenue
    revs = [s["revenue"] for s in d["shops"]]
    assert revs == sorted(revs, reverse=True)
    # revenue shares add up to ~100
    assert sum(s["revenue_share_pct"] for s in d["shops"]) == pytest.approx(100.0, abs=0.2)


def test_overview_default_window_is_trailing_90_and_flags_decline():
    d = get("/api/analytics/overview")
    assert d["period"]["days"] == 90
    # previous window is the equal-length span immediately before the current one
    assert d["period"]["prev_to"] < d["period"]["from"]
    campus = next(s for s in d["shops"] if s["name"] == "Campus Grounds")
    # the seeded 30% decline over the last 6 months shows as a negative period-over-period delta
    assert campus["revenue_delta_pct"] < 0


def test_overview_carries_shop_level_ratings_matching_source():
    # reviews are recorded per shop only, so ratings live on the shop rows, not categories/baristas
    d = get("/api/analytics/overview", date_from=FULL_FROM, date_to=FULL_TO)
    assert all("avg_rating" in s and "review_count" in s for s in d["shops"])
    # per-shop review counts reconcile to the chain count
    assert sum(s["review_count"] for s in d["shops"]) == d["chain"]["review_count"]
    # the chain average matches a direct query over the same window
    conn = sqlite3.connect(str(DB_PATH))
    n, avg = conn.execute(
        "SELECT COUNT(*), ROUND(AVG(rating), 2) FROM reviews WHERE date(ts) BETWEEN ? AND ?",
        (FULL_FROM, FULL_TO),
    ).fetchone()
    conn.close()
    assert d["chain"]["review_count"] == n
    assert d["chain"]["avg_rating"] == pytest.approx(avg, abs=0.01)


# --- categories -------------------------------------------------------------

def test_categories_ranked_by_absolute_margin_not_percentage():
    d = get("/api/analytics/categories", date_from=FULL_FROM, date_to=FULL_TO)
    cats = {c["category"]: c for c in d["categories"]}
    order = [c["category"] for c in d["categories"]]
    # ranked by absolute margin dollars, descending
    margins = [c["margin"] for c in d["categories"]]
    assert margins == sorted(margins, reverse=True)
    assert order[0] == "coffee"
    # the core point: tea has a higher margin PERCENT than coffee, but far fewer margin DOLLARS,
    # so it must rank below coffee
    assert cats["tea"]["margin_pct"] > cats["coffee"]["margin_pct"]
    assert cats["tea"]["margin"] < cats["coffee"]["margin"]
    assert order.index("tea") > order.index("coffee")
    # margin shares add up to ~100
    assert sum(c["margin_share_pct"] for c in d["categories"]) == pytest.approx(100.0, abs=0.2)


def test_categories_keep_zero_sale_rows_in_a_period_with_no_seasonal_sales():
    # February has no Pumpkin Spice sales (seasonal item sells Sep-Nov only)
    d = get("/api/analytics/categories", date_from="2026-02-01", date_to="2026-02-28")
    cats = {c["category"]: c for c in d["categories"]}
    # the category is still present rather than dropped by the date filter
    assert "seasonal" in cats
    assert cats["seasonal"]["units"] == 0
    assert cats["seasonal"]["margin"] == 0
    assert cats["seasonal"]["margin_pct"] is None


# --- baristas ---------------------------------------------------------------

def test_baristas_benchmarked_within_shop():
    d = get("/api/analytics/baristas", shop_id=4, date_from=FULL_FROM, date_to=FULL_TO)
    rows = d["baristas"]
    # filtering by shop returns only that shop's baristas
    assert len(rows) == 4
    assert all(b["shop_id"] == 4 for b in rows)
    # benchmark fields are always present
    assert all("avg_ticket_vs_shop_pct" in b for b in rows)
    elena = next(b for b in rows if b["name"] == "Elena Kowalski")
    peers = [b for b in rows if b["name"] != "Elena Kowalski"]
    # the one seeded upsell behaviour: highest pastry attach and a positive gap to the shop
    assert elena["avg_ticket_vs_shop_pct"] > 0
    assert all(elena["pastry_attach"] > p["pastry_attach"] for p in peers)
