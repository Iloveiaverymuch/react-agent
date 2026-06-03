"""
W02D2 — 20-task eval runner for the ReAct agent.

Runs all 20 tasks, captures pass/fail/failure-mode for each,
and writes a structured log to eval_results.jsonl + failure_taxonomy.md.

Usage:
    python run_evals.py

Output:
    eval_results.jsonl    — one JSON record per task
    failure_taxonomy.md   — bucketed failure analysis
"""

import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional
from agent import run_react

# ── Task definitions ──────────────────────────────────────────────────────────

TASKS = [

    # ── Category A: Single-tool (should always pass) ─────────────────────────
    {
        "id": "A1", "category": "single-tool",
        "task": "What is 2 to the power of 10?",
        "expected": "1024",
        "pass_if": lambda r: "1024" in r,
    },
    {
        "id": "A2", "category": "single-tool",
        "task": "Calculate the square root of 256.",
        "expected": "16.0",
        "pass_if": lambda r: "16" in r,
    },
    {
        "id": "A3", "category": "single-tool",
        "task": "What is pi multiplied by 2, rounded to 4 decimal places?",
        "expected": "6.2832",
        "pass_if": lambda r: "6.2832" in r,
    },
    {
        "id": "A4", "category": "single-tool",
        "task": "Read the file notes.txt and tell me the value of the 'author' field.",
        "expected": "riadh",
        "pass_if": lambda r: "riadh" in r.lower(),
    },
    {
        "id": "A5", "category": "single-tool",
        "task": "Read notes.txt and tell me what 'stack' is listed.",
        "expected": "python, anthropic, duckduckgo",
        "pass_if": lambda r: "python" in r.lower() and "anthropic" in r.lower(),
    },

    # ── Category B: Multi-hop (chain 2–3 tools) ───────────────────────────────
    {
        "id": "B1", "category": "multi-hop",
        "task": "Read notes.txt, find the number in the 'lines' field, then compute that number squared.",
        "expected": "144 (12^2)",
        "pass_if": lambda r: "144" in r,
    },
    {
        "id": "B2", "category": "multi-hop",
        "task": "Read notes.txt to find the week field, then compute the square root of that week number.",
        "expected": "sqrt(1) = 1.0",
        "pass_if": lambda r: "1.0" in r or r.strip().endswith("1"),
    },
    {
        "id": "B3", "category": "multi-hop",
        "task": "Calculate 15 * 8, then calculate the square root of that result, then round it to 2 decimal places.",
        "expected": "sqrt(120) ≈ 10.95",
        "pass_if": lambda r: "10.95" in r,
    },
    {
        "id": "B4", "category": "multi-hop",
        "task": "Read notes.txt, count how many key-value pairs it contains (lines with a colon), then multiply that count by 3.",
        "expected": "10 pairs * 3 = 30",
        "pass_if": lambda r: "30" in r,
    },
    {
        "id": "B5", "category": "multi-hop",
        "task": "Compute 2^8, then compute 2^4, then tell me the ratio of the first result to the second.",
        "expected": "256 / 16 = 16.0",
        "pass_if": lambda r: "16" in r,
    },

    # ── Category C: Search-dependent (exposes search flakiness) ───────────────
    {
        "id": "C1", "category": "search",
        "task": "Search for what 'FastMCP' is and summarize it in one sentence.",
        "expected": "A Python framework for building MCP servers",
        "pass_if": lambda r: "mcp" in r.lower() or "model context" in r.lower() or "fastmcp" in r.lower(),
    },
    {
        "id": "C2", "category": "search",
        "task": "Search for the capital of France.",
        "expected": "Paris",
        "pass_if": lambda r: "paris" in r.lower(),
    },
    {
        "id": "C3", "category": "search",
        "task": "Search for what 'HotpotQA' is.",
        "expected": "A multi-hop QA benchmark",
        "pass_if": lambda r: "question" in r.lower() or "qa" in r.lower() or "hotpot" in r.lower(),
    },
    {
        "id": "C4", "category": "search",
        "task": "Search for 'Anthropic Claude' and tell me what kind of company Anthropic is.",
        "expected": "AI safety company",
        "pass_if": lambda r: "anthropic" in r.lower() or "ai" in r.lower(),
    },
    {
        "id": "C5", "category": "search",
        "task": "Search for 'chain of thought prompting' and explain what it is.",
        "expected": "Prompting technique where LLM shows reasoning steps",
        "pass_if": lambda r: "reason" in r.lower() or "step" in r.lower() or "chain" in r.lower(),
    },

    # ── Category D: Adversarial (exposes loops, hallucination, premature stop) ─
    {
        "id": "D1", "category": "adversarial",
        "task": "Read the file called secret.txt and tell me its contents.",
        "expected": "File not found error, graceful handling",
        "pass_if": lambda r: "not found" in r.lower() or "error" in r.lower() or "exist" in r.lower(),
    },
    {
        "id": "D2", "category": "adversarial",
        "task": "What is the meaning of life?",
        "expected": "Should answer without tools or with search, not loop",
        "pass_if": lambda r: len(r) > 10 and "max steps" not in r.lower(),
    },
    {
        "id": "D3", "category": "adversarial",
        "task": "Calculate the square root of -1.",
        "expected": "Should report error or explain complex numbers, not crash",
        "pass_if": lambda r: "error" in r.lower() or "complex" in r.lower() or "imaginary" in r.lower() or "cannot" in r.lower(),
    },
    {
        "id": "D4", "category": "adversarial",
        "task": "Search for 'xkzqwmblorf' and tell me what it is.",
        "expected": "Should gracefully report no results found",
        "pass_if": lambda r: "not found" in r.lower() or "no result" in r.lower() or "couldn't find" in r.lower() or "unable" in r.lower(),
    },
    {
        "id": "D5", "category": "adversarial",
        "task": "Read notes.txt, then search for the goal mentioned in it, then calculate how many characters are in that goal string.",
        "expected": "Multi-hop with search in the middle — may fail on search step",
        "pass_if": lambda r: any(c.isdigit() for c in r) and "max steps" not in r.lower(),
    },
]

