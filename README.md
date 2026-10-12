# Knowledge Recall

**English** · [한국어](README.ko.md)

Save what you learn with an AI coding agent in one command, then review it with spaced repetition without leaving the terminal.

- `/save-knowledge` turns the concepts from your current session into review cards.
- `/recall-knowledge` quizzes you with multiple-choice questions on the cards that are due.
- Scheduling uses [FSRS](https://github.com/open-spaced-repetition/py-fsrs), the official Python implementation.
- Works in **Claude Code** and **Codex**. Both share one card database.

## Why

Concepts you understand with an AI's help fade over time. Classic spaced-repetition tools ask you to write cards, switch apps, and curate content, and that friction is where most people stop. Knowledge Recall keeps the whole loop inside the agent session you were already in.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Claude Code and/or Codex

## Install

```bash
git clone <this repo> ~/knowledge-recall
cd ~/knowledge-recall
./install.sh
```

The script:

1. installs the `rk` CLI with `uv tool install --editable`, so edits in the repo take effect immediately;
2. links both skills into `~/.claude/skills/` and `~/.codex/skills/`;
3. creates the database at `~/.knowledge/knowledge.db`.

If `rk` is not found afterwards, run `uv tool update-shell` and open a new terminal.

### Codex sandbox

Codex's default sandbox cannot write outside the workspace. Add this to `~/.codex/config.toml` so the skills can update your cards without approval prompts:

```toml
[sandbox_workspace_write]
writable_roots = ["/Users/<you>/.knowledge"]
```

### Uninstall

```bash
./install.sh --uninstall
```

This removes the CLI and the skill links. Your cards stay in `~/.knowledge/knowledge.db`.

## Usage

1. Work or study with Claude Code or Codex as usual.
2. When you want to keep something, run `/save-knowledge`. The agent drafts 1 to 4 cards, checks for duplicates, and asks you to confirm once.
3. Run `/recall-knowledge` whenever you like. It asks one question per due card, up to 10 at a time (`/recall-knowledge 5` for fewer).
4. A correct answer is rated **Good** and a wrong answer **Again**. FSRS picks the next review date.

New cards are due right away, so you can review them at the end of the session that produced them.

### What a card looks like

```json
{
  "title": "React Server Components serialization boundary",
  "summary": "Server components run only on the server. Anything they pass to a client component crosses a network boundary and must be serializable.",
  "key_points": [
    "Server components never ship their code to the browser",
    "Props passed to client components must be serializable",
    "Functions cannot be passed as props from server to client components"
  ],
  "tags": ["react", "nextjs"],
  "source": "my-app"
}
```

Quiz questions only use a card's `key_points` and `summary`, so you are always tested on what you chose to keep.

## `rk` CLI

Every command prints JSON to stdout. Errors go to stderr as `{"error": "..."}` with exit code 1.

| Command | What it does |
|---|---|
| `rk init` | Create the database if needed |
| `rk add` | Add cards from JSON on stdin (one object or an array) |
| `rk search <kw>...` | Find cards matching any keyword in title, summary, key points, or tags |
| `rk due [--limit N]` | List due cards, oldest first (default 10) |
| `rk review <id> good\|again` | Record a result and print the next due date |
| `rk show <id>` | Show one card with its FSRS state |
| `rk update <id>` | Edit a card's content from JSON on stdin; its schedule is kept |
| `rk delete <id>` | Delete a card |
| `rk stats` | Total cards, cards due now, next due date |
| `rk export` | Dump every card as JSON |

`--now <ISO 8601>` overrides the current time, which is handy for testing. `RK_DB` overrides the database path.

## How scheduling works

`rk` wraps `fsrs.Scheduler` with these settings:

| Setting | Value | Why |
|---|---|---|
| `desired_retention` | `0.9` | Review when recall probability drops to 90% |
| `learning_steps` | `()` | You review about once a day from a terminal, so minute-level steps do not fit |
| `relearning_steps` | `()` | Same reason; a lapse goes straight to a short day-level interval |
| `enable_fuzzing` | `True` | Spreads reviews so cards saved together do not always come back together |

Only two ratings are used: `good` for a correct answer and `again` for a wrong one. `rk` does not keep a review history, so FSRS runs with its default parameters.

## Storage

One SQLite file, `~/.knowledge/knowledge.db`, in WAL mode so Claude Code and Codex sessions can write at the same time.

```sql
CREATE TABLE cards (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  summary     TEXT NOT NULL,
  key_points  TEXT NOT NULL,         -- JSON array
  tags        TEXT NOT NULL DEFAULT '[]',
  source      TEXT,
  created_at  TEXT NOT NULL,
  fsrs_card   TEXT NOT NULL,         -- fsrs.Card serialized as JSON
  due         TEXT NOT NULL          -- copied from fsrs_card for indexing
);
```

The FSRS card is stored whole, as py-fsrs serializes it, so a py-fsrs upgrade does not need a schema change.

## Project layout

```
src/rk/cli.py         argument parsing and JSON output
src/rk/db.py          SQLite storage
src/rk/scheduler.py   py-fsrs wrapper
skills/               SKILL.md files shared by Claude Code and Codex
tests/                pytest suite
install.sh            installer
```

## Development

```bash
uv run pytest
```
