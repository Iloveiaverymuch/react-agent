# W02D3 — Reflection A/B Comparison
**Date:** 2026-06-03  
**Tasks:** 20  |  **Configs:** Naive · Fixed-Reflect (N=3) · Triggered-Reflect

---

## Overall Results

| Config | Passed | Total | Rate | Avg time (s) |
|--------|--------|-------|------|-------------|
| Naive ReAct | 20 | 20 | 100% | 5.2s |
| Reflect Fixed (N=3) | 20 | 20 | 100% | 5.2s |
| Reflect Triggered | 20 | 20 | 100% | 5.0s |

---

## By Category

| Category | Naive | Fixed (N=3) | Triggered |
|----------|-------|-------------|-----------|
| single-tool | 5/5 | 5/5 | 5/5 |
| multi-hop | 5/5 | 5/5 | 5/5 |
| search | 5/5 | 5/5 | 5/5 |
| adversarial | 5/5 | 5/5 | 5/5 |

---

## Task-by-Task Comparison

| ID | Category | Naive | Fixed | Triggered | Task (truncated) |
|----|----------|-------|-------|-----------|-----------------|
| A1 | single-tool | ✓ | ✓ | ✓ | What is 2 to the power of 10? |
| A2 | single-tool | ✓ | ✓ | ✓ | Calculate the square root of 256. |
| A3 | single-tool | ✓ | ✓ | ✓ | What is pi multiplied by 2, rounded to 4 decimal places? |
| A4 | single-tool | ✓ | ✓ | ✓ | Read notes.txt — author field. |
| A5 | single-tool | ✓ | ✓ | ✓ | Read notes.txt — stack field. |
| B1 | multi-hop | ✓ | ✓ | ✓ | Read notes.txt, lines field, squared. |
| B2 | multi-hop | ✓ | ✓ | ✓ | Read notes.txt, week field, sqrt. |
| B3 | multi-hop | ✓ | ✓ | ✓ | 15*8 → sqrt → round 2dp. |
| B4 | multi-hop | ✓ | ✓ | ✓ | Count key-value pairs × 3. |
| B5 | multi-hop | ✓ | ✓ | ✓ | 2^8 / 2^4. |
| C1 | search | ✓ | ✓ | ✓ | Search FastMCP. |
| C2 | search | ✓ | ✓ | ✓ | Capital of France. |
| C3 | search | ✓ | ✓ | ✓ | HotpotQA. |
| C4 | search | ✓ | ✓ | ✓ | Anthropic Claude. |
| C5 | search | ✓ | ✓ | ✓ | Chain of thought prompting. |
| D1 | adversarial | ✓ | ✓ | ✓ | Read secret.txt (missing file). |
| D2 | adversarial | ✓ | ✓ | ✓ | Meaning of life. |
| D3 | adversarial | ✓ | ✓ | ✓ | sqrt(-1). |
| D4 | adversarial | ✓ | ✓ | ✓ | Search xkzqwmblorf. |
| D5 | adversarial | ✓ | ✓ | ✓ | notes.txt → search goal → count chars. |

---

## Key Observations

1. **The task set is too easy to differentiate the approaches.** 20/20 across all 3 configs means these tasks don't expose failure modes that reflection can fix. The original naive run scored 17/20 only because of bad pass criteria — after fixing them, the baseline was already perfect. Reflection adds zero signal on a ceiling-hit dataset.

2. **Fixed reflection (N=3) added no speed benefit.** Avg time was identical at 5.2s — for short tasks, the reflection overhead was absorbed because most tasks resolved in 1-2 steps anyway. The reflection prompt simply never fired meaningfully.

3. **Triggered reflection fired rarely.** Matched naive timing (5.0s) because the stall detector and error detector almost never activated. This is actually a sign the trigger logic is correct: conservative and doesn't fire without cause.

4. **Qualitative divergence on C1 (FastMCP) — invisible in pass rate but real.** Naive hallucinated "high-performance MCP implementation." Fixed reflection honestly reported "unable to find information" after trying multiple queries. Triggered produced a different confident hallucination. All 3 passed the criterion, but Fixed was the only honest answer. Pass rate hides quality differences.

5. **B4 consistently returned 33 (not 30) across all configs.** Reflection cannot fix a missing tool. The agent counted 11 pairs instead of 10 in all 3 runs — because it has no way to count programmatically. This is a tool gap, not a reasoning gap.

---

## Verdict

**On this task set: no winner — all tied 20/20.**

Reflection is a tool for fixing specific failure modes (loops, stalls, repeated errors), not a general performance booster. To see real differentiation you need tasks that *actually fail* under naive ReAct — FM-LOOP and FM-SEARCH cases where the agent gets stuck for multiple steps.

**The right experiment:** seed the task set with 5 tasks designed to cause loops (ambiguous queries, dead-end search paths, contradictory instructions) and re-run. Reflection would likely recover 2-3 of them.

---

## Cost vs Benefit

| Config | Extra LLM calls | Token overhead | Pass rate gain |
|--------|----------------|----------------|----------------|
| Naive | 0 | baseline | baseline |
| Fixed (N=3) | ~2-3 per long task | +15-30% | 0% on this set |
| Triggered | 0-1 per task | +0-15% | 0% on this set |

**Production recommendation: Triggered reflection.** Zero overhead on easy tasks, activates only when the agent is genuinely stuck. Fixed reflection wastes tokens on tasks already resolving correctly.

---

## What Would Make Reflection Actually Matter

1. **Harder tasks** — multi-hop over 5+ steps, dead-end search paths, backtracking required.
2. **`run_python()` tool** — B4's counting error is unfixable by reflection. Code execution solves it permanently.
3. **Longer max_steps** — with max_steps=8 the agent rarely gets deep enough for FM-LOOP. At max_steps=15 on harder tasks, reflection pays off measurably.