# ── Failure mode taxonomy ─────────────────────────────────────────────────────

FAILURE_MODES = {
    "FM-LOOP":      "Agent repeated the same Thought+Action without progress",
    "FM-TOOL-ERR":  "Tool returned an error (file not found, calc error, network)",
    "FM-HALLUC":    "Agent made up a tool name or observation",
    "FM-PREMATURE": "Agent gave Answer too early without using needed tools",
    "FM-SEARCH":    "Search returned no result or wrong result, derailed reasoning",
    "FM-MAXSTEP":   "Hit max_steps without reaching an Answer",
    "FM-PARSE":     "Agent output couldn't be parsed as Thought/Action/Answer",
    "FM-NONE":      "No failure — task passed",
}

# ── Runner ────────────────────────────────────────────────────────────────────

def classify_failure(answer: str, passed: bool, error: Optional[str]) -> str:
    if passed:
        return "FM-NONE"
    if error:
        return "FM-TOOL-ERR"
    if "max steps" in answer.lower():
        return "FM-MAXSTEP"
    if "no result" in answer.lower() or "not found" in answer.lower():
        return "FM-SEARCH"
    return "FM-PREMATURE"  # default for wrong answer without obvious other cause


def run_all(max_steps: int = 8, verbose: bool = False):
    results = []
    output_dir = Path(__file__).parent

    print(f"\n{'='*60}")
    print(f"W02D2 — ReAct Agent Eval: {len(TASKS)} tasks")
    print(f"{'='*60}\n")

    for task in TASKS:
        tid  = task["id"]
        cat  = task["category"]
        q    = task["task"]
        print(f"[{tid}] {cat}: {q[:70]}...")

        start   = time.time()
        answer  = ""
        error   = None
        passed  = False

        try:
            answer = run_react(q, max_steps=max_steps, verbose=verbose)
            passed = task["pass_if"](answer)
        except Exception as e:
            error  = str(e)
            answer = f"EXCEPTION: {e}"

        duration  = round(time.time() - start, 1)
        failure   = classify_failure(answer, passed, error)
        status    = "PASS ✓" if passed else f"FAIL ✗ [{failure}]"

        print(f"    → {status} ({duration}s)\n")

        results.append({
            "id":       tid,
            "category": cat,
            "task":     q,
            "expected": task["expected"],
            "answer":   answer[:300],   # cap for readability
            "passed":   passed,
            "failure":  failure,
            "duration": duration,
            "error":    error,
            "ts":       datetime.utcnow().isoformat(),
        })

    # ── Write JSONL ───────────────────────────────────────────────────────────
    jsonl_path = output_dir / "eval_results.jsonl"
    with jsonl_path.open("w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"Results written to {jsonl_path}")

    # ── Write taxonomy doc ────────────────────────────────────────────────────
    write_taxonomy(results, output_dir)

    # ── Print summary ─────────────────────────────────────────────────────────
    passed_count = sum(1 for r in results if r["passed"])
    print(f"\n{'='*60}")
    print(f"Total: {passed_count}/{len(results)} passed")
    print(f"{'='*60}\n")

    by_cat = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r["passed"])
    for cat, vals in by_cat.items():
        p = sum(vals)
        print(f"  {cat:15s}: {p}/{len(vals)}")

    print()
    failures = [r for r in results if not r["passed"]]
    if failures:
        print("Failures:")
        for r in failures:
            print(f"  [{r['id']}] {r['failure']} — {r['task'][:60]}")


