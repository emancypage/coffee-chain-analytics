"""Offline unit tests for the AI classification layer.

No network calls. Uses FakeClassifier and direct schema construction only.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from ai.cache import ClassificationCache, classify_reviews
from ai.classifier import FakeClassifier
from ai.schema import ReviewClassification
from ai.themes import ReviewTheme


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_confidence_clamped_above_one():
    r = ReviewClassification(theme=ReviewTheme.dairy, confidence=1.5, evidence="")
    assert r.confidence == 1.0


def test_confidence_clamped_below_zero():
    r = ReviewClassification(theme=ReviewTheme.dairy, confidence=-0.3, evidence="")
    assert r.confidence == 0.0


def test_confidence_boundary_values():
    assert ReviewClassification(theme=ReviewTheme.other, confidence=0.0, evidence="").confidence == 0.0
    assert ReviewClassification(theme=ReviewTheme.other, confidence=1.0, evidence="").confidence == 1.0


def test_invalid_theme_string_rejected():
    with pytest.raises(ValidationError):
        ReviewClassification(theme="not_a_theme", confidence=0.5, evidence="")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# FakeClassifier
# ---------------------------------------------------------------------------


def test_fake_dairy():
    fc = FakeClassifier()
    result = fc.classify("The milk was sour and ruined my latte.")
    assert result.theme == ReviewTheme.dairy
    assert result.confidence > 0


def test_fake_wifi():
    fc = FakeClassifier()
    result = fc.classify("The wifi kept dropping every few minutes.")
    assert result.theme == ReviewTheme.wifi


def test_fake_empty_text_returns_unknown():
    fc = FakeClassifier()
    assert fc.classify("").theme == ReviewTheme.unknown
    assert fc.classify("   ").theme == ReviewTheme.unknown


def test_fake_unmatched_real_complaint_returns_other():
    fc = FakeClassifier()
    # A complaint that contains no keywords from the map.
    result = fc.classify("The bathroom was absolutely disgusting and had no soap.")
    assert result.theme == ReviewTheme.other


def test_fake_wait_time():
    fc = FakeClassifier()
    result = fc.classify("I waited in the queue for 20 minutes.")
    assert result.theme == ReviewTheme.wait_time


def test_fake_noise():
    fc = FakeClassifier()
    result = fc.classify("Music was way too loud, impossible to have a conversation.")
    assert result.theme == ReviewTheme.noise


def test_fake_pricing():
    fc = FakeClassifier()
    result = fc.classify("Way too expensive for what you get.")
    assert result.theme == ReviewTheme.pricing


def test_fake_staff():
    fc = FakeClassifier()
    result = fc.classify("The barista was rude and dismissive.")
    assert result.theme == ReviewTheme.staff


# ---------------------------------------------------------------------------
# Cache: get / put / version invalidation
# ---------------------------------------------------------------------------


def test_cache_miss_then_hit(tmp_path: Path):
    db = tmp_path / "test_cache.db"
    cache = ClassificationCache(path=db)

    assert cache.get(1, "model-a", "v1") is None

    classification = ReviewClassification(theme=ReviewTheme.dairy, confidence=0.9, evidence="sour milk")
    cache.put(1, classification, "model-a", "v1")

    result = cache.get(1, "model-a", "v1")
    assert result is not None
    assert result.theme == ReviewTheme.dairy
    assert result.evidence == "sour milk"

    cache.close()


def test_cache_different_prompt_version_is_miss(tmp_path: Path):
    db = tmp_path / "test_cache.db"
    cache = ClassificationCache(path=db)

    classification = ReviewClassification(theme=ReviewTheme.wifi, confidence=0.8, evidence="wifi")
    cache.put(42, classification, "gpt-4o-mini", "v1")

    # Same review_id and model, but different prompt_version: must be a miss.
    assert cache.get(42, "gpt-4o-mini", "v2") is None

    cache.close()


def test_cache_different_model_is_miss(tmp_path: Path):
    db = tmp_path / "test_cache.db"
    cache = ClassificationCache(path=db)

    classification = ReviewClassification(theme=ReviewTheme.staff, confidence=0.7, evidence="rude")
    cache.put(7, classification, "gpt-4o-mini", "v1")

    assert cache.get(7, "gpt-4-turbo", "v1") is None

    cache.close()


# ---------------------------------------------------------------------------
# classify_reviews: call count and caching behaviour
# ---------------------------------------------------------------------------


class _CountingClassifier:
    """Wraps FakeClassifier and counts how many times classify() is called."""

    def __init__(self) -> None:
        self._inner = FakeClassifier()
        self.call_count = 0

    def classify(self, text: str) -> ReviewClassification:
        self.call_count += 1
        return self._inner.classify(text)


def test_classify_reviews_returns_one_result_per_input(tmp_path: Path):
    db = tmp_path / "test_cache.db"
    cache = ClassificationCache(path=db)
    classifier = _CountingClassifier()

    reviews = [(1, "The milk was sour."), (2, "Terrible wifi."), (3, "Rude staff member.")]
    results = classify_reviews(reviews, classifier, "fake", "v1", cache=cache)

    assert len(results) == 3
    assert set(results.keys()) == {1, 2, 3}
    cache.close()


def test_classify_reviews_skips_cached_ids(tmp_path: Path):
    db = tmp_path / "test_cache.db"
    cache = ClassificationCache(path=db)

    # Pre-populate review 1 in the cache.
    cached = ReviewClassification(theme=ReviewTheme.pricing, confidence=0.95, evidence="expensive")
    cache.put(1, cached, "fake", "v1")

    classifier = _CountingClassifier()
    reviews = [(1, "overpriced"), (2, "The queue was incredibly long.")]
    classify_reviews(reviews, classifier, "fake", "v1", cache=cache)

    # Only review 2 should have triggered a classifier call.
    assert classifier.call_count == 1
    cache.close()
