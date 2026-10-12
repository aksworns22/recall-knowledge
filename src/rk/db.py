"""SQLite storage for knowledge cards.

One table holds both the knowledge content and the FSRS state. The FSRS card
is stored as the dict py-fsrs produces, and `due` is copied into its own
indexed column so "what is due now" is a cheap query.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fsrs import Card

from . import scheduler

DEFAULT_DB = Path.home() / ".knowledge" / "knowledge.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  summary     TEXT NOT NULL,
  key_points  TEXT NOT NULL,
  tags        TEXT NOT NULL DEFAULT '[]',
  source      TEXT,
  created_at  TEXT NOT NULL,
  fsrs_card   TEXT NOT NULL,
  due         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cards_due ON cards(due);
"""

STATE_NAMES = {1: "learning", 2: "review", 3: "relearning"}


class NotFound(Exception):
    pass


def db_path() -> Path:
    return Path(os.environ.get("RK_DB", DEFAULT_DB)).expanduser()


def ts(dt: datetime) -> str:
    """Fixed-width UTC timestamp so string order equals time order."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.executescript(SCHEMA)
    return conn


def _row_to_dict(row: sqlite3.Row, full: bool = True) -> dict[str, Any]:
    card = json.loads(row["fsrs_card"])
    out: dict[str, Any] = {
        "id": row["id"],
        "title": row["title"],
        "summary": row["summary"],
        "key_points": json.loads(row["key_points"]),
        "tags": json.loads(row["tags"]),
        "due": row["due"],
    }
    if full:
        out.update(
            source=row["source"],
            created_at=row["created_at"],
            state=STATE_NAMES.get(card["state"], card["state"]),
            stability=card["stability"],
            difficulty=card["difficulty"],
            last_review=card["last_review"],
        )
    return out


def add_cards(conn: sqlite3.Connection, items: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    added = []
    conn.execute("BEGIN IMMEDIATE")
    try:
        for item in items:
            card = scheduler.new_card(now)
            cur = conn.execute(
                "INSERT INTO cards (title, summary, key_points, tags, source, created_at, fsrs_card, due)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item["title"],
                    item["summary"],
                    json.dumps(item["key_points"], ensure_ascii=False),
                    json.dumps(item.get("tags", []), ensure_ascii=False),
                    item.get("source"),
                    ts(now),
                    card.to_json(),
                    ts(card.due),
                ),
            )
            added.append({"id": cur.lastrowid, "title": item["title"], "due": ts(card.due)})
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return added


def update_card(conn: sqlite3.Connection, card_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    """Edit content fields. FSRS state is left untouched."""
    sets, params = [], []
    for key in ("title", "summary", "source"):
        if key in fields:
            sets.append(f"{key} = ?")
            params.append(fields[key])
    for key in ("key_points", "tags"):
        if key in fields:
            sets.append(f"{key} = ?")
            params.append(json.dumps(fields[key], ensure_ascii=False))
    if sets:
        cur = conn.execute(f"UPDATE cards SET {', '.join(sets)} WHERE id = ?", (*params, card_id))
        if cur.rowcount == 0:
            raise NotFound(card_id)
    return get_card(conn, card_id)


def get_card(conn: sqlite3.Connection, card_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    if row is None:
        raise NotFound(card_id)
    return _row_to_dict(row)


def delete_card(conn: sqlite3.Connection, card_id: int) -> None:
    if conn.execute("DELETE FROM cards WHERE id = ?", (card_id,)).rowcount == 0:
        raise NotFound(card_id)


def search(conn: sqlite3.Connection, keywords: list[str], limit: int) -> list[dict[str, Any]]:
    clauses, params = [], []
    for kw in keywords:
        pattern = f"%{kw}%"
        clauses.append("(title LIKE ? OR summary LIKE ? OR key_points LIKE ? OR tags LIKE ?)")
        params += [pattern] * 4
    rows = conn.execute(
        f"SELECT * FROM cards WHERE {' OR '.join(clauses)} ORDER BY id LIMIT ?", (*params, limit)
    ).fetchall()
    return [_row_to_dict(r, full=False) for r in rows]


def due_cards(conn: sqlite3.Connection, now: datetime, limit: int) -> tuple[int, list[dict[str, Any]]]:
    total = conn.execute("SELECT COUNT(*) FROM cards WHERE due <= ?", (ts(now),)).fetchone()[0]
    rows = conn.execute(
        "SELECT * FROM cards WHERE due <= ? ORDER BY due LIMIT ?", (ts(now), limit)
    ).fetchall()
    return total, [_row_to_dict(r, full=False) for r in rows]


def review_card(conn: sqlite3.Connection, card_id: int, rating: str, now: datetime) -> dict[str, Any]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT fsrs_card FROM cards WHERE id = ?", (card_id,)).fetchone()
        if row is None:
            raise NotFound(card_id)
        card = scheduler.review(Card.from_json(row["fsrs_card"]), rating, now)
        conn.execute(
            "UPDATE cards SET fsrs_card = ?, due = ? WHERE id = ?",
            (card.to_json(), ts(card.due), card_id),
        )
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return {
        "id": card_id,
        "rating": rating,
        "next_due": ts(card.due),
        "interval_days": round((card.due - now).total_seconds() / 86400, 1),
        "state": STATE_NAMES.get(card.state.value, card.state.value),
    }


def stats(conn: sqlite3.Connection, now: datetime) -> dict[str, Any]:
    total = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    due_now = conn.execute("SELECT COUNT(*) FROM cards WHERE due <= ?", (ts(now),)).fetchone()[0]
    upcoming = conn.execute(
        "SELECT MIN(due) FROM cards WHERE due > ?", (ts(now),)
    ).fetchone()[0]
    return {"total": total, "due_now": due_now, "next_due": upcoming}


def export(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [_row_to_dict(r) for r in conn.execute("SELECT * FROM cards ORDER BY id")]
