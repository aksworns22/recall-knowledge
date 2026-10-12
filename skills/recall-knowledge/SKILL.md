---
name: recall-knowledge
description: Review saved knowledge cards that are due, using multiple-choice questions limited to each card's key points, and record results with FSRS via the `rk` CLI. Use when the user runs /recall-knowledge or asks to review, quiz, or practice what they saved.
allowed-tools: Bash(rk *)
---

# Recall Knowledge

Quiz the user on cards that FSRS says are due. A correct answer is rated `good`, a wrong answer `again`. `rk` handles all scheduling; never compute dates or intervals yourself.

## 1. Load due cards

```bash
rk due --limit 10
```

If the user gave a number after the command (for example `/recall-knowledge 5`), use it as `--limit`.

If `due_count` is 0, run `rk stats`, tell the user how many cards they have and when the next one is due (as a relative time such as "in 2 days"), and stop.

Otherwise say how many cards are due and how many you will ask now.

## 2. Ask one question per card

Go through the cards in order. For card number `i` (starting at 0):

**Pick the material.** Choose one item from the card's `key_points`. Vary which point you pick instead of always taking the first one, and do not test the same point twice in a session.

**Write the question.**
- It must be answerable from the card's `key_points` and `summary` alone. Never ask about anything outside them, even if you know more about the topic.
- Test understanding, not wording: ask what happens, why, or which statement is true.
- Exactly one option is correct. The three distractors come from the same domain, look similar in length and form, and are clearly contradicted by the card.
- No "all of the above", "none of the above", or trick negations.
- Write in the language of the card.

**Place the correct answer** at position `(card.id + i) % 4` (0 = A, 1 = B, 2 = C, 3 = D). This keeps answer positions spread out.

**Ask.**
- **If the `AskUserQuestion` tool is available** (Claude Code): one single-select question with `header` = `Q<i+1>/<n>` and four options in the chosen order. `label` = the option text, kept short; `description` = a brief neutral restatement that does not hint at correctness.
- **Otherwise** (Codex and other agents): print the question with options `A)` to `D)` and ask the user to reply with a letter. End your turn and wait for the reply.

Never reveal or hint at the answer before the user responds.

## 3. Grade and record immediately

- The chosen option matches the correct one: correct.
- Anything else, including "I don't know" or a free-text answer that does not clearly state the correct option: wrong.

Show the result in two or three lines: correct or wrong, the correct answer, and a one-sentence explanation based on the key point.

Then record it right away, before the next question, so progress survives if the user stops early:

```bash
rk review <card.id> good    # correct
rk review <card.id> again   # wrong
```

If the user says to stop, stop. Cards you did not record stay due.

## 4. Wrap up

Run `rk stats` and give a short summary:
- score, for example `4/5 correct`
- titles of the cards answered wrong, if any
- when the next card is due, as a relative time

## Troubleshooting

- `rk: command not found`: the user needs to run `install.sh` from the knowledge-recall repository.
- A sandbox blocks writing to `~/.knowledge` (Codex): request permission to run `rk` outside the sandbox, or tell the user to add `~/.knowledge` to `writable_roots` (see the README).
