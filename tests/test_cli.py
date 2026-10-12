import io
import json
import multiprocessing as mp

import pytest

from rk import cli

CARD = {
    "title": "React Server Components serialization boundary",
    "summary": "Props passed from a server component to a client component must be serializable.",
    "key_points": ["RSC run only on the server", "Props crossing to client components must be serializable"],
    "tags": ["react", "nextjs"],
    "source": "my-app",
}

T0 = "2026-10-12T09:00:00Z"


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    path = tmp_path / "k.db"
    monkeypatch.setenv("RK_DB", str(path))
    return path


def run(capsys, monkeypatch, *argv, stdin=None):
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin if isinstance(stdin, str) else json.dumps(stdin)))
    code = cli.main(list(argv))
    out, err = capsys.readouterr()
    return code, (json.loads(out) if out else None), (json.loads(err) if err else None)


def test_add_single_and_list(capsys, monkeypatch):
    code, out, _ = run(capsys, monkeypatch, "--now", T0, "add", stdin=CARD)
    assert code == 0
    assert out["added"][0]["id"] == 1
    code, out, _ = run(capsys, monkeypatch, "--now", T0, "add", stdin=[CARD, {**CARD, "title": "Second"}])
    assert [c["id"] for c in out["added"]] == [2, 3]


def test_new_card_is_due_immediately(capsys, monkeypatch):
    run(capsys, monkeypatch, "--now", T0, "add", stdin=CARD)
    _, out, _ = run(capsys, monkeypatch, "--now", T0, "due")
    assert out["due_count"] == 1
    assert out["cards"][0]["key_points"] == CARD["key_points"]


def test_good_pushes_due_into_future(capsys, monkeypatch):
    run(capsys, monkeypatch, "--now", T0, "add", stdin=CARD)
    _, out, _ = run(capsys, monkeypatch, "--now", T0, "review", "1", "good")
    assert out["state"] == "review"
    assert out["interval_days"] >= 1
    _, out, _ = run(capsys, monkeypatch, "--now", T0, "due")
    assert out["due_count"] == 0
    _, out, _ = run(capsys, monkeypatch, "--now", "2026-12-31T00:00:00Z", "due")
    assert out["due_count"] == 1


def test_again_schedules_sooner_than_good(capsys, monkeypatch):
    run(capsys, monkeypatch, "--now", T0, "add", stdin=[CARD, CARD])
    for card_id in ("1", "2"):
        run(capsys, monkeypatch, "--now", T0, "review", card_id, "good")
    later = "2026-10-20T09:00:00Z"
    _, good, _ = run(capsys, monkeypatch, "--now", later, "review", "1", "good")
    _, again, _ = run(capsys, monkeypatch, "--now", later, "review", "2", "again")
    assert again["interval_days"] < good["interval_days"]
    _, shown, _ = run(capsys, monkeypatch, "show", "2")
    assert shown["state"] == "review"


def test_review_output_has_no_review_log(capsys, monkeypatch):
    run(capsys, monkeypatch, "--now", T0, "add", stdin=CARD)
    _, out, _ = run(capsys, monkeypatch, "--now", T0, "review", "1", "again")
    assert set(out) == {"id", "rating", "next_due", "interval_days", "state"}


def test_search_matches_any_keyword(capsys, monkeypatch):
    run(capsys, monkeypatch, "--now", T0, "add", stdin=[CARD, {**CARD, "title": "Rust ownership", "key_points": ["Each value has one owner"], "tags": ["rust"], "summary": "Ownership rules."}])
    _, out, _ = run(capsys, monkeypatch, "search", "owner", "nothing-here")
    assert [r["title"] for r in out["results"]] == ["Rust ownership"]
    _, out, _ = run(capsys, monkeypatch, "search", "NEXTJS")
    assert len(out["results"]) == 1


def test_korean_content_round_trips(capsys, monkeypatch):
    ko = {**CARD, "title": "서버 컴포넌트", "key_points": ["props는 직렬화 가능해야 한다"]}
    run(capsys, monkeypatch, "--now", T0, "add", stdin=ko)
    _, out, _ = run(capsys, monkeypatch, "search", "직렬화")
    assert out["results"][0]["title"] == "서버 컴포넌트"


def test_update_keeps_schedule(capsys, monkeypatch):
    run(capsys, monkeypatch, "--now", T0, "add", stdin=CARD)
    _, reviewed, _ = run(capsys, monkeypatch, "--now", T0, "review", "1", "good")
    _, out, _ = run(capsys, monkeypatch, "update", "1", stdin={"key_points": ["new point"]})
    assert out["key_points"] == ["new point"]
    assert out["due"] == reviewed["next_due"]


def test_delete_and_not_found(capsys, monkeypatch):
    run(capsys, monkeypatch, "--now", T0, "add", stdin=CARD)
    code, out, _ = run(capsys, monkeypatch, "delete", "1")
    assert code == 0 and out == {"deleted": 1}
    code, _, err = run(capsys, monkeypatch, "review", "1", "good")
    assert code == 1 and "not found" in err["error"]


@pytest.mark.parametrize("bad", [
    {"summary": "x", "key_points": ["a"]},
    {"title": "x", "summary": "x", "key_points": []},
    {"title": "x", "summary": "x", "key_points": "a"},
    "not json",
])
def test_add_rejects_invalid_input(capsys, monkeypatch, bad):
    code, out, err = run(capsys, monkeypatch, "add", stdin=bad if isinstance(bad, dict) else bad)
    assert code == 1 and out is None and "error" in err


def test_stats(capsys, monkeypatch):
    run(capsys, monkeypatch, "--now", T0, "add", stdin=[CARD, CARD])
    run(capsys, monkeypatch, "--now", T0, "review", "1", "good")
    _, out, _ = run(capsys, monkeypatch, "--now", T0, "stats")
    assert out["total"] == 2 and out["due_now"] == 1 and out["next_due"] > T0


def _add_many(db_path, n):
    import os, sys
    os.environ["RK_DB"] = db_path
    for _ in range(n):
        sys.stdin = io.StringIO(json.dumps(CARD))
        sys.stdout = io.StringIO()
        assert cli.main(["add"]) == 0


def test_concurrent_writers(temp_db, capsys, monkeypatch):
    ctx = mp.get_context("spawn")
    procs = [ctx.Process(target=_add_many, args=(str(temp_db), 20)) for _ in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
        assert p.exitcode == 0
    _, out, _ = run(capsys, monkeypatch, "stats")
    assert out["total"] == 80
