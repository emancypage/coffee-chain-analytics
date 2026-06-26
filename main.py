"""Coffee Chain Analytics — deliberately "dumb" dashboard backend.

No AI, no summaries, no forecasts. Raw data only.
Candidates are expected to identify where AI adds value and implement it.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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


# Static dashboard -- mounted last so API routes take priority.
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard not built yet")
    return FileResponse(str(index_path))
