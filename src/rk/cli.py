"""rk command line interface. Every command prints JSON to stdout."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from . import __version__, db, scheduler


class UsageError(Exception):
    pass


def _emit(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _read_stdin_json() -> Any:
    raw = sys.stdin.read()
    if not raw.strip():
        raise UsageError("expected JSON on stdin")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise UsageError(f"invalid JSON on stdin: {e}") from e


def _str_list(value: Any, field: str, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise UsageError(f"'{field}' must be a list of non-empty strings")
    if not value and not allow_empty:
        raise UsageError(f"'{field}' must not be empty")
    return [v.strip() for v in value]


def _validate_item(item: Any, partial: bool = False) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise UsageError("each card must be a JSON object")
    out: dict[str, Any] = {}
    for key in ("title", "summary"):
        if key in item:
            if not isinstance(item[key], str) or not item[key].strip():
                raise UsageError(f"'{key}' must be a non-empty string")
            out[key] = item[key].strip()
        elif not partial:
            raise UsageError(f"missing '{key}'")
    if "key_points" in item:
        out["key_points"] = _str_list(item["key_points"], "key_points", allow_empty=False)
    elif not partial:
        raise UsageError("missing 'key_points'")
    if "tags" in item:
        out["tags"] = _str_list(item["tags"], "tags", allow_empty=True)
    if "source" in item:
        if item["source"] is not None and not isinstance(item["source"], str):
            raise UsageError("'source' must be a string")
        out["source"] = item["source"]
    return out


def _parse_now(value: str | None) -> datetime:
    if value is None:
        return scheduler.utcnow()
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def cmd_init(args, conn, now):
    return {"db": str(db.db_path()), **db.stats(conn, now)}


def cmd_add(args, conn, now):
    payload = _read_stdin_json()
    items = payload if isinstance(payload, list) else [payload]
    if not items:
        raise UsageError("no cards given")
    return {"added": db.add_cards(conn, [_validate_item(i) for i in items], now)}


def cmd_update(args, conn, now):
    fields = _validate_item(_read_stdin_json(), partial=True)
    if not fields:
        raise UsageError("nothing to update")
    return db.update_card(conn, args.id, fields)


def cmd_show(args, conn, now):
    return db.get_card(conn, args.id)


def cmd_delete(args, conn, now):
    db.delete_card(conn, args.id)
    return {"deleted": args.id}


def cmd_search(args, conn, now):
    return {"results": db.search(conn, args.keywords, args.limit)}


def cmd_due(args, conn, now):
    total, cards = db.due_cards(conn, now, args.limit)
    return {"due_count": total, "cards": cards}


def cmd_review(args, conn, now):
    return db.review_card(conn, args.id, args.rating, now)


def cmd_stats(args, conn, now):
    return db.stats(conn, now)


def cmd_export(args, conn, now):
    return {"cards": db.export(conn)}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rk", description="Recall Knowledge: spaced repetition for what you learn with AI.")
    p.add_argument("--version", action="version", version=f"rk {__version__}")
    p.add_argument("--now", help="override the current time (ISO 8601), for testing")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the database if needed").set_defaults(fn=cmd_init)
    sub.add_parser("add", help="add cards from JSON on stdin (object or array)").set_defaults(fn=cmd_add)

    s = sub.add_parser("update", help="edit a card's content from JSON on stdin; keeps its schedule")
    s.add_argument("id", type=int)
    s.set_defaults(fn=cmd_update)

    s = sub.add_parser("show", help="show one card")
    s.add_argument("id", type=int)
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("delete", help="delete one card")
    s.add_argument("id", type=int)
    s.set_defaults(fn=cmd_delete)

    s = sub.add_parser("search", help="find cards matching any keyword")
    s.add_argument("keywords", nargs="+")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(fn=cmd_search)

    s = sub.add_parser("due", help="list cards due for review")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(fn=cmd_due)

    s = sub.add_parser("review", help="record a review result")
    s.add_argument("id", type=int)
    s.add_argument("rating", choices=sorted(scheduler.RATINGS))
    s.set_defaults(fn=cmd_review)

    sub.add_parser("stats", help="card counts and next due date").set_defaults(fn=cmd_stats)
    sub.add_parser("export", help="dump every card as JSON").set_defaults(fn=cmd_export)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        now = _parse_now(args.now)
        conn = db.connect()
        try:
            _emit(args.fn(args, conn, now))
        finally:
            conn.close()
    except db.NotFound as e:
        _emit_error(f"card {e.args[0]} not found")
        return 1
    except (UsageError, ValueError) as e:
        _emit_error(str(e))
        return 1
    return 0


def _emit_error(message: str) -> None:
    print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
