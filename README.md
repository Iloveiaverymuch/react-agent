# react-agent

ReAct (Reasoning + Acting) agent implemented from scratch in raw Python — no LangChain, no framework.

**Reference:** [Yao et al., ICLR 2023](https://arxiv.org/abs/2210.03629)

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
Observation: <tool result>
  │
  ▼
Thought: what does this tell me?
Action: ...
  │
  ▼
Answer: <final answer>
```

## Tools

| Tool | What it does |
|------|-------------|
| `calc(expr)` | Evaluate math expressions (`sqrt`, `**`, `pi`, etc.) |
| `file_read(path)` | Read a local file (first 2000 chars) |
| `search(query)` | DuckDuckGo Instant Answer API (no key needed) |

## Setup

```bash
cd react-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=your_key_here
```

## Run

```bash
# Default multi-hop task
python run_task.py

# Custom question
python agent.py "What is the square root of 144?"
```

## Architecture

```
agent.py     — ReAct loop: LLM call, parse Thought/Action, feed Observation
tools.py     — Tool implementations + dispatch (execute_tool)
run_task.py  — 5-step multi-hop QA demo task
notes.txt    — Sample file for file_read tool
```

## Key design decisions

- **No framework** — the loop is ~60 LOC of plain Python. You can read it in 5 minutes.
- **`stop_sequences=["Observation:"]`** — prevents the model from hallucinating its own observations.
- **Whitelist eval** for `calc` — safe math without `eval()` on arbitrary code.
- **claude-haiku** for the loop — fast and cheap. Swap to sonnet for harder tasks.
