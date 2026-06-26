"""Generate deterministic seed data for coffee-chain-analytics.

Run:
    python seed.py

Output:
    data/coffee.db (SQLite)

Data: 5 shops, 12 months, ~50k transactions, 15 baristas, ~200 reviews.
Fixed random seed for reproducibility.
"""

import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

RANDOM_SEED = 42
DB_PATH = Path(__file__).parent / "data" / "coffee.db"

END_DATE = date(2026, 4, 19)
START_DATE = END_DATE - timedelta(days=365)

SHOPS = [
    (1, "Bean & Brew Downtown", "Downtown, 5th Ave", 30, date(2020, 1, 15)),
    (2, "Riverside Coffee", "Riverside Blvd 102", 25, date(2021, 6, 1)),
    (3, "Campus Grounds", "University Quarter", 40, date(2019, 9, 10)),
    (4, "Airport Espresso", "Terminal B, Gate 12", 20, date(2022, 3, 20)),
    (5, "Park Avenue Cafe", "Park Ave 88", 35, date(2020, 11, 5)),
]

MENU_ITEMS = [
    (1, "Espresso", "coffee", 2.50, 0.50),
    (2, "Americano", "coffee", 3.00, 0.55),
    (3, "Latte", "coffee", 4.50, 0.85),
    (4, "Cappuccino", "coffee", 4.50, 0.85),
    (5, "Flat White", "coffee", 4.75, 0.85),
    (6, "Mocha", "coffee", 5.25, 1.00),
    (7, "Macchiato", "coffee", 3.75, 0.70),
    (8, "Iced Latte", "cold", 4.75, 0.90),
    (9, "Iced Americano", "cold", 3.25, 0.55),
    (10, "Cold Brew", "cold", 4.50, 0.60),
    (11, "Coffee Frappe", "cold", 5.50, 1.10),
    (12, "Iced Mocha", "cold", 5.50, 1.10),
    (13, "Iced Matcha", "cold", 5.25, 1.20),
    (14, "Earl Grey Tea", "tea", 3.50, 0.25),
    (15, "Green Tea", "tea", 3.50, 0.25),
    (16, "Chai Latte", "tea", 5.00, 0.95),
    (17, "Matcha Latte", "tea", 5.25, 1.10),
    (18, "Hibiscus Tea", "tea", 3.75, 0.30),
    (19, "Croissant", "pastry", 3.50, 0.80),
    (20, "Blueberry Muffin", "pastry", 3.00, 0.75),
    (21, "Cinnamon Roll", "pastry", 4.25, 0.95),
    (22, "Chocolate Cookie", "pastry", 2.75, 0.55),
    (23, "Walnut Brownie", "pastry", 3.25, 0.70),
    (24, "Turkey Sandwich", "food", 8.50, 3.40),
    (25, "Avocado Toast", "food", 9.75, 3.80),
    (26, "Everything Bagel", "food", 4.50, 1.40),
    (27, "Granola Bowl", "food", 7.50, 2.60),
    (28, "Pumpkin Spice Latte", "seasonal", 5.75, 1.05),
    (29, "Lavender Honey Latte", "coffee", 6.50, 1.20),
    (30, "Oat Milk Cortado", "coffee", 4.75, 0.95),
]

HOT_COFFEE = {1, 2, 3, 4, 5, 6, 7, 30}
COLD_DRINKS = {8, 9, 10, 11, 12, 13}
TEAS = {14, 15, 16, 17, 18}
PASTRIES = {19, 20, 21, 22, 23}
FOOD = {24, 25, 26, 27}
PUMPKIN_SPICE = 28
LAVENDER_HONEY = 29

BARISTAS = [
    (1, "Marcus Lee", 1, date(2023, 3, 1)),
    (2, "Sofia Ramirez", 1, date(2022, 8, 15)),
    (3, "Pedro Alvarez", 1, date(2024, 1, 10)),
    (4, "Jan Nowak", 2, date(2023, 5, 20)),
    (5, "Petra Kowalczyk", 2, date(2021, 11, 1)),
    (6, "Oliwia Wojcik", 2, date(2024, 6, 15)),
    (7, "Karolina Zielinska", 3, date(2020, 2, 10)),
    (8, "Tomasz Lewandowski", 3, date(2023, 9, 1)),
    (9, "Adam Dabrowski", 3, date(2024, 3, 5)),
    (10, "Elena Kowalski", 4, date(2022, 4, 1)),
    (11, "Rafal Mazur", 4, date(2023, 7, 20)),
    (12, "Iga Krawczyk", 4, date(2024, 2, 15)),
    (13, "Wojtek Szymanski", 4, date(2023, 10, 1)),
    (14, "Maria Chen", 5, date(2021, 8, 1)),
    (15, "Kuba Piotrowski", 5, date(2023, 12, 10)),
]

