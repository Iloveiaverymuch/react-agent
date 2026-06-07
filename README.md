# react-agent

ReAct (Reasoning + Acting) agent built from scratch in raw Python — no LangChain, no framework.

Part of a 22-week AI engineering sprint. This repo covers **W02D1–D4**: implement ReAct, stress-test it with 20 structured evals, compare naive vs reflective variants, and refactor tools applying Anthropic's tool design principles.

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

## Tools (v2 — current)

| Tool | What it does |
|------|-------------|
| `web_search(query)` | DuckDuckGo Instant Answer API. Agent-facing description tells it when NOT to use search (math, local files). Returns 3 recovery strategies on failure. |
| `file_read(file_path, max_chars)` | Read a local file. Returns content + metadata (line count, total chars, truncation notice with exact `max_chars` to request more). |
| `run_python(code)` | Execute Python — math, counting, string ops, data processing. Auto-detects expression vs statement mode. Replaces the old `calc` tool. |

See `docs/tool_design_delta.md` for the full W02D4 before/after refactor (5 Anthropic principles applied).

---

## Structure

```
react-agent/
├── agent/                    # Agent loop implementations (Python package)
│   ├── __init__.py           # Re-exports run_react + run_react_reflective
│   ├── base.py               # Naive ReAct loop: Thought → Action → Observation
│   └── reflective.py         # ReAct + reflection (fixed interval or error-triggered)
│
├── tools/                    # Tool implementations (Python package)
│   ├── __init__.py           # Re-exports current TOOLS + execute_tool (from v2)
│   ├── v1.py                 # Legacy tools: calc, file_read, search (kept for reference)
│   └── v2.py                 # Current tools: web_search, file_read, run_python (W02D4)
│
├── evals/                    # Eval runners + results
│   ├── run_evals.py          # W02D2: 20-task baseline → eval_results.jsonl + failure_taxonomy.md
│   ├── run_ab_eval.py        # W02D3: A/B runner (3 configs × 20 tasks) → ab_results.jsonl + ab_comparison.md
│   ├── eval_results.jsonl    # W02D2 baseline results (20 tasks, naive agent)
│   ├── ab_results.jsonl      # W02D3 A/B results (60 runs)
│   ├── failure_taxonomy.md   # W02D2 failure mode analysis with root causes
│   └── ab_comparison.md      # W02D3 side-by-side comparison + verdict
│
├── docs/                     # Design notes and analysis
│   └── tool_design_delta.md  # W02D4 before/after tool refactor (5 Anthropic principles)
│
├── data/                     # Sample data files
│   └── notes.txt             # Key-value project metadata, used by eval tasks
│
├── run_task.py               # Entry point: 5-step multi-hop demo (W02D1)
├── requirements.txt
└── README.md
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

# Custom question (naive agent)
python -m agent.base "What is the square root of the number of lines in data/notes.txt?"

# Reflective agent — fixed interval (reflect every 3 steps)
python -m agent.reflective fixed "Read data/notes.txt and summarize the goal."

# Reflective agent — triggered (reflect only on error or stall)
python -m agent.reflective triggered "Search for FastMCP and explain it."

# Run the 20-task baseline evaluation (can be run from the root or inside evals/)
python evals/run_evals.py

# Run the A/B comparison (Naive vs Fixed vs Triggered reflection)
python evals/run_ab_eval.py
```

---

## Results

### W02D1 — Multi-hop demo
5-step task combining `file_read` + `web_search` + `run_python`. Agent resolved in 9 steps, self-recovered from 3 consecutive DuckDuckGo failures using context from the file.

### W02D2 — 20-task eval baseline

| Category | Passed | Notes |
|----------|--------|-------|
| single-tool | 5/5 | file_read + run_python fully reliable |
| multi-hop | 5/5 | 3-tool chains work; counting is imprecise without run_python |
| search | 5/5 | DuckDuckGo flaky, agent self-recovers |
| adversarial | 5/5 | Missing files, nonsense queries, sqrt(-1) all handled |

**Corrected score: 18/20** on original run (2 failures were eval design bugs, 1 was real FM-REASONING).

Top failure mode: **FM-REASONING** — agent miscounted file lines without a code execution primitive. Fixed by adding `run_python()` in W02D4.

### W02D3 — Reflection A/B

| Config | Score | Avg time |
|--------|-------|----------|
| Naive ReAct | 20/20 | 5.2s |
| Fixed Reflect (N=3) | 20/20 | 5.2s |
| Triggered Reflect | 20/20 | 5.0s |

All tied at 20/20 — task set was too easy after fixing eval criteria. Key finding: **triggered reflection is the right production default** (zero overhead on easy tasks, fires only on genuine stalls). Fixed reflection wastes tokens on tasks already resolving correctly.

Qualitative difference on C1 (FastMCP): naive hallucinated a confident answer, fixed-reflect honestly reported "unable to find." Both passed binary criterion — pass rate hides quality differences.

### W02D4 — Tool design refactor

| Change | Impact |
|--------|--------|
| Removed `calc` (redundant with `run_python`) | Eliminates tool-choice ambiguity |
| `search` → `web_search` | Unambiguous name, explicit DO NOT USE for math/files |
| Agent-facing docstrings (when to use, when NOT to use, what to do on failure) | Reduces hallucinated tool calls |
| `file_read` now returns metadata + truncation notice | Agent can decide to request more without blind retry |
| Errors now actionable (list directory on file-not-found, 3 recovery strategies on search failure) | Agent self-corrects without wasting steps |

---

## Architecture decisions

- **No framework** — the loop is ~60 LOC of plain Python. Readable in 5 minutes.
- **`stop_sequences=["Observation:"]`** — prevents the model from hallucinating its own observations. Critical.
- **Package layout** — `agent/`, `tools/`, `evals/` are proper Python packages with `__init__.py`. Run with `python -m` from repo root.
- **claude-haiku for the loop** — fast and cheap. Swap to sonnet for harder tasks.
- **Triggered > Fixed reflection** — zero overhead when not needed, activates on genuine stalls or errors.
- **JSONL for results** — append-only, grep-able, no DB needed.

---

## Known limitations

- `web_search` uses DuckDuckGo free API — flaky on niche queries, no rate limit guarantees. Swap to Brave/Serper for production.
- `file_read` default cap at 3000 chars — increase with `max_chars` parameter for large files.
- Reflection adds no measurable value on short, easy tasks. Needs harder task set (5+ steps, genuine dead-ends) to show benefit.
- Binary `pass_if` criterion hides answer quality differences — qualitative review still needed.
