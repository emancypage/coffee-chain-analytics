"""SQLite connection helper for FastAPI dependency injection."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "coffee.db"


def get_conn():
    # check_same_thread=False: FastAPI runs sync endpoints (and their generator
    # dependencies) on a threadpool, and the setup and the handler are not
    # guaranteed to land on the same worker. Each request still gets its own
    # connection and a request runs sequentially, so there is no shared-state race.
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()
