# react-agent

ReAct (Reasoning + Acting) agent built from scratch in raw Python — no LangChain, no framework.

Part of a 22-week AI engineering sprint. This repo covers **W02D1–D3**: implement ReAct, stress-test it with 20 structured evals, and compare naive vs reflective variants.

**Reference:** [Yao et al., ICLR 2023](https://arxiv.org/abs/2210.03629)

---

## What it does

Implements the Thought → Action → Observation loop:

```
Question
  │
  ▼
Thought: what should I do?
Action: tool_name(argument)
  │
  ▼
Observation: <real tool result>
  │
  ▼
Thought: what does this tell me?
Action: ...
  │
  ▼
Answer: <final answer>
```

Key implementation detail: `stop_sequences=["Observation:"]` prevents the model from hallucinating its own tool results — the loop always pauses and waits for real observations.

---

## Tools

| Tool | What it does |
|------|-------------|
| `calc(expr)` | Safe math evaluation — `sqrt`, `**`, `pi`, `log`, etc. Whitelist-only, no arbitrary `eval()`. |
| `file_read(path)` | Read a local file (first 2000 chars). Absolute or relative path. |
| `search(query)` | DuckDuckGo Instant Answer API — no key needed. Flaky on niche queries; agent self-recovers. |

---

## Files

```
agent.py              — Naive ReAct loop (~130 LOC): LLM call → parse Thought/Action → execute tool → feed Observation
agent_reflective.py   — ReAct + reflection (~180 LOC): two modes (fixed interval, error-triggered)
tools.py              — Tool implementations + single dispatch point (execute_tool)
run_task.py           — 5-step multi-hop demo: file_read → calc → search → calc → Answer
run_evals.py          — W02D2: 20-task eval runner, auto FM classification, outputs JSONL + taxonomy
run_ab_eval.py        — W02D3: A/B runner — naive vs fixed-reflect vs triggered-reflect across 20 tasks
notes.txt             — Sample data file used by evals
eval_results.jsonl    — W02D2 baseline results (20 tasks, naive agent)
ab_results.jsonl      — W02D3 A/B results (60 runs: 3 configs × 20 tasks)
failure_taxonomy.md   — W02D2 failure mode analysis with root causes and fixes
ab_comparison.md      — W02D3 comparison table + write-up
```

---

## Setup

```bash
cd react-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Run

```bash
# 5-step multi-hop demo (W02D1)
python run_task.py

# Custom question
python agent.py "What is the square root of the number of lines in notes.txt?"

# Reflective agent — fixed interval (reflect every 3 steps)
python agent_reflective.py fixed "Read notes.txt and summarize the goal."

# Reflective agent — triggered (reflect only on error or stall)
python agent_reflective.py triggered "Search for FastMCP and explain it."

# W02D2: run 20-task eval set
python run_evals.py

# W02D3: run A/B comparison (naive vs fixed vs triggered) — ~8-10 min
python run_ab_eval.py
```

---

## Results

### W02D1 — Multi-hop demo
5-step task combining `file_read` + `calc` + `search` + `calc`. Agent resolved in 9 steps, self-recovered from 3 consecutive DuckDuckGo failures using context from the file.

### W02D2 — 20-task eval baseline

| Category | Passed | Notes |
|----------|--------|-------|
| single-tool | 5/5 | calc + file_read fully reliable |
| multi-hop | 5/5 | 3-tool chains work; counting is imprecise |
| search | 5/5 | DuckDuckGo flaky, agent self-recovers |
| adversarial | 5/5 | Missing files, nonsense queries, sqrt(-1) all handled |

**Corrected score: 18/20** on original run (2 failures were eval design bugs, 1 was real FM-REASONING).

Top failure mode: **FM-REASONING** — agent miscounts file lines because it has no code execution primitive. Fix: add `run_python()` tool.

### W02D3 — Reflection A/B

| Config | Score | Avg time |
|--------|-------|----------|
| Naive ReAct | 20/20 | 5.2s |
| Fixed Reflect (N=3) | 20/20 | 5.2s |
| Triggered Reflect | 20/20 | 5.0s |

All tied at 20/20 — task set was too easy after fixing eval criteria. Key finding: **triggered reflection is the right production default** (zero overhead on easy tasks, fires only on genuine stalls). Fixed reflection wastes tokens on tasks already resolving correctly.

Qualitative difference found on C1 (FastMCP): naive hallucinated a confident answer, fixed-reflect honestly reported "unable to find." Both passed the binary criterion — pass rate hides quality differences.

---

## Architecture decisions

- **No framework** — the loop is ~60 LOC of plain Python. Readable in 5 minutes.
- **`stop_sequences=["Observation:"]`** — prevents the model from hallucinating its own observations. Critical.
- **Whitelist eval for `calc`** — safe math without `eval()` on arbitrary code.
- **claude-haiku for the loop** — fast and cheap. Swap to sonnet for harder tasks.
- **Triggered > Fixed reflection** — zero overhead when not needed, activates on genuine stalls or errors.
- **JSONL for results** — append-only, grep-able, no DB needed.

---

## Known limitations

- `search` uses DuckDuckGo free API — flaky on niche queries, no rate limit guarantees. Swap to Brave/Serper for production.
- No `run_python()` tool — agent cannot programmatically count or filter file content. Reasoning-only counting is imprecise.
- `file_read` capped at 2000 chars — large files are truncated.
- Reflection adds no measurable value on short, easy tasks. Needs harder task set (5+ steps, genuine dead-ends) to show benefit.
