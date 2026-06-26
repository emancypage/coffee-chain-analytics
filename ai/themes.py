"""Closed theme vocabulary for review classification."""

from enum import Enum


class ReviewTheme(str, Enum):
    dairy = "dairy"
    wait_time = "wait_time"
    noise = "noise"
    order_accuracy = "order_accuracy"
    pricing = "pricing"
    staff = "staff"
    wifi = "wifi"
    seating = "seating"
    other = "other"
    unknown = "unknown"


# One-line descriptions used when building the classifier system prompt.
THEME_DESCRIPTIONS: dict[ReviewTheme, str] = {
    ReviewTheme.dairy: "complaints about milk, cream, or dairy quality (sour, curdled, wrong type)",
    ReviewTheme.wait_time: "complaints about slow service, long queues, or excessive waiting",
    ReviewTheme.noise: "complaints about loud music, ambient noise, or disruptive environment",
    ReviewTheme.order_accuracy: "complaints about wrong items, missing items, or incorrect preparation",
    ReviewTheme.pricing: "complaints about high prices, poor value, or unexpected charges",
    ReviewTheme.staff: "complaints about rude, unhelpful, or inattentive staff behaviour",
    ReviewTheme.wifi: "complaints about wifi availability, speed, or reliability",
    ReviewTheme.seating: "complaints about seating availability, comfort, or cleanliness",
    ReviewTheme.other: "a genuine complaint that does not fit any of the named themes",
    ReviewTheme.unknown: "text too vague, too short, or not clearly a complaint",
}