POSITIVE_REVIEWS = [
    "Great coffee, friendly staff. Will come back.",
    "My favorite spot in the neighborhood.",
    "The latte was perfect today.",
    "Cozy atmosphere, reliable wifi.",
    "Best cappuccino in town.",
    "Staff remembered my name, love it here.",
    "Quick service even during rush hour.",
    "Pastries are always fresh.",
    "Great place to work from.",
    "The barista recommended a new drink, excellent.",
    "Coffee tastes consistent, always good.",
    "Nice ambiance, went back to the office recharged.",
    "Their cold brew is the best I've had.",
    "Finally a place where they get the temperature right.",
    "Brought a friend - she loved it too.",
    "The matcha latte is on point.",
    "Staff is always welcoming.",
    "Their oat milk options are great.",
    "Genuinely good espresso.",
    "Best flat white in the city.",
]

NEUTRAL_REVIEWS = [
    "Coffee was fine. Nothing special but decent.",
    "Average experience.",
    "Decent coffee but nothing to write home about.",
    "Good enough for a quick stop.",
    "Standard coffee shop, works for me.",
    "OK coffee, OK service.",
    "Came for the wifi, stayed for the coffee. Both fine.",
]

NEGATIVE_GENERIC = [
    "Waited too long for my order.",
    "Coffee was lukewarm when served.",
    "Too noisy to work here.",
    "Prices went up again.",
    "Staff seemed stressed today.",
    "Wifi was unreliable during my visit.",
    "The music was way too loud.",
    "Seating is uncomfortable.",
    "Line was out the door, gave up.",
    "My order was wrong twice.",
]

REVIEW_TEMPLATES_B = [
    "My latte tasted off - milk might be going bad.",
    "Second time the milk tastes strange here.",
    "Something wrong with the milk, latte was sour.",
    "The cappuccino foam was weird, like the milk wasn't fresh.",
    "Milk seemed curdled in my drink, had to return it.",
    "Three visits in a row the milk taste was off.",
    "My iced latte looked like it was separating.",
    "Something wrong with the dairy quality lately.",
    "The flat white had a strange aftertaste, milk?",
    "Asked for oat milk but the regular milk they used tasted bad anyway.",
    "Milk definitely not fresh. Won't come back until they fix this.",
    "Third time this month - milk issues. Someone please tell management.",
    "Coffee was great but something off with the milk.",
]


def init_schema(conn):
    conn.executescript("""
    DROP TABLE IF EXISTS transaction_items;
    DROP TABLE IF EXISTS transactions;
    DROP TABLE IF EXISTS reviews;
    DROP TABLE IF EXISTS shifts;
    DROP TABLE IF EXISTS baristas;
    DROP TABLE IF EXISTS menu_items;
    DROP TABLE IF EXISTS shops;

    CREATE TABLE shops (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        seats INTEGER NOT NULL,
        opened_on DATE NOT NULL
    );

    CREATE TABLE menu_items (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        cost REAL NOT NULL
    );

    CREATE TABLE baristas (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        primary_shop_id INTEGER NOT NULL REFERENCES shops(id),
        hired_on DATE NOT NULL
    );

    CREATE TABLE shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barista_id INTEGER NOT NULL REFERENCES baristas(id),
        shop_id INTEGER NOT NULL REFERENCES shops(id),
        shift_date DATE NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        hours REAL NOT NULL
    );

    CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id INTEGER NOT NULL REFERENCES shops(id),
        barista_id INTEGER NOT NULL REFERENCES baristas(id),
        ts TIMESTAMP NOT NULL,
        total REAL NOT NULL
    );

    CREATE TABLE transaction_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL REFERENCES transactions(id),
        menu_item_id INTEGER NOT NULL REFERENCES menu_items(id),
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL
    );

    CREATE TABLE reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_id INTEGER NOT NULL REFERENCES shops(id),
        ts TIMESTAMP NOT NULL,
        rating INTEGER NOT NULL,
        text TEXT NOT NULL
    );

    CREATE INDEX idx_tx_shop_ts ON transactions(shop_id, ts);
    CREATE INDEX idx_tx_barista ON transactions(barista_id);
    CREATE INDEX idx_items_tx ON transaction_items(transaction_id);
    CREATE INDEX idx_items_menu ON transaction_items(menu_item_id);
    CREATE INDEX idx_reviews_shop_ts ON reviews(shop_id, ts);
    CREATE INDEX idx_shifts_barista_date ON shifts(barista_id, shift_date);
    CREATE INDEX idx_shifts_shop_date ON shifts(shop_id, shift_date);
    """)
    conn.commit()


