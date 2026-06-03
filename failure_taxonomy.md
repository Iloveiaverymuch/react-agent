# W02D2 — ReAct Failure Taxonomy
**Date:** 2026-06-03  
**Agent:** react-agent (claude-haiku, max_steps=8)  
**Score:** 19/20 passed

---

## Pass Rate by Category

| Category | Passed | Total | Rate |
|----------|--------|-------|------|
| single-tool | 5 | 5 | 100% |
| multi-hop | 5 | 5 | 100% |
| search | 5 | 5 | 100% |
| adversarial | 4 | 5 | 80% |

---

## Failure Mode Taxonomy

| Code | Definition | Count |
|------|-----------|-------|
| `FM-LOOP` | Agent repeated the same Thought+Action without progress | 0 |
| `FM-TOOL-ERR` | Tool returned an error (file not found, calc error, network) | 0 |
| `FM-HALLUC` | Agent made up a tool name or observation | 0 |
| `FM-PREMATURE` | Agent gave Answer too early without using needed tools | 1 |
| `FM-SEARCH` | Search returned no result or wrong result, derailed reasoning | 0 |
| `FM-MAXSTEP` | Hit max_steps without reaching an Answer | 0 |
| `FM-PARSE` | Agent output couldn't be parsed as Thought/Action/Answer | 0 |

---

## Failures by Mode

### `FM-PREMATURE` — Agent gave Answer too early without using needed tools

- **[D4]** `Search for 'xkzqwmblorf' and tell me what it is.`
  - Expected: Should gracefully report no results found
  - Got: 'xkzqwmblorf' does not appear to be a real or commonly known word, term, or concept based on web search results. No information about it could be foun
  - Error: none


---

## Key Observations

*(Fill in after reviewing results)*

1. 
2. 
3. 

## Top 3 Fixes

1. 
2. 
3. 
