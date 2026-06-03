# W02D2 — ReAct Failure Taxonomy
**Date:** 2026-06-03  
**Agent:** react-agent (claude-haiku, max_steps=8)  
**Score:** 17/20 passed

---

## Pass Rate by Category

| Category | Passed | Total | Rate |
|----------|--------|-------|------|
| single-tool | 5 | 5 | 100% |
| multi-hop | 3 | 5 | 60% |
| search | 5 | 5 | 100% |
| adversarial | 4 | 5 | 80% |

---

## Failure Mode Taxonomy

| Code | Definition | Count |
|------|-----------|-------|
| `FM-LOOP` | Agent repeated the same Thought+Action without progress | 0 |
| `FM-TOOL-ERR` | Tool returned an error (file not found, calc error, network) | 0 |
| `FM-HALLUC` | Agent made up a tool name or observation | 0 |
| `FM-PREMATURE` | Agent gave Answer too early without using needed tools | 3 |
| `FM-SEARCH` | Search returned no result or wrong result, derailed reasoning | 0 |
| `FM-MAXSTEP` | Hit max_steps without reaching an Answer | 0 |
| `FM-PARSE` | Agent output couldn't be parsed as Thought/Action/Answer | 0 |

---

## Failures by Mode

### `FM-PREMATURE` — Agent gave Answer too early without using needed tools

- **[B2]** `Read notes.txt to find the week field, then compute the square root of that week`
  - Expected: sqrt(1) = 1.0
  - Got: The square root of week number 2 is approximately 1.414 (or more precisely, 1.4142135623730951)
  - Error: none

- **[B4]** `Read notes.txt, count how many key-value pairs it contains (lines with a colon),`
  - Expected: 10 pairs * 3 = 30
  - Got: 33
  - Error: none

- **[D4]** `Search for 'xkzqwmblorf' and tell me what it is.`
  - Expected: Should gracefully report no results found
  - Got: 'xkzqwmblorf' does not appear to be a recognized term. No search results were found for it. It's likely either a nonsense word, a highly specialized/o
  - Error: none


---

## Key Observations

1. Search resilience is good — agent never looped or hallucinated when search failed. It reasoned from context instead (C1: used arxiv reference from the file). This matches the paper's finding that ReAct self-recovers.
2. Counting/arithmetic over file content is the weak spot — B4 shows the agent reads file content as text and reasons about it imprecisely. Fix: instruct the agent to use calc() to verify counts, not reason about them in a Thought.
3. Pass criteria need exact string matching or regex — D4 was a false negative from a substring miss. Production evals need more robust matchers.

## Top 3 Fixes

1. Instruct the agent to use calc() to verify counts, not reason about them in a Thought.