def insert_static_data(conn):
    conn.executemany(
        "INSERT INTO shops VALUES (?, ?, ?, ?, ?)",
        [(s[0], s[1], s[2], s[3], s[4].isoformat()) for s in SHOPS],
    )
    conn.executemany("INSERT INTO menu_items VALUES (?, ?, ?, ?, ?)", MENU_ITEMS)
    conn.executemany(
        "INSERT INTO baristas VALUES (?, ?, ?, ?)",
        [(b[0], b[1], b[2], b[3].isoformat()) for b in BARISTAS],
    )
    conn.commit()


def item_seasonality(d: date, item_id: int) -> float:
    m = d.month
    if item_id in COLD_DRINKS:
        if m in (6, 7, 8):
            return 2.2
        if m in (5, 9):
            return 1.4
        if m in (12, 1, 2):
            return 0.25
        if m in (3, 11):
            return 0.55
        return 1.0
    if item_id in HOT_COFFEE or item_id in TEAS:
        if m in (12, 1, 2):
            return 1.45
        if m in (6, 7, 8):
            return 0.75
        return 1.0
    if item_id == PUMPKIN_SPICE:
        return 1.0 if m in (9, 10, 11) else 0.0
    if item_id == LAVENDER_HONEY:
        return 0.12
    return 1.0


def shop_volume(shop_id: int, d: date) -> float:
    if shop_id == 3:
        decline_start = END_DATE - timedelta(days=183)
        if d >= decline_start:
            days_in = (d - decline_start).days
            total_days = (END_DATE - decline_start).days
            return 1.0 - 0.30 * (days_in / total_days)
    return 1.0


def day_factor(d: date) -> float:
    return 1.15 if d.weekday() >= 5 else 1.0


def date_modifier(d: date) -> float:
    if date(2025, 10, 20) <= d <= date(2025, 10, 26):
        return 0.55
    return 1.0


BASE_TX_PER_DAY = {1: 30, 2: 25, 3: 28, 4: 35, 5: 22}

CATEGORY_BASE_WEIGHT = {
    "coffee": 3.0,
    "cold": 2.5,
    "tea": 1.2,
    "pastry": 1.5,
    "food": 0.8,
    "seasonal": 1.5,
}


def monthly_weights():
    """Precompute menu weights for each month (seasonality only)."""
    out = {}
    for m in range(1, 13):
        probe = date(2025, m, 15)
        weights = []
        for item in MENU_ITEMS:
            iid, _, cat, _, _ = item
            base = CATEGORY_BASE_WEIGHT[cat]
            if iid == LAVENDER_HONEY:
                base = 3.0
            w = base * item_seasonality(probe, iid)
            weights.append(w)
        out[m] = weights
    return out


