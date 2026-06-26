"""Batch runner: classify all negative reviews (rating <= 3) and cache results.

Usage:
    OPENAI_API_KEY=sk-... python -m ai.classify

Optional overrides:
    AI_MODEL=gpt-4o-mini          (default)
    OPENAI_BASE_URL=...           (for OpenRouter / Ollama-compatible servers)
    AI_PROMPT_VERSION=v1          (default)
"""

import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

from ai.cache import ClassificationCache, classify_reviews
from ai.classifier import LLMClassifier

_DB_PATH = Path(__file__).parent.parent / "data" / "coffee.db"


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    model = os.environ.get("AI_MODEL", "gpt-4o-mini")
    prompt_version = os.environ.get("AI_PROMPT_VERSION", "v1")

    # Open coffee.db read-only; we never write to it.
    conn = sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, text FROM reviews WHERE rating <= 3").fetchall()
    conn.close()

    reviews = [(row["id"], row["text"]) for row in rows]
    total = len(reviews)
    print(f"Found {total} negative reviews to classify.")

    cache = ClassificationCache()

    # Count cache hits before running.
    hits_before = sum(
        1 for rid, _ in reviews if cache.get(rid, model, prompt_version) is not None
    )

    classifier = LLMClassifier(model=model, prompt_version=prompt_version)
    results = classify_reviews(reviews, classifier, model, prompt_version, cache=cache)

    cache.close()

    new_calls = total - hits_before
    theme_counts: Counter[str] = Counter(r.theme.value for r in results.values())

    print(f"Cache hits: {hits_before}, new LLM calls: {new_calls}")
    print("\nTheme breakdown:")
    for theme, count in sorted(theme_counts.items(), key=lambda x: -x[1]):
        print(f"  {theme:<20} {count}")


if __name__ == "__main__":
    main()