def write_taxonomy(results: list, output_dir: Path):
    from collections import Counter, defaultdict

    failures = [r for r in results if not r["passed"]]
    fm_counts = Counter(r["failure"] for r in failures)
    by_fm = defaultdict(list)
    for r in failures:
        by_fm[r["failure"]].append(r)

    passed = sum(1 for r in results if r["passed"])

    lines = [
        "# W02D2 — ReAct Failure Taxonomy",
        f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}  ",
        f"**Agent:** react-agent (claude-haiku, max_steps=8)  ",
        f"**Score:** {passed}/{len(results)} passed\n",
        "---\n",
        "## Pass Rate by Category\n",
        "| Category | Passed | Total | Rate |",
        "|----------|--------|-------|------|",
    ]

    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)
    for cat, items in by_cat.items():
        p = sum(1 for i in items if i["passed"])
        lines.append(f"| {cat} | {p} | {len(items)} | {p/len(items)*100:.0f}% |")

    lines += [
        "\n---\n",
        "## Failure Mode Taxonomy\n",
        "| Code | Definition | Count |",
        "|------|-----------|-------|",
    ]
    for fm, definition in FAILURE_MODES.items():
        if fm == "FM-NONE":
            continue
        count = fm_counts.get(fm, 0)
        lines.append(f"| `{fm}` | {definition} | {count} |")

    lines += ["\n---\n", "## Failures by Mode\n"]
    for fm, items in by_fm.items():
        lines.append(f"### `{fm}` — {FAILURE_MODES.get(fm, fm)}\n")
        for r in items:
            lines.append(f"- **[{r['id']}]** `{r['task'][:80]}`")
            lines.append(f"  - Expected: {r['expected']}")
            lines.append(f"  - Got: {r['answer'][:150]}")
            lines.append(f"  - Error: {r['error'] or 'none'}\n")

    lines += [
        "\n---\n",
        "## Key Observations\n",
        "*(Fill in after reviewing results)*\n",
        "1. \n2. \n3. \n",
        "## Top 3 Fixes\n",
        "1. \n2. \n3. \n",
    ]

    taxonomy_path = output_dir / "failure_taxonomy.md"
    taxonomy_path.write_text("\n".join(lines))
    print(f"Taxonomy written to {taxonomy_path}")


if __name__ == "__main__":
    run_all(max_steps=8, verbose=False)
