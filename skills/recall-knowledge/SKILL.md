---
name: recall-knowledge
description: Quiz the user on saved knowledge cards that are due, with multiple-choice questions, through the rk MCP server. Use when the user runs /recall-knowledge or asks to review or practice what they saved.
allowed-tools: mcp__rk
---

# Recall Knowledge

Question rules are in the `get_due_cards` tool description. Follow them.

1. Call `get_due_cards`. If the user gave a number with the command, pass it as `limit`. If nothing is due, call `get_stats`, say when the next card is due as a relative time, and stop.
2. For each card, ask one question with the correct option at its `answer_slot`.
   - With `AskUserQuestion`: `header` = `Q<n>/<total>`, four options in A to D order.
   - Without it: print the options as `A)` to `D)` and wait for a letter.
3. Say whether the answer was right, give the correct answer with a one-sentence explanation, then call `record_review` before moving on.
4. Stop when the user asks. At the end call `get_stats` and report the score, the cards missed, and when the next card is due.
