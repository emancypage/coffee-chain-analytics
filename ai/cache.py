"""SQLite sidecar cache for review classifications.

Stored in data/classification_cache.db, separate from coffee.db.
A cache hit requires matching both model and prompt_version so that
bumping either forces reclassification.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ai.classifier import Classifier
from ai.schema import ReviewClassification
from ai.themes import ReviewTheme


def _default_cache_path() -> Path:
    """Cache location, overridable via CLASSIFICATION_CACHE_DB (used by tests)."""
    override = os.environ.get("CLASSIFICATION_CACHE_DB")
    if override:
        return Path(override)
    return Path(__file__).parent.parent / "data" / "classification_cache.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS classifications (
    review_id     INTEGER NOT NULL,
    theme         TEXT    NOT NULL,
    confidence    REAL    NOT NULL,
    evidence      TEXT    NOT NULL,
    model         TEXT    NOT NULL,
    prompt_version TEXT   NOT NULL,
    created_at    TEXT    NOT NULL,
    PRIMARY KEY (review_id, model, prompt_version)
)
"""


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


class ClassificationCache:
    def __init__(self, path: Path | None = None) -> None:
        self._conn = _connect(path or _default_cache_path())

    def get(self, review_id: int, model: str, prompt_version: str) -> ReviewClassification | None:
        row = self._conn.execute(
            "SELECT theme, confidence, evidence FROM classifications "
            "WHERE review_id = ? AND model = ? AND prompt_version = ?",
            (review_id, model, prompt_version),
        ).fetchone()
        if row is None:
            return None
        return ReviewClassification(
            theme=ReviewTheme(row["theme"]),
            confidence=row["confidence"],
            evidence=row["evidence"],
        )

    def put(
        self,
        review_id: int,
        classification: ReviewClassification,
        model: str,
        prompt_version: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO classifications
                (review_id, theme, confidence, evidence, model, prompt_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(review_id, model, prompt_version) DO UPDATE SET
                theme = excluded.theme,
                confidence = excluded.confidence,
                evidence = excluded.evidence,
                created_at = excluded.created_at
            """,
            (
                review_id,
                classification.theme.value,
                classification.confidence,
                classification.evidence,
                model,
                prompt_version,
                now,
            ),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def classify_reviews(
    reviews: Iterable[tuple[int, str]],
    classifier: Classifier,
    model: str,
    prompt_version: str,
    cache: ClassificationCache | None = None,
) -> dict[int, ReviewClassification]:
    """Classify an iterable of (review_id, text) pairs, using cache where available.

    Returns a mapping of review_id to ReviewClassification.
    """
    if cache is None:
        cache = ClassificationCache()

    results: dict[int, ReviewClassification] = {}
    for review_id, text in reviews:
        cached = cache.get(review_id, model, prompt_version)
        if cached is not None:
            results[review_id] = cached
            continue
        classification = classifier.classify(text)
        cache.put(review_id, classification, model, prompt_version)
        results[review_id] = classification

    return results