def generate_shifts(conn, rng):
    rows = []
    for barista_id, _, shop_id, hired_on in BARISTAS:
        d = max(START_DATE, hired_on)
        while d <= END_DATE:
            if rng.random() < 5 / 7:
                if rng.random() < 0.5:
                    start, end, hours = "06:30", "14:30", 8.0
                else:
                    start, end, hours = "13:30", "21:30", 8.0
                rows.append((barista_id, shop_id, d.isoformat(), start, end, hours))
            d += timedelta(days=1)
    conn.executemany(
        "INSERT INTO shifts (barista_id, shop_id, shift_date, start_time, end_time, hours) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    print(f"  shifts: {len(rows)}")


def build_shift_index(conn):
    cur = conn.execute(
        "SELECT shop_id, shift_date, barista_id FROM shifts ORDER BY shop_id, shift_date"
    )
    idx = {}
    for shop_id, d, barista_id in cur.fetchall():
        idx.setdefault((shop_id, d), []).append(barista_id)
    return idx


def generate_transactions(conn, rng):
    menu_by_id = {m[0]: m for m in MENU_ITEMS}
    item_ids = [m[0] for m in MENU_ITEMS]
    weights_by_month = monthly_weights()
    shift_idx = build_shift_index(conn)
    fallback_baristas_per_shop = {s: [b[0] for b in BARISTAS if b[2] == s] for s in range(1, 6)}

    tx_rows = []
    item_rows = []
    tx_id = 1

    d = START_DATE
    while d <= END_DATE:
        month_weights = weights_by_month[d.month]
        for shop_id in (1, 2, 3, 4, 5):
            count = BASE_TX_PER_DAY[shop_id]
            count *= shop_volume(shop_id, d) * day_factor(d) * date_modifier(d)
            count *= rng.uniform(0.85, 1.15)
            count = max(1, int(round(count)))

            baristas_today = shift_idx.get((shop_id, d.isoformat())) or fallback_baristas_per_shop[shop_id]

            for _ in range(count):
                barista_id = rng.choice(baristas_today)
                minutes = rng.randint(6 * 60 + 30, 21 * 60)
                ts = datetime(d.year, d.month, d.day, minutes // 60, minutes % 60)

                n_items = rng.choices([1, 2, 3], weights=[0.55, 0.35, 0.10], k=1)[0]
                total = 0.0
                items_for_tx = []
                for _ in range(n_items):
                    mi = rng.choices(item_ids, weights=month_weights, k=1)[0]
                    qty = 1 if rng.random() > 0.1 else 2
                    price = menu_by_id[mi][3]
                    total += price * qty
                    items_for_tx.append((tx_id, mi, qty, price))

                if barista_id == 10 and rng.random() < 0.45:
                    mi = rng.choice(list(PASTRIES))
                    qty = 1
                    price = menu_by_id[mi][3]
                    total += price * qty
                    items_for_tx.append((tx_id, mi, qty, price))

                tx_rows.append((tx_id, shop_id, barista_id, ts.isoformat(), round(total, 2)))
                item_rows.extend(items_for_tx)
                tx_id += 1
        d += timedelta(days=1)

    conn.executemany("INSERT INTO transactions VALUES (?, ?, ?, ?, ?)", tx_rows)
    conn.executemany(
        "INSERT INTO transaction_items (transaction_id, menu_item_id, quantity, unit_price) "
        "VALUES (?, ?, ?, ?)",
        item_rows,
    )
    conn.commit()
    print(f"  transactions: {len(tx_rows)}  items: {len(item_rows)}")


def generate_reviews(conn, rng):
    rows = []
    cluster_start = date(2025, 10, 1)
    cluster_end = date(2025, 12, 31)
    for text in REVIEW_TEMPLATES_B:
        offset = rng.randint(0, (cluster_end - cluster_start).days)
        review_date = cluster_start + timedelta(days=offset)
        ts = datetime.combine(review_date, datetime.min.time()) + timedelta(
            hours=rng.randint(8, 20), minutes=rng.randint(0, 59)
        )
        rating = rng.choice([1, 2, 2])
        rows.append((2, ts.isoformat(), rating, text))

    baseline_count = 200 - len(REVIEW_TEMPLATES_B)
    for _ in range(baseline_count):
        shop_id = rng.choices([1, 2, 3, 4, 5], weights=[1.2, 0.9, 1.1, 0.9, 0.9], k=1)[0]
        offset = rng.randint(0, 365)
        review_date = START_DATE + timedelta(days=offset)
        ts = datetime.combine(review_date, datetime.min.time()) + timedelta(
            hours=rng.randint(8, 20), minutes=rng.randint(0, 59)
        )
        r = rng.random()
        if r < 0.55:
            text = rng.choice(POSITIVE_REVIEWS)
            rating = rng.choice([4, 5, 5, 5])
        elif r < 0.80:
            text = rng.choice(NEUTRAL_REVIEWS)
            rating = rng.choice([3, 3, 4])
        else:
            text = rng.choice(NEGATIVE_GENERIC)
            rating = rng.choice([1, 2, 2, 3])
        rows.append((shop_id, ts.isoformat(), rating, text))

    conn.executemany(
        "INSERT INTO reviews (shop_id, ts, rating, text) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    print(f"  reviews: {len(rows)}")


def main():
    rng = random.Random(RANDOM_SEED)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    print(f"Creating {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")

    init_schema(conn)
    insert_static_data(conn)
    generate_shifts(conn, rng)
    generate_transactions(conn, rng)
    generate_reviews(conn, rng)

    conn.close()
    size_mb = DB_PATH.stat().st_size / 1024 / 1024
    print(f"Done. DB size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
