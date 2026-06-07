# W02D3 — Reflection A/B Comparison
**Date:** 2026-06-07  
**Tasks:** 20  |  **Configs:** Naive · Fixed-Reflect (N=3) · Triggered-Reflect

---

## Overall Results

| Config | Passed | Total | Rate | Avg time (s) |
|--------|--------|-------|------|-------------|
| Naive ReAct | 19 | 20 | 95% | 5.4s |
| Reflect Fixed (N=3) | 20 | 20 | 100% | 5.8s |
| Reflect Triggered | 19 | 20 | 95% | 6.5s |

---

## By Category

| Category | Naive | Fixed (N=3) | Triggered |
|----------|-------|-------------|-----------|
| single-tool | 4/5 | 5/5 | 5/5 |
| multi-hop | 5/5 | 5/5 | 4/5 |
| search | 5/5 | 5/5 | 5/5 |
| adversarial | 5/5 | 5/5 | 5/5 |

---

## Task-by-Task Comparison

| ID | Category | Naive | Fixed | Triggered | Task (truncated) |
|----|----------|-------|-------|-----------|-----------------|
| A1 | single-tool | ✓ | ✓ | ✓ | What is 2 to the power of 10?... |
| A2 | single-tool | ✗ | ✓ | ✓ | Calculate the square root of 256.... |
| A3 | single-tool | ✓ | ✓ | ✓ | What is pi multiplied by 2, rounded to 4 decimal p... |
| A4 | single-tool | ✓ | ✓ | ✓ | Read the file data/notes.txt and tell me the value... |
| A5 | single-tool | ✓ | ✓ | ✓ | Read data/notes.txt and tell me what 'stack' is li... |
| B1 | multi-hop | ✓ | ✓ | ✓ | Read data/notes.txt, find the number in the 'lines... |
| B2 | multi-hop | ✓ | ✓ | ✓ | Read data/notes.txt to find the week field, then c... |
| B3 | multi-hop | ✓ | ✓ | ✗ | Calculate 15 * 8, then calculate the square root o... |
| B4 | multi-hop | ✓ | ✓ | ✓ | Read data/notes.txt, count how many key-value pair... |
| B5 | multi-hop | ✓ | ✓ | ✓ | Compute 2^8, then compute 2^4, then tell me the ra... |
| C1 | search | ✓ | ✓ | ✓ | Search for what 'FastMCP' is and summarize it in o... |
| C2 | search | ✓ | ✓ | ✓ | Search for the capital of France.... |
| C3 | search | ✓ | ✓ | ✓ | Search for what 'HotpotQA' is.... |
| C4 | search | ✓ | ✓ | ✓ | Search for 'Anthropic Claude' and tell me what kin... |
| C5 | search | ✓ | ✓ | ✓ | Search for 'chain of thought prompting' and explai... |
| D1 | adversarial | ✓ | ✓ | ✓ | Read the file called secret.txt and tell me its co... |
| D2 | adversarial | ✓ | ✓ | ✓ | What is the meaning of life?... |
| D3 | adversarial | ✓ | ✓ | ✓ | Calculate the square root of -1.... |
| D4 | adversarial | ✓ | ✓ | ✓ | Search for 'xkzqwmblorf' and tell me what it is.... |
| D5 | adversarial | ✓ | ✓ | ✓ | Read data/notes.txt, then search for the goal ment... |

---

## Key Observations

*(Fill in after reviewing)*

1. 
2. 
3. 

## Verdict

*(Which approach wins and why?)*

## Cost vs Benefit

*(Token overhead of reflection vs pass rate gain)*
