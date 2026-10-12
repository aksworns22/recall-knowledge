"""rk MCP server (stdio).

Exposes the card store to Claude Code, Codex, or any MCP client. Card writing
and quiz rules live in the tool descriptions, so the skills only describe the
flow.
"""

from __future__ import annotations

import random
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from . import db, scheduler
from .validate import card_fields

INSTRUCTIONS = """\
rk stores what the user has learned as spaced-repetition cards scheduled by FSRS.
Save with search_cards then save_cards. Review with get_due_cards, one
multiple-choice question per card, then record_review after every answer.
Never compute review dates yourself; rk does it."""

mcp = MCPServer("rk", instructions=INSTRUCTIONS)


class CardInput(BaseModel):
    title: str = Field(description="Short name of the concept, at most 80 characters.")
    summary: str = Field(description="2 to 4 sentences that make sense months later without the original conversation.")
    key_points: list[str] = Field(
        min_length=1,
        description=(
            "3 to 5 items. Each is one standalone, verifiable fact, specific enough that a "
            "multiple-choice question with exactly one correct answer can be built from it. "
            "Quizzes use only these points and the summary."
        ),
    )
    tags: list[str] = Field(default_factory=list, description="1 to 4 lowercase tags (language, framework, area).")
    source: str | None = Field(default=None, description="Project directory name, if any.")


def _with_conn(fn, *args):
    conn = db.connect()
    try:
        return fn(conn, *args)
    except db.NotFound as e:
        raise ToolError(f"card {e.args[0]} not found") from None
    finally:
        conn.close()


def _fields(item: dict[str, Any], partial: bool = False) -> dict[str, Any]:
    try:
        return card_fields(item, partial)
    except ValueError as e:
        raise ToolError(str(e)) from None


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def search_cards(
    keywords: Annotated[list[str], Field(min_length=1, description="2 to 5 keywords; mix English terms and the user's language.")],
    limit: int = 20,
) -> dict[str, Any]:
    """Find saved cards matching any keyword. Call before save_cards to avoid duplicates."""
    return {"results": _with_conn(db.search, keywords, limit)}


@mcp.tool()
def save_cards(cards: list[CardInput]) -> dict[str, Any]:
    """Save knowledge cards, one concept per card. Write cards in the user's language and keep
    code identifiers and technical terms in their original form. New cards are due immediately."""
    items = [_fields(c.model_dump()) for c in cards]
    if not items:
        raise ToolError("no cards given")
    return {"added": _with_conn(db.add_cards, items, scheduler.utcnow())}


@mcp.tool()
def update_card(
    card_id: int,
    title: str | None = None,
    summary: str | None = None,
    key_points: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Edit an existing card, for example to merge a new point into a duplicate.
    Pass only the fields to change; lists replace the old value. The review schedule is kept."""
    fields = _fields(
        {"title": title, "summary": summary, "key_points": key_points, "tags": tags}, partial=True
    )
    if not fields:
        raise ToolError("nothing to update")
    return _with_conn(db.update_card, card_id, fields)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_due_cards(limit: int = 10) -> dict[str, Any]:
    """List cards due for review, oldest first.

    For each card ask one four-option multiple-choice question:
    - Build it only from the card's key_points and summary. Never ask about anything else.
    - Pick a different key point each time; test understanding, not wording.
    - Exactly one option is correct. Distractors come from the same domain, match the correct
      option in length and form, and are clearly contradicted by the card.
    - No "all/none of the above" or trick negations. Use the card's language.
    - Put the correct option at the card's answer_slot (A to D).
    Do not reveal the answer before the user responds. Call record_review right after each answer."""
    total, cards = _with_conn(db.due_cards, scheduler.utcnow(), limit)
    for card in cards:
        card["answer_slot"] = random.choice("ABCD")
    return {"due_count": total, "cards": cards}


@mcp.tool()
def record_review(card_id: int, correct: bool) -> dict[str, Any]:
    """Record one quiz answer. correct=true rates the card Good, false rates it Again
    (including "I don't know" or an unclear answer). Returns the next due date."""
    return _with_conn(db.review_card, card_id, "good" if correct else "again", scheduler.utcnow())


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_stats() -> dict[str, Any]:
    """Total cards, cards due now, and the next due date (UTC)."""
    return _with_conn(db.stats, scheduler.utcnow())


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
