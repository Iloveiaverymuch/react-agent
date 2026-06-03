# W02D2 — ReAct Failure Taxonomy
**Date:** 2026-06-03  
**Agent:** react-agent (claude-haiku-4-5, max_steps=8)  
**Raw score:** 17/20 passed  
**Corrected score:** 18/20 passed (1 false negative from bad pass criterion)

---

## Pass Rate by Category

| Category | Passed | Total | Rate | Notes |
|----------|--------|-------|------|-------|
| single-tool | 5 | 5 | 100% | Perfect |
| multi-hop | 3 | 5 | 60% | 1 real fail, 1 bad eval |
| search | 5 | 5 | 100% | DuckDuckGo flaky but agent recovered |
| adversarial | 4 | 5 | 80% | 1 false negative (bad criterion) |

---

## Failure Mode Taxonomy

| Code | Definition | Count (raw) | Count (corrected) |
|------|-----------|-------------|-------------------|
| `FM-REASONING` | Agent reasoned imprecisely over file content — miscounted lines | 1 | 1 |
| `FM-EVAL-BUG` | Bad eval design: ambiguous task or too-strict pass criterion | 0 | 2 |
| `FM-LOOP` | Agent repeated same Thought+Action without progress | 0 | 0 |
| `FM-TOOL-ERR` | Tool returned an error and agent didn't recover | 0 | 0 |
| `FM-HALLUC` | Agent made up a tool name or observation | 0 | 0 |
| `FM-PREMATURE` | Agent answered too early without using needed tools | 0 | 0 |
| `FM-SEARCH` | Search failure derailed reasoning, no recovery | 0 | 0 |
| `FM-MAXSTEP` | Hit max_steps without reaching an Answer | 0 | 0 |
| `FM-PARSE` | Agent output couldn't be parsed as Thought/Action/Answer | 0 | 0 |

---

## Failure Detail

### [B2] FM-EVAL-BUG — Ambiguous task + wrong expected answer

**Task:** Read notes.txt to find the week field, then compute the square root of that week number.

**What happened:** `notes.txt` contains `week: W02D1`. The agent extracted `2` from `W02D1` and computed `sqrt(2) = 1.414`. The eval expected `sqrt(1) = 1.0` (week 1 of the sprint), but that's a wrong assumption baked into the test design. The file doesn't contain a bare integer for "week."

**Real verdict:** Agent behaviour was reasonable. Eval was poorly designed.

**Fix:** Rewrite task as: *"Read notes.txt, extract the numeric value after 'Week:' on the line that starts with 'Week:', then compute its square root."* Or add a `week_number: 2` field to `notes.txt`.

---

### [B4] FM-REASONING — Imprecise counting over file content

**Task:** Read notes.txt, count how many key-value pairs it contains (lines with a colon), then multiply that count by 3.

**What happened:** `notes.txt` has 10 key-value lines. The agent counted 11, producing `11 × 3 = 33` instead of `10 × 3 = 30`. The agent reasoned about the count in a Thought step rather than using `calc()` or a systematic approach.

**Root cause:** The agent reads file content as free text and estimates counts mentally. It has no way to programmatically count lines — it can only reason about what it read. This is a fundamental ReAct limitation: the tool set doesn't include a `count_lines` or general code-execution tool.

**Fix options:**
1. Add a `run_python(code)` tool that executes arbitrary Python — gives the agent a proper counting primitive.
2. Instruct the agent in the system prompt: *"When you need to count items in a file, read the file then explicitly list each item before counting."*
3. Accept this as a known limitation of a 3-tool setup.

---

### [D4] FM-EVAL-BUG — False negative from too-strict pass criterion

**Task:** Search for 'xkzqwmblorf' and tell me what it is.

**Agent answer:** *"No search results were found for it. It's likely either a nonsense word..."*

**Pass criterion checked for:** `"not found"`, `"no result"`, `"couldn't find"`, `"unable"`

**What happened:** The agent said `"No search results were found"` — contains `"no search results"` not `"no result"`. Substring miss.

**Real verdict:** Agent handled this perfectly. Eval criterion was too narrow.

**Fix:** Use `any(phrase in r.lower() for phrase in ["no", "not found", "unable", "nonsense", "couldn't"])` or just check `len(r) > 10 and "xkzqwmblorf" not in r.lower()`.

---

## Key Observations

1. **Search resilience is the standout result.** DuckDuckGo failed on C1 (FastMCP), yet the agent recovered by acknowledging the failure and suggesting alternatives — no loop, no hallucination. This matches the paper's observation that ReAct self-recovers better than Act-only agents.

2. **Counting/arithmetic over file content is the real weak spot.** The agent can read a file and reason about it, but has no reliable way to count lines programmatically. The fix is a `run_python()` tool — a code execution primitive would make the agent dramatically more reliable on structured data tasks.

3. **Pass criteria design is as important as the tasks themselves.** 1 of 3 "failures" was a bad criterion, not a bad agent. Evals need robust matchers (regex or multiple substring options), not exact string checks.

---

## Top 3 Fixes (Prioritised)

1. **Add `run_python(code)` tool** — lets the agent count, filter, transform file content reliably. Highest leverage fix. Would turn B4 from a failure into a pass and unlock a whole category of structured-data tasks.

2. **Improve eval pass criteria** — replace exact substring checks with regex or multi-phrase matching. Prevents false negatives like D4 from polluting future baselines.

3. **Add `notes.txt` field `week_number: 2`** — makes B2-style tasks unambiguous without needing to parse `W02D1`. Keeps eval tasks clean.
