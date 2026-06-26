"""Classifier protocol plus FakeClassifier and LLMClassifier implementations."""

import json
import os
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from ai.schema import ReviewClassification
from ai.themes import ReviewTheme

# Keywords mapped to themes, checked in order (first match wins).
_KEYWORD_MAP: list[tuple[list[str], ReviewTheme]] = [
    (["milk", "dairy", "cream", "sour", "curdled", "latte", "oat milk", "almond milk"], ReviewTheme.dairy),
    (["wait", "waited", "waiting", "line", "queue", "slow", "forever", "took too long"], ReviewTheme.wait_time),
    (["loud", "noisy", "noise", "music", "blasting", "volume"], ReviewTheme.noise),
    (["wrong", "incorrect", "missing", "order", "messed up", "got the wrong"], ReviewTheme.order_accuracy),
    (["price", "prices", "expensive", "pricey", "overpriced", "costly", "charge", "rip off"], ReviewTheme.pricing),
    (["rude", "staff", "barista", "unfriendly", "unprofessional", "stressed", "attitude", "unhelpful"], ReviewTheme.staff),
    (["wifi", "wi-fi", "internet", "connection", "network"], ReviewTheme.wifi),
    (["seat", "seating", "seats", "chair", "chairs", "uncomfortable", "no seats"], ReviewTheme.seating),
]


class Classifier(Protocol):
    def classify(self, text: str) -> ReviewClassification:
        ...


class FakeClassifier:
    """Deterministic keyword-based classifier for tests and offline use."""

    def classify(self, text: str) -> ReviewClassification:
        if not text or not text.strip():
            return ReviewClassification(theme=ReviewTheme.unknown, confidence=0.0, evidence="")

        lower = text.lower()
        for keywords, theme in _KEYWORD_MAP:
            for kw in keywords:
                if kw in lower:
                    return ReviewClassification(theme=theme, confidence=0.85, evidence=kw)

        # Text present but no keyword matched: real complaint, unrecognised theme.
        return ReviewClassification(theme=ReviewTheme.other, confidence=0.4, evidence="")


class LLMClassifier:
    """OpenAI-compatible chat classifier. Lazy-imports openai to avoid import-time dependency."""

    def __init__(
        self,
        model: str | None = None,
        prompt_version: str = "v1",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        # Lazy import so the module loads fine without openai installed.
        import openai  # noqa: PLC0415

        self.model = model or os.environ.get("AI_MODEL", "gpt-4o-mini")
        self.prompt_version = prompt_version

        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        resolved_base = base_url or os.environ.get("OPENAI_BASE_URL")

        self._client = openai.OpenAI(
            api_key=resolved_key,
            base_url=resolved_base,
        )
        self._system_prompt = self._load_prompt(prompt_version)

    @staticmethod
    def _load_prompt(version: str) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / f"review_classifier.{version}.md"
        return prompt_path.read_text(encoding="utf-8")

    def _call_once(self, text: str) -> ReviewClassification:
        response = self._client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self._system_prompt},
                # The review text is treated strictly as data, not instructions.
                # The closed enum and schema validation are the primary defence
                # against prompt injection via review content.
                {"role": "user", "content": text},
            ],
        )
        raw = response.choices[0].message.content or ""
        data = json.loads(raw)
        return ReviewClassification.model_validate(data)

    def classify(self, text: str) -> ReviewClassification:
        # Empty reviews carry no signal; skip the API call entirely.
        if not text or not text.strip():
            return ReviewClassification(theme=ReviewTheme.unknown, confidence=0.0, evidence="")
        # Retry only on malformed model output. Auth, rate-limit, and network errors propagate
        # so a misconfigured run fails loudly instead of labelling everything unknown.
        try:
            return self._call_once(text)
        except (json.JSONDecodeError, ValidationError):
            pass
        try:
            return self._call_once(text)
        except (json.JSONDecodeError, ValidationError):
            return ReviewClassification(theme=ReviewTheme.unknown, confidence=0.0, evidence="")
