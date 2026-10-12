"""End-to-end tests that talk to rk-mcp over stdio like a real MCP client."""

import json
import os
import sys

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

CARD = {
    "title": "FSRS stability",
    "summary": "Stability is the number of days until recall probability falls to 90%.",
    "key_points": ["Stability is the interval at which retrievability falls to 0.9", "A Good rating increases stability"],
    "tags": ["fsrs"],
}


def call(db_path, steps):
    """Run (tool, args) steps in one server session and return parsed results."""

    async def go():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "rk.server"], env={**os.environ, "RK_DB": str(db_path)}
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                out = []
                for name, args in steps:
                    res = await session.call_tool(name, args)
                    text = res.content[0].text if res.content else ""
                    out.append((res.is_error, text if res.is_error else json.loads(text)))
                return out

    return anyio.run(go)


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "k.db"


def test_save_review_flow(db_path):
    results = call(db_path, [
        ("save_cards", {"cards": [CARD]}),
        ("search_cards", {"keywords": ["stability"]}),
        ("get_due_cards", {}),
        ("record_review", {"card_id": 1, "result": "correct"}),
        ("get_stats", {}),
    ])
    assert not any(err for err, _ in results)
    saved, found, due, reviewed, stats = (r for _, r in results)
    assert saved["added"][0]["id"] == 1
    assert found["results"][0]["title"] == "FSRS stability"
    assert due["due_count"] == 1 and due["cards"][0]["id"] == 1
    assert reviewed["rating"] == "good" and reviewed["interval_days"] >= 1
    assert stats == {"total": 1, "due_now": 0, "next_due": reviewed["next_due"]}


def test_wrong_answer_rates_again(db_path):
    (_, _), (err, reviewed) = call(db_path, [
        ("save_cards", {"cards": [CARD]}),
        ("record_review", {"card_id": 1, "result": "wrong"}),
    ])
    assert not err and reviewed["rating"] == "again"


def test_vague_answer_rates_hard(db_path):
    (_, _), (err, reviewed) = call(db_path, [
        ("save_cards", {"cards": [CARD]}),
        ("record_review", {"card_id": 1, "result": "vague"}),
    ])
    assert not err and reviewed["rating"] == "hard"


def test_update_and_errors(db_path):
    results = call(db_path, [
        ("save_cards", {"cards": [CARD]}),
        ("update_card", {"card_id": 1, "key_points": ["merged point"]}),
        ("update_card", {"card_id": 99, "title": "x"}),
        ("save_cards", {"cards": [{**CARD, "key_points": []}]}),
    ])
    assert results[1] == (False, results[1][1]) and results[1][1]["key_points"] == ["merged point"]
    assert results[2][0] and "not found" in results[2][1]
    assert results[3][0]
