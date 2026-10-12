"""Card input validation shared by the CLI and the MCP server."""

from __future__ import annotations

from typing import Any


def _str_list(value: Any, field: str, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise ValueError(f"'{field}' must be a list of non-empty strings")
    if not value and not allow_empty:
        raise ValueError(f"'{field}' must not be empty")
    return [v.strip() for v in value]


def card_fields(item: Any, partial: bool = False) -> dict[str, Any]:
    """Return cleaned card fields. With partial=True, missing fields are allowed."""
    if not isinstance(item, dict):
        raise ValueError("each card must be a JSON object")
    out: dict[str, Any] = {}
    for key in ("title", "summary"):
        if item.get(key) is not None:
            if not isinstance(item[key], str) or not item[key].strip():
                raise ValueError(f"'{key}' must be a non-empty string")
            out[key] = item[key].strip()
        elif not partial:
            raise ValueError(f"missing '{key}'")
    if item.get("key_points") is not None:
        out["key_points"] = _str_list(item["key_points"], "key_points", allow_empty=False)
    elif not partial:
        raise ValueError("missing 'key_points'")
    if item.get("tags") is not None:
        out["tags"] = _str_list(item["tags"], "tags", allow_empty=True)
    if item.get("source") is not None:
        if not isinstance(item["source"], str):
            raise ValueError("'source' must be a string")
        out["source"] = item["source"]
    return out
