---
name: save-knowledge
description: Save what the user learned as spaced-repetition cards through the rk MCP server. Use when the user runs /save-knowledge or asks to remember or save something for later review.
allowed-tools: mcp__rk
---

# Save Knowledge

Card writing rules are in the `save_cards` tool description. Follow them.

## 1. Decide what to save

- **The user wrote content with the command** (for example `/save-knowledge useEffect cleanup runs before the next effect`): save exactly that. Expand it into a full card using this conversation for context, but do not add other concepts. Skip the confirmation in step 3.
- **The user wrote nothing**: pick 1 to 4 concepts from this conversation that the user found hard (asked about repeatedly, got wrong, needed several explanations) or that are central to what they learned. Skip what they clearly already knew. If nothing qualifies, say so and stop.

## 2. Check for duplicates

Call `search_cards` once per concept. If a card already covers it, merge with `update_card` instead of saving a new one.

## 3. Confirm once (only when you chose the concepts)

- With `AskUserQuestion`: one multiSelect question, one option per concept, `label` = title, `description` = key points.
- Without it: list the concepts with numbers and ask for numbers, `all`, or `none`. Wait for the reply.

## 4. Save and report

Call `save_cards` once with every approved card. Reply in one line, for example: `Saved 2 cards (#14, #15). Run /recall-knowledge to review.`
