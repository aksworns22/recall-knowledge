"""Thin wrapper around the official py-fsrs scheduler.

rk reviews roughly once a day from the terminal, so minute-level learning
steps are disabled and every review moves a card straight to day-level
intervals. Only two ratings are used: a correct answer is Good, a wrong
answer is Again.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler

DESIRED_RETENTION = 0.9

RATINGS = {
    "good": Rating.Good,
    "again": Rating.Again,
}

_scheduler = Scheduler(
    desired_retention=DESIRED_RETENTION,
    learning_steps=(),
    relearning_steps=(),
    enable_fuzzing=True,
)


def new_card(now: datetime) -> Card:
    """Create a card that is due immediately."""
    card = Card()
    card.due = now
    return card


def review(card: Card, rating: str, now: datetime) -> Card:
    """Apply a review and return the updated card."""
    if rating not in RATINGS:
        raise ValueError(f"rating must be one of {sorted(RATINGS)}, got {rating!r}")
    updated, _ = _scheduler.review_card(card, RATINGS[rating], review_datetime=now)
    return updated


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
