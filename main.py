"""Coffee Chain Analytics — deliberately "dumb" dashboard backend.

No AI, no summaries, no forecasts. Raw data only.
Candidates are expected to identify where AI adds value and implement it.
"""

import os
import subprocess
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ai.cache import ClassificationCache
from db import DB_PATH, get_conn

app = FastAPI(title="Coffee Chain Analytics", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def ensure_database():
    if not DB_PATH.exists():
        print("Database not found, running seed.py...")
        seed_script = Path(__file__).parent / "seed.py"
        result = subprocess.run(
            [sys.executable, str(seed_script)],
            cwd=str(Path(__file__).parent),
        )
        if result.returncode != 0:
            raise RuntimeError("seed.py failed")


@app.get("/api/shops")
def list_shops(conn=Depends(get_conn)):
    rows = conn.execute(
        "SELECT id, name, location, seats, opened_on FROM shops ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/menu")
def list_menu(conn=Depends(get_conn)):
    rows = conn.execute(
        "SELECT id, name, category, price, cost FROM menu_items ORDER BY category, name"
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/baristas")
def list_baristas(conn=Depends(get_conn)):
    rows = conn.execute(
        """
        SELECT b.id, b.name, b.primary_shop_id, s.name AS shop_name, b.hired_on
        FROM baristas b JOIN shops s ON s.id = b.primary_shop_id
        ORDER BY b.id
        """
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/transactions")
def list_transactions(
    shop_id: Optional[int] = None,
    barista_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    conn=Depends(get_conn),
):
    where = []
    params: list = []
    if shop_id is not None:
        where.append("t.shop_id = ?")
        params.append(shop_id)
    if barista_id is not None:
        where.append("t.barista_id = ?")
        params.append(barista_id)
    if date_from:
        where.append("t.ts >= ?")
        params.append(date_from)
    if date_to:
        where.append("t.ts <= ?")
        params.append(date_to)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    rows = conn.execute(
        f"""
        SELECT t.id, t.shop_id, s.name AS shop_name,
               t.barista_id, b.name AS barista_name,
               t.ts, t.total
        FROM transactions t
        JOIN shops s ON s.id = t.shop_id
        JOIN baristas b ON b.id = t.barista_id
        {clause}
        ORDER BY t.ts DESC
        LIMIT ? OFFSET ?
        """,
        (*params, limit, offset),
    ).fetchall()

    tx_ids = [r["id"] for r in rows]
    items_by_tx: dict = {}
    if tx_ids:
        placeholders = ",".join("?" * len(tx_ids))
        item_rows = conn.execute(
            f"""
            SELECT ti.transaction_id, ti.menu_item_id, mi.name AS item_name,
                   ti.quantity, ti.unit_price
            FROM transaction_items ti
            JOIN menu_items mi ON mi.id = ti.menu_item_id
            WHERE ti.transaction_id IN ({placeholders})
            """,
            tx_ids,
        ).fetchall()
        for ir in item_rows:
            items_by_tx.setdefault(ir["transaction_id"], []).append(
                {
                    "menu_item_id": ir["menu_item_id"],
                    "item_name": ir["item_name"],
                    "quantity": ir["quantity"],
                    "unit_price": ir["unit_price"],
                }
            )

    result = []
    for r in rows:
        d = dict(r)
        d["items"] = items_by_tx.get(r["id"], [])
        result.append(d)
    return result


@app.get("/api/reviews")
def list_reviews(
    shop_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    max_rating: Optional[int] = Query(None, ge=1, le=5),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    conn=Depends(get_conn),
):
    where = []
    params: list = []
    if shop_id is not None:
        where.append("r.shop_id = ?")
        params.append(shop_id)
    if date_from:
        where.append("r.ts >= ?")
        params.append(date_from)
    if date_to:
        where.append("r.ts <= ?")
        params.append(date_to)
    if min_rating is not None:
        where.append("r.rating >= ?")
        params.append(min_rating)
    if max_rating is not None:
        where.append("r.rating <= ?")
        params.append(max_rating)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    rows = conn.execute(
        f"""
        SELECT r.id, r.shop_id, s.name AS shop_name, r.ts, r.rating, r.text
        FROM reviews r JOIN shops s ON s.id = r.shop_id
        {clause}
        ORDER BY r.ts DESC
        LIMIT ? OFFSET ?
        """,
        (*params, limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/shifts")
def list_shifts(
    shop_id: Optional[int] = None,
    barista_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    conn=Depends(get_conn),
):
    where = []
    params: list = []
    if shop_id is not None:
        where.append("sh.shop_id = ?")
        params.append(shop_id)
    if barista_id is not None:
        where.append("sh.barista_id = ?")
        params.append(barista_id)
    if date_from:
        where.append("sh.shift_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("sh.shift_date <= ?")
        params.append(date_to)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    rows = conn.execute(
        f"""
        SELECT sh.id, sh.barista_id, b.name AS barista_name,
               sh.shop_id, s.name AS shop_name,
               sh.shift_date, sh.start_time, sh.end_time, sh.hours
        FROM shifts sh
        JOIN baristas b ON b.id = sh.barista_id
        JOIN shops s ON s.id = sh.shop_id
        {clause}
        ORDER BY sh.shift_date DESC, sh.shop_id
        LIMIT ? OFFSET ?
        """,
        (*params, limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/stats/daily")
def stats_daily(
    shop_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    conn=Depends(get_conn),
):
    """Daily aggregates: transactions count, revenue, avg ticket."""
    where = []
    params: list = []
    if shop_id is not None:
        where.append("t.shop_id = ?")
        params.append(shop_id)
    if date_from:
        where.append("t.ts >= ?")
        params.append(date_from)
    if date_to:
        where.append("t.ts <= ?")
        params.append(date_to)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    rows = conn.execute(
        f"""
        SELECT date(t.ts) AS day,
               t.shop_id,
               COUNT(*) AS tx_count,
               ROUND(SUM(t.total), 2) AS revenue,
               ROUND(AVG(t.total), 2) AS avg_ticket
        FROM transactions t
        {clause}
        GROUP BY day, t.shop_id
        ORDER BY day, t.shop_id
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/stats/items")
def stats_items(
    shop_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    conn=Depends(get_conn),
):
    """Aggregated sales per menu item: units sold, revenue, margin."""
    where = []
    params: list = []
    if shop_id is not None:
        where.append("t.shop_id = ?")
        params.append(shop_id)
    if date_from:
        where.append("t.ts >= ?")
        params.append(date_from)
    if date_to:
        where.append("t.ts <= ?")
        params.append(date_to)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    rows = conn.execute(
        f"""
        SELECT mi.id, mi.name, mi.category, mi.price, mi.cost,
               SUM(ti.quantity) AS units_sold,
               ROUND(SUM(ti.quantity * ti.unit_price), 2) AS revenue,
               ROUND(SUM(ti.quantity * (ti.unit_price - mi.cost)), 2) AS margin
        FROM menu_items mi
        LEFT JOIN transaction_items ti ON ti.menu_item_id = mi.id
        LEFT JOIN transactions t ON t.id = ti.transaction_id
        {clause}
        GROUP BY mi.id
        ORDER BY units_sold DESC NULLS LAST
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/stats/barista")
def stats_barista(
    shop_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    conn=Depends(get_conn),
):
    """Aggregated stats per barista: tx count, avg ticket, total revenue."""
    where = []
    params: list = []
    if shop_id is not None:
        where.append("t.shop_id = ?")
        params.append(shop_id)
    if date_from:
        where.append("t.ts >= ?")
        params.append(date_from)
    if date_to:
        where.append("t.ts <= ?")
        params.append(date_to)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    rows = conn.execute(
        f"""
        SELECT b.id, b.name, b.primary_shop_id,
               s.name AS shop_name,
               COUNT(t.id) AS tx_count,
               ROUND(AVG(t.total), 2) AS avg_ticket,
               ROUND(SUM(t.total), 2) AS revenue
        FROM baristas b
        JOIN shops s ON s.id = b.primary_shop_id
        LEFT JOIN transactions t ON t.barista_id = b.id
        {clause}
        GROUP BY b.id
        ORDER BY b.primary_shop_id, b.id
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Deterministic analytics layer.
#
# Plain arithmetic over the existing tables, no model involved. Reports what is
# happening per shop, category, and barista for a selected period, plus the change
# versus the previous equal-length period. Explaining the cause is out of scope here:
# this layer is the substrate later AI features read from.
# ---------------------------------------------------------------------------

ANALYTICS_DEFAULT_DAYS = 90

# Reviews at or below this rating are treated as negative and fed to the classifier.
REVIEW_NEGATIVE_MAX = 2


def _safe_div(num, den):
    return round(num / den, 2) if den else None


def _pct(num, den):
    return round(num / den * 100, 1) if den else None


def _delta(cur, prev):
    """Period-over-period percent change. None when there is no prior baseline."""
    return round((cur - prev) / prev * 100, 1) if prev else None


def _resolve_window(conn, date_from, date_to):
    """Resolve the current and previous comparison windows as ISO date strings.

    With no range, the current window is the trailing ANALYTICS_DEFAULT_DAYS of data.
    The previous window is always the equal-length span immediately before the current one,
    so the same comparison logic works whether or not the caller passes explicit dates.
    """
    row = conn.execute(
        "SELECT MIN(date(ts)) AS lo, MAX(date(ts)) AS hi FROM transactions"
    ).fetchone()
    lo, hi = row["lo"], row["hi"]
    if lo is None:
        return None
    if date_from is None and date_to is None:
        cur_to = date.fromisoformat(hi)
        cur_from = cur_to - timedelta(days=ANALYTICS_DEFAULT_DAYS - 1)
    else:
        cur_from = date.fromisoformat(date_from) if date_from else date.fromisoformat(lo)
        cur_to = date.fromisoformat(date_to) if date_to else date.fromisoformat(hi)
    span = (cur_to - cur_from).days
    prev_to = cur_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=span)
    return {
        "data_min": lo,
        "data_max": hi,
        "from": cur_from.isoformat(),
        "to": cur_to.isoformat(),
        "prev_from": prev_from.isoformat(),
        "prev_to": prev_to.isoformat(),
        "days": span + 1,
    }


def _shop_rows(conn, d_from, d_to):
    """Per-shop totals for one window. Shops with no sales in the window still appear
    (the date filter lives inside the CTE, so the LEFT JOIN is not collapsed to an inner one)."""
    return conn.execute(
        """
        WITH win AS (
            SELECT t.id, t.shop_id,
                   ti.quantity AS q, ti.unit_price AS up, mi.cost AS cost
            FROM transactions t
            JOIN transaction_items ti ON ti.transaction_id = t.id
            JOIN menu_items mi ON mi.id = ti.menu_item_id
            WHERE date(t.ts) BETWEEN ? AND ?
        )
        SELECT s.id, s.name,
               COUNT(DISTINCT win.id) AS tx,
               COALESCE(ROUND(SUM(win.q * win.up), 2), 0) AS revenue,
               COALESCE(ROUND(SUM(win.q * win.cost), 2), 0) AS cogs,
               COALESCE(ROUND(SUM(win.q * (win.up - win.cost)), 2), 0) AS margin,
               COALESCE(SUM(win.q), 0) AS units
        FROM shops s
        LEFT JOIN win ON win.shop_id = s.id
        GROUP BY s.id
        ORDER BY revenue DESC
        """,
        (d_from, d_to),
    ).fetchall()


@app.get("/api/analytics/overview")
def analytics_overview(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    conn=Depends(get_conn),
):
    """Chain and per-shop scorecard for a period, with change vs the previous period."""
    win = _resolve_window(conn, date_from, date_to)
    if win is None:
        return {"period": None, "chain": None, "shops": []}

    cur = list(_shop_rows(conn, win["from"], win["to"]))
    prev = {r["id"]: r for r in _shop_rows(conn, win["prev_from"], win["prev_to"])}
    chain_rev = sum(r["revenue"] for r in cur)

    # Reviews are recorded per shop only (no barista or product link), so ratings can be
    # aggregated to the shop but not to a category or a barista. Period-aware; the review
    # count is returned alongside because reviews are sparse and a small sample can mislead.
    ratings = {
        r["shop_id"]: r
        for r in conn.execute(
            "SELECT shop_id, COUNT(*) AS n, ROUND(AVG(rating), 2) AS avg_rating "
            "FROM reviews WHERE date(ts) BETWEEN ? AND ? GROUP BY shop_id",
            (win["from"], win["to"]),
        ).fetchall()
    }

    shops = []
    for r in cur:
        p = prev.get(r["id"])
        rv = ratings.get(r["id"])
        shops.append(
            {
                "shop_id": r["id"],
                "name": r["name"],
                "tx": r["tx"],
                "revenue": r["revenue"],
                "cogs": r["cogs"],
                "gross_margin": r["margin"],
                "gross_margin_pct": _pct(r["margin"], r["revenue"]),
                "avg_ticket": _safe_div(r["revenue"], r["tx"]),
                "items_per_tx": _safe_div(r["units"], r["tx"]),
                "revenue_share_pct": _pct(r["revenue"], chain_rev),
                "revenue_delta_pct": _delta(r["revenue"], p["revenue"] if p else 0),
                "margin_delta_pct": _delta(r["margin"], p["margin"] if p else 0),
                "avg_rating": rv["avg_rating"] if rv else None,
                "review_count": rv["n"] if rv else 0,
            }
        )

    chain: dict = {
        "tx": sum(r["tx"] for r in cur),
        "revenue": round(chain_rev, 2),
        "cogs": round(sum(r["cogs"] for r in cur), 2),
        "gross_margin": round(sum(r["margin"] for r in cur), 2),
        "units": sum(r["units"] for r in cur),
    }
    chain["gross_margin_pct"] = _pct(chain["gross_margin"], chain["revenue"])
    chain["avg_ticket"] = _safe_div(chain["revenue"], chain["tx"])
    chain["items_per_tx"] = _safe_div(chain["units"], chain["tx"])
    chain["revenue_delta_pct"] = _delta(chain["revenue"], sum(r["revenue"] for r in prev.values()))
    chain["margin_delta_pct"] = _delta(chain["gross_margin"], sum(r["margin"] for r in prev.values()))
    chain_reviews = conn.execute(
        "SELECT COUNT(*) AS n, ROUND(AVG(rating), 2) AS avg_rating "
        "FROM reviews WHERE date(ts) BETWEEN ? AND ?",
        (win["from"], win["to"]),
    ).fetchone()
    chain["avg_rating"] = chain_reviews["avg_rating"]
    chain["review_count"] = chain_reviews["n"]

    return {"period": win, "chain": chain, "shops": shops}


@app.get("/api/analytics/categories")
def analytics_categories(
    shop_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    conn=Depends(get_conn),
):
    """Category contribution, ranked by absolute margin dollars for the period.

    Revenue share and margin share are reported alongside so a high margin percentage on a
    small-dollar category does not read as a priority. The ranking is recomputed per period."""
    win = _resolve_window(conn, date_from, date_to)
    if win is None:
        return {"period": None, "categories": []}

    params: list = [win["from"], win["to"]]
    shop_clause = ""
    if shop_id is not None:
        shop_clause = "AND t.shop_id = ?"
        params.append(shop_id)

    rows = conn.execute(
        f"""
        WITH win AS (
            SELECT mi.category AS cat, ti.quantity AS q,
                   ti.unit_price AS up, mi.cost AS cost
            FROM transactions t
            JOIN transaction_items ti ON ti.transaction_id = t.id
            JOIN menu_items mi ON mi.id = ti.menu_item_id
            WHERE date(t.ts) BETWEEN ? AND ? {shop_clause}
        )
        SELECT cats.category,
               COALESCE(SUM(win.q), 0) AS units,
               COALESCE(ROUND(SUM(win.q * win.up), 2), 0) AS revenue,
               COALESCE(ROUND(SUM(win.q * (win.up - win.cost)), 2), 0) AS margin
        FROM (SELECT DISTINCT category FROM menu_items) cats
        LEFT JOIN win ON win.cat = cats.category
        GROUP BY cats.category
        ORDER BY margin DESC
        """,
        params,
    ).fetchall()

    total_rev = sum(r["revenue"] for r in rows)
    total_margin = sum(r["margin"] for r in rows)
    categories = [
        {
            "category": r["category"],
            "units": r["units"],
            "revenue": r["revenue"],
            "margin": r["margin"],
            "margin_pct": _pct(r["margin"], r["revenue"]),
            "revenue_share_pct": _pct(r["revenue"], total_rev),
            "margin_share_pct": _pct(r["margin"], total_margin),
        }
        for r in rows
    ]
    return {"period": win, "categories": categories}


@app.get("/api/analytics/baristas")
def analytics_baristas(
    shop_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    conn=Depends(get_conn),
):
    """Per-barista performance, benchmarked within the barista's own shop.

    In this dataset a barista only ever works their primary shop, so a chain-wide comparison
    would confound barista behaviour with shop location. Attach rate (items and pastries per
    transaction) isolates the behaviour better than average ticket alone."""
    win = _resolve_window(conn, date_from, date_to)
    if win is None:
        return {"period": None, "baristas": []}

    params: list = [win["from"], win["to"]]
    txw_shop = ""
    barista_shop = ""
    if shop_id is not None:
        txw_shop = "AND t.shop_id = ?"
        barista_shop = "WHERE b.primary_shop_id = ?"
        params.extend([shop_id, shop_id])

    rows = conn.execute(
        f"""
        WITH txw AS (
            SELECT t.id, t.barista_id, t.total
            FROM transactions t
            WHERE date(t.ts) BETWEEN ? AND ? {txw_shop}
        ),
        itx AS (
            SELECT txw.id,
                   SUM(ti.quantity) AS units,
                   SUM(CASE WHEN mi.category = 'pastry' THEN ti.quantity ELSE 0 END) AS pastry
            FROM txw
            JOIN transaction_items ti ON ti.transaction_id = txw.id
            JOIN menu_items mi ON mi.id = ti.menu_item_id
            GROUP BY txw.id
        )
        SELECT b.id, b.name, b.primary_shop_id, s.name AS shop_name,
               COUNT(txw.id) AS tx,
               COALESCE(ROUND(AVG(txw.total), 2), 0) AS avg_ticket,
               COALESCE(SUM(itx.units), 0) AS units,
               COALESCE(SUM(itx.pastry), 0) AS pastry_units
        FROM baristas b
        JOIN shops s ON s.id = b.primary_shop_id
        LEFT JOIN txw ON txw.barista_id = b.id
        LEFT JOIN itx ON itx.id = txw.id
        {barista_shop}
        GROUP BY b.id
        ORDER BY b.primary_shop_id, avg_ticket DESC
        """,
        params,
    ).fetchall()

    baristas = [
        {
            "barista_id": r["id"],
            "name": r["name"],
            "shop_id": r["primary_shop_id"],
            "shop_name": r["shop_name"],
            "tx": r["tx"],
            "avg_ticket": r["avg_ticket"],
            "items_per_tx": _safe_div(r["units"], r["tx"]),
            "pastry_attach": _safe_div(r["pastry_units"], r["tx"]),
            "shop_avg_ticket": None,
            "shop_pastry_attach": None,
            "avg_ticket_vs_shop_pct": None,
        }
        for r in rows
    ]

    by_shop: dict = {}
    for b in baristas:
        by_shop.setdefault(b["shop_id"], []).append(b)
    for shop_baristas in by_shop.values():
        active = [b for b in shop_baristas if b["tx"]]
        if not active:
            continue
        bench_ticket = round(sum(b["avg_ticket"] for b in active) / len(active), 2)
        bench_attach = round(sum((b["pastry_attach"] or 0) for b in active) / len(active), 2)
        for b in shop_baristas:
            b["shop_avg_ticket"] = bench_ticket
            b["shop_pastry_attach"] = bench_attach
            b["avg_ticket_vs_shop_pct"] = _delta(b["avg_ticket"], bench_ticket)

    return {"period": win, "baristas": baristas}


@app.get("/api/analytics/review-themes")
def analytics_review_themes(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    shop_id: Optional[int] = None,
    conn=Depends(get_conn),
):
    """Theme breakdown of negative reviews per shop, read from the classification cache.

    The LLM is never called on this path. Classifications are produced offline by
    `python -m ai.classify` and stored in a sidecar cache; this endpoint only counts and
    ranks them, so the request stays deterministic, cheap, and fast. Reviews not yet
    classified are reported as a count rather than hidden, so the surface is honest about
    its coverage.
    """
    win = _resolve_window(conn, date_from, date_to)
    if win is None:
        return {"period": None, "chain_themes": [], "shops": [], "totals": None}

    model = os.environ.get("AI_MODEL", "gpt-4o-mini")
    prompt_version = os.environ.get("AI_PROMPT_VERSION", "v1")

    sql = (
        "SELECT r.id, r.shop_id, s.name AS shop_name "
        "FROM reviews r JOIN shops s ON s.id = r.shop_id "
        "WHERE r.rating <= ? AND date(r.ts) BETWEEN ? AND ?"
    )
    params: list = [REVIEW_NEGATIVE_MAX, win["from"], win["to"]]
    if shop_id is not None:
        sql += " AND r.shop_id = ?"
        params.append(shop_id)
    rows = conn.execute(sql, params).fetchall()

    cache = ClassificationCache()
    try:
        shops: dict = {}
        chain_counts: Counter = Counter()
        classified_total = 0
        for r in rows:
            sid = r["shop_id"]
            bucket = shops.setdefault(
                sid,
                {"shop_id": sid, "name": r["shop_name"], "counts": Counter(),
                 "negative_reviews": 0, "classified": 0},
            )
            bucket["negative_reviews"] += 1
            cls = cache.get(r["id"], model, prompt_version)
            if cls is None:
                continue
            bucket["classified"] += 1
            bucket["counts"][cls.theme.value] += 1
            chain_counts[cls.theme.value] += 1
            classified_total += 1
    finally:
        cache.close()

    shop_out = []
    for b in sorted(shops.values(), key=lambda x: x["negative_reviews"], reverse=True):
        classified = b["classified"]
        themes = [
            {"theme": t, "count": n, "share_pct": _pct(n, classified)}
            for t, n in b["counts"].most_common()
        ]
        shop_out.append(
            {
                "shop_id": b["shop_id"],
                "name": b["name"],
                "negative_reviews": b["negative_reviews"],
                "classified": classified,
                "unclassified": b["negative_reviews"] - classified,
                "top_theme": themes[0]["theme"] if themes else None,
                "themes": themes,
            }
        )

    negative_total = sum(b["negative_reviews"] for b in shops.values())
    return {
        "period": win,
        "model": model,
        "prompt_version": prompt_version,
        "negative_threshold": REVIEW_NEGATIVE_MAX,
        "totals": {
            "negative_reviews": negative_total,
            "classified": classified_total,
            "unclassified": negative_total - classified_total,
        },
        "chain_themes": [
            {"theme": t, "count": n, "share_pct": _pct(n, classified_total)}
            for t, n in chain_counts.most_common()
        ],
        "shops": shop_out,
    }


# Static dashboard -- mounted last so API routes take priority.
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard not built yet")
    return FileResponse(str(index_path))
