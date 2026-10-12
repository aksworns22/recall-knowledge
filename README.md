# Recall Knowledge

**English** · [한국어](README.ko.md)

Save what you learn with an AI coding agent in one command, then review it with spaced repetition without leaving the terminal.

- `/save-knowledge` turns the concepts from your current session into review cards.
- `/recall-knowledge` quizzes you with multiple-choice questions on the cards that are due.
- Scheduling uses [FSRS](https://github.com/open-spaced-repetition/py-fsrs), the official Python implementation.
- Works in **Claude Code** and **Codex** through one MCP server, `rk-mcp`. Both share one card database.

## Why

Concepts you understand with an AI's help fade over time. Classic spaced-repetition tools ask you to write cards, switch apps, and curate content, and that friction is where most people stop. Recall Knowledge keeps the whole loop inside the agent session you were already in.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Claude Code and/or Codex

## Install

```bash
git clone https://github.com/aksworns22/recall-knowledge.git ~/recall-knowledge
cd ~/recall-knowledge
./install.sh
```

The script:

1. installs `rk` (CLI) and `rk-mcp` (MCP server) with `uv tool install --editable`, so edits in the repo take effect immediately;
2. links both skills into `~/.claude/skills/` and `~/.codex/skills/`;
3. registers the MCP server as `rk` with `claude mcp add --scope user` and `codex mcp add`;
4. creates the database at `~/.knowledge/knowledge.db`.

If `rk` is not found afterwards, run `uv tool update-shell` and open a new terminal.

### Uninstall

```bash
./install.sh --uninstall
```

This removes the CLI, the MCP registration, and the skill links. Your cards stay in `~/.knowledge/knowledge.db`.

## Usage

1. Work or study with Claude Code or Codex as usual.
2. When you want to keep something, run `/save-knowledge`.
   - With text, such as `/save-knowledge useEffect cleanup runs before the next effect`, that content is saved as a card right away.
   - Without text, the agent picks 1 to 4 concepts you found hard or that were central to the session, checks for duplicates, and asks you to confirm once.
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

## Architecture

```
/save-knowledge, /recall-knowledge   SKILL.md: the flow only
            │ MCP (stdio)
            ▼
rk-mcp                               tools, plus card and quiz rules in their descriptions
            │
            ▼
~/.knowledge/knowledge.db            SQLite + py-fsrs
```

The skills stay short because the rules for writing cards and questions live in the MCP tool descriptions. Any MCP client gets the same behavior, and the agent never builds shell commands or JSON by hand.

## MCP tools

| Tool | What it does |
|---|---|
| `search_cards(keywords, limit)` | Find cards matching any keyword, for duplicate checks |
| `save_cards(cards)` | Save one or more cards; they are due immediately |
| `update_card(card_id, ...)` | Edit a card's content; its schedule is kept |
| `get_due_cards(limit)` | Due cards, each with a random `answer_slot` (A to D) for the correct option |
| `record_review(card_id, correct)` | `true` rates Good, `false` rates Again; returns the next due date |
| `get_stats()` | Total cards, cards due now, next due date |

## `rk` CLI

The CLI uses the same database. It is meant for you, for scripting, and for debugging. Every command prints JSON to stdout. Errors go to stderr as `{"error": "..."}` with exit code 1.

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
src/rk/server.py      MCP server (rk-mcp)
src/rk/cli.py         CLI (rk)
src/rk/db.py          SQLite storage
src/rk/scheduler.py   py-fsrs wrapper
src/rk/validate.py    card validation shared by the CLI and the server
skills/               SKILL.md files shared by Claude Code and Codex
tests/                pytest suite
install.sh            installer
```

## Troubleshooting

- **The agent does not see the `rk` tools.** Run `claude mcp list` or `codex mcp list` and check that `rk` is there. Restart the session after installing.
- **Codex reports it cannot write to `~/.knowledge`.** Add the folder to the sandbox's writable roots in `~/.codex/config.toml`:

  ```toml
  [sandbox_workspace_write]
  writable_roots = ["/Users/<you>/.knowledge"]
  ```

## Development

```bash
uv run pytest
```
