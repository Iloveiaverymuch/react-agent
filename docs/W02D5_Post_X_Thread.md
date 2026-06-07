# W02D5 — X/Twitter Thread Draft

---

## Thread

**[1/7]**
I built a ReAct agent from scratch in ~150 lines of Python.

No LangChain. No framework. Raw Anthropic API.

After 20 evals and 60 A/B runs, here's what actually matters 🧵

---

**[2/7]**
The whole loop is this:

```
Thought → Action → Observation → repeat
```

One line makes it real: `stop_sequences=["Observation:"]`

Without it, the model writes its own fake tool results.
That's the difference between a ReAct agent and a hallucination machine.

---

**[3/7]**
I ran 20 structured tasks across 4 categories and built a failure taxonomy:

```
FM-MAXSTEP   → hits step limit (chained math)
FM-HALLUC    → makes up tool names
FM-PREMATURE → answers too early
FM-SEARCH    → can't recover from API failure
FM-LOOP      → repeats same action
```

90% of failures were multi-hop math. Fix: swap `calc` for a real `run_python` executor.

---

**[4/7]**
Does reflection help?

60 runs, 3 configs:
→ Naive ReAct: 95%, 5.4s
→ Fixed reflection (N=3): 100%, 5.8s  
→ Triggered reflection: 95%, 5.0s

**Pass rate hides the real story.**

Naive hallucinated a confident wrong answer on a hard search task.
Fixed-reflect said "I couldn't find it."

Both "passed."

---

**[5/7]**
Verdict on reflection: triggered wins in production.

Fixed = seatbelt you wear even on a 10-meter drive.
Triggered = airbag that deploys when you actually crash.

Zero overhead on easy tasks. Fires on genuine stalls or tool errors.

---

**[6/7]**
Tool descriptions are prompt engineering.

Before: `"""Search for information using DuckDuckGo."""`

After: explicit when to use, when NOT to use (math → run_python, local files → file_read), and 3 recovery strategies on failure.

Result: fewer hallucinated tool calls, fewer wasted steps.

---

**[7/7]**
Repo → github.com/Iloveiaverymuch/react-agent

Includes:
- Full agent loop (~150 LOC)
- 3 tools with agent-facing docstrings
- 20-task eval suite + failure taxonomy
- A/B comparison (naive vs reflective)
- Tool design cheatsheet (Anthropic principles applied)

Week 2 of 22. Building in public.

---

## Notes for posting

- Post tweet 1 first, then reply with the thread (not "quote tweet")
- Pin the repo link in tweet 7 — don't post it in tweet 1 or it gets buried
- Best times: Tuesday/Thursday 9-11am EST
- Reply to your own thread with the LinkedIn link after posting
