"""Pydantic schema for a single review classification result."""

from pydantic import BaseModel, field_validator

from ai.themes import ReviewTheme


class ReviewClassification(BaseModel):
    theme: ReviewTheme
    confidence: float  # clamped to [0.0, 1.0]
    evidence: str  # short quoted span from the review; may be empty

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))
