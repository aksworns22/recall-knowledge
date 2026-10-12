---
name: recall-knowledge
description: Quiz the user on saved knowledge cards that are due, with short-answer questions, through the rk MCP server. Use when the user runs /recall-knowledge or asks to review or practice what they saved.
allowed-tools: mcp__rk
---

# Recall Knowledge

Question rules are in the `get_due_cards` tool description. Follow them.

1. Call `get_due_cards`. If the user gave a number with the command, pass it as `limit`. If nothing is due, call `get_stats`, say when the next card is due as a relative time, and stop.
2. For each card, print one question headed `Q<n>/<total>` and wait for the user's answer.
3. Say whether the answer was correct, vague, or wrong, give the correct answer with a one-sentence explanation, then call `record_review` before moving on.
4. Stop when the user asks. At the end call `get_stats` and report the score, the cards missed or answered vaguely, and when the next card is due.
