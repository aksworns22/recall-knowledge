---
name: save-knowledge
description: Save the key concepts the user learned in the current session as spaced-repetition cards using the `rk` CLI. Use when the user runs /save-knowledge or asks to remember, save, or keep what they just learned for later review.
allowed-tools: Bash(rk *)
---

# Save Knowledge

Turn what the user learned in this conversation into review cards stored by `rk`. The user should only have to confirm once.

## 1. Pick the concepts

Choose **1 to 4** concepts the user newly learned or worked to understand in this conversation.

- Save concepts, not chat history: a mechanism, a rule, a trade-off, an API behavior, a design reason.
- Skip things the user clearly already knew, generic trivia, and one-off project details (file paths, ticket numbers) unless the detail is the lesson.
- If the user gave a topic after the command (for example `/save-knowledge react hooks`), focus on that topic.
- If nothing is worth saving, say so in one line and stop.

## 2. Draft each card

| Field | Rule |
|---|---|
| `title` | Short name of the concept, at most 80 characters. |
| `summary` | 2 to 4 sentences that make sense months later without this conversation. |
| `key_points` | 3 to 5 items. Each is one standalone, verifiable fact, specific enough that a multiple-choice question with exactly one correct answer can be built from it. |
| `tags` | 1 to 4 lowercase tags (language, framework, area). |
| `source` | The current project directory name, or omit it. |

Write the card in the language the user has been using in this conversation. Keep code identifiers and technical terms in their original form.

The key points are the only material future quiz questions may use, so make sure everything worth remembering is in them.

## 3. Check for duplicates

For each concept run one search with 2 to 5 keywords, mixing English technical terms and the user's language:

```bash
rk search "server component" serialization 직렬화
```

If an existing card covers the same concept, plan to merge into it instead of adding a new card. A merge keeps that card's review schedule:

```bash
rk update 12 <<'EOF'
{"key_points": ["...existing points...", "...new point..."]}
EOF
```

## 4. Confirm once

- **If the `AskUserQuestion` tool is available** (Claude Code): ask one multiSelect question. One option per concept, `label` = the title, `description` = the key points joined with " / ". Prefix the description with "Merge into #<id>:" for merges.
- **Otherwise** (Codex and other agents): show a numbered list with each title and its key points, and ask the user to reply with numbers, `all`, or `none`. End your turn and wait for the reply.

If the user asks for edits, apply them before saving. If they choose nothing, stop.

## 5. Save

Pass all new cards in one call as a JSON array through a quoted heredoc:

```bash
rk add <<'EOF'
[
  {
    "title": "...",
    "summary": "...",
    "key_points": ["...", "...", "..."],
    "tags": ["..."],
    "source": "my-project"
  }
]
EOF
```

Run any `rk update` merges the user approved.

## 6. Report

One line, for example: `Saved 2 cards (#14, #15). They are due now; run /recall-knowledge to review.`

## Troubleshooting

- `rk: command not found`: the user needs to run `install.sh` from the knowledge-recall repository.
- A sandbox blocks writing to `~/.knowledge` (Codex): request permission to run `rk` outside the sandbox, or tell the user to add `~/.knowledge` to `writable_roots` (see the README).
- `rk` prints errors as JSON on stderr. Fix the input and retry once.
