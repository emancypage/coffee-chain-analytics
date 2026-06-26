"""Batch runner: classify all negative reviews (rating <= 3) and cache results.

Usage:
    OPENAI_API_KEY=sk-... python -m ai.classify

Optional overrides:
    AI_MODEL=gpt-4o-mini          (default)
    OPENAI_BASE_URL=...           (for OpenRouter / Ollama-compatible servers)
    AI_PROMPT_VERSION=v1          (default)

Offline trial without a key:
    python -m ai.classify --fake
    Uses the keyword FakeClassifier and tags cache rows with model "fake-keyword",
    so the labels are never mistaken for real model output. To preview them in the
    dashboard, run the API with AI_MODEL=fake-keyword.
"""

import argparse
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

from ai.cache import ClassificationCache, classify_reviews

_DB_PATH = Path(__file__).parent.parent / "data" / "coffee.db"
_FAKE_MODEL = "fake-keyword"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify negative reviews into themes and cache the results."
    )
    parser.add_argument(
        "--fake",
        action="store_true",
        help="Use the offline keyword classifier instead of the LLM (no API key needed).",
    )
    args = parser.parse_args()

    prompt_version = os.environ.get("AI_PROMPT_VERSION", "v1")

    if args.fake:
        from ai.classifier import FakeClassifier

        classifier = FakeClassifier()
        model = _FAKE_MODEL
    else:
        if not os.environ.get("OPENAI_API_KEY"):
            print(
                "Error: OPENAI_API_KEY is not set. Use --fake for an offline keyword run.",
                file=sys.stderr,
            )
            sys.exit(1)
        from ai.classifier import LLMClassifier

        model = os.environ.get("AI_MODEL", "gpt-4o-mini")
        classifier = LLMClassifier(model=model, prompt_version=prompt_version)

    # Open coffee.db read-only; we never write to it.
    conn = sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, text FROM reviews WHERE rating <= 3").fetchall()
    conn.close()

    reviews = [(row["id"], row["text"]) for row in rows]
    total = len(reviews)
    print(f"Found {total} negative reviews to classify (model={model}).")

    cache = ClassificationCache()
    hits_before = sum(
        1 for rid, _ in reviews if cache.get(rid, model, prompt_version) is not None
    )
    results = classify_reviews(reviews, classifier, model, prompt_version, cache=cache)
    cache.close()

    theme_counts: Counter[str] = Counter(r.theme.value for r in results.values())
    print(f"Cache hits: {hits_before}, new calls: {total - hits_before}")
    print("\nTheme breakdown:")
    for theme, count in sorted(theme_counts.items(), key=lambda x: -x[1]):
        print(f"  {theme:<20} {count}")


if __name__ == "__main__":
    main()
