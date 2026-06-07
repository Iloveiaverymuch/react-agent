# W02D5 — LinkedIn Post Draft

---

## Post

I built a ReAct agent from scratch in ~150 lines of Python. No LangChain. No framework. Raw Anthropic API.

Here's what I learned after 20 structured evals and 60 A/B runs — and what actually matters.

---

**What ReAct is (in one paragraph)**

The loop is simple: Thought → Action → Observation. The model reasons about what to do, calls a tool, sees the real result, reasons again. The key implementation detail that makes it work: `stop_sequences=["Observation:"]`. Without it, the model writes its own fake tool results. That one line is the difference between a ReAct agent and a hallucination machine.

---

**The failure taxonomy (20-task eval, claude-haiku)**

After running 20 structured tasks across 4 categories — single-tool, multi-hop, search, adversarial — here's where agents actually break:

```
FM-MAXSTEP   → hits step limit without an answer (chained math)
FM-HALLUC    → makes up a tool name or observation
FM-PREMATURE → answers too early before using tools
FM-SEARCH    → DuckDuckGo fails, agent can't recover
FM-LOOP      → repeats same action, no progress
```

Most failures were multi-hop math tasks where the model wrote `math.sqrt(x)` without `print()` — got "no output", looped, hit max_steps.

The fix: replace `calc` with `run_python` — a real Python executor that auto-wraps expressions in `print()`. Suddenly chained computation just works.

---

**Does reflection help? (60 A/B runs)**

I compared 3 configs:
- Naive ReAct: 95% pass, 5.4s avg
- Fixed reflection every N=3 steps: 100% pass, 5.8s avg
- Triggered reflection (fire on error or stall only): 95% pass, 5.0s avg

**Binary pass rate hides the real story.** On a niche search task (FastMCP), naive hallucinated a confident wrong answer. Fixed-reflect said "I couldn't find reliable information." Both "passed" the binary criterion.

**Verdict: triggered reflection is the right production default.** It's an airbag — deploys when you hit something, zero cost otherwise. Fixed reflection wastes tokens on every task that was already going fine.

---

**The tool design insight that changed everything**

Tool descriptions are prompt engineering. They're injected into the agent's context and directly determine which tool gets called, with what argument, when.

Before: `def search(query: str) -> str: """Search for information using DuckDuckGo."""`

After: explicit "Use when X, do NOT use for math or local files, on failure try Y then Z."

Result: tool errors dropped, hallucinated tool calls dropped, steps per task dropped.

5 principles that matter: right tool set (fewer wins), namespacing, meaningful context, token efficiency, agent-facing descriptions (not developer-facing).

---

**The repo** → github.com/Iloveiaverymuch/react-agent

Includes: the full agent loop, 3 tools (web_search, file_read, run_python), 20-task eval suite, A/B comparison runner, failure taxonomy, and a cheatsheet synthesizing Anthropic's tool design article.

Week 2 of 22. Building in public.

#AIEngineering #LLM #ReAct #Agents #BuildingInPublic

---

## Notes for posting

- Keep the code block — engineers stop scrolling for code
- The "hallucination machine" line is the hook — leads with stakes
- Tag the Anthropic engineering blog post if possible
- Post on a weekday morning (Tuesday/Wednesday 8-9am CET gets best reach for tech audience)
- Follow up with the X thread the same day for cross-posting
