"""
ReAct Agent — Thought → Action → Observation loop
Raw Python, no framework. ~150 LOC.

Reference: Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models"
           https://arxiv.org/abs/2210.03629

Usage:
    python agent.py "What is the square root of the number of lines in notes.txt?"
"""

import re
import os
import sys
import anthropic
from tools import TOOLS, execute_tool

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a ReAct agent. You solve problems by interleaving Thought, Action, and Observation steps.

You have access to these tools:
- search(query) — search for information on a topic
- calc(expression) — evaluate a math expression (e.g. "sqrt(144)", "2 ** 10")
- file_read(path) — read the contents of a local file

Always follow this exact format for each step:

Thought: <your reasoning about what to do next>
Action: <tool_name>(<argument>)

After each Action, you will receive an Observation. Use it to continue reasoning.

When you have the final answer, output:
Thought: I now have the final answer.
Answer: <your final answer>

Do not skip steps. Do not call multiple tools in one Action.
Do not make up observations — wait for real ones.
"""

# ── Parser ────────────────────────────────────────────────────────────────────

def parse_action(text: str) -> tuple[str, str] | None:
    """Extract (tool_name, argument) from 'Action: tool_name(argument)' line."""
    match = re.search(r"Action:\s*(\w+)\((.+?)\)\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None

def parse_answer(text: str) -> str | None:
    """Extract final answer if present."""
    match = re.search(r"Answer:\s*(.+)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

# ── ReAct Loop ────────────────────────────────────────────────────────────────

def run_react(question: str, max_steps: int = 10, verbose: bool = True) -> str:
    """
    Run the ReAct loop until the agent produces an Answer or hits max_steps.

    Returns the final answer string.
    """
    client = anthropic.Anthropic()

    messages = [{"role": "user", "content": question}]
    step = 0

    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print(f"{'='*60}\n")

    while step < max_steps:
        step += 1

        # ── LLM call ──────────────────────────────────────────────────────────
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",   # fast + cheap for agent loops
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
            stop_sequences=["Observation:"],      # stop before hallucinating obs
        )

        assistant_text = response.content[0].text.strip()

        if verbose:
            print(f"--- Step {step} ---")
            print(assistant_text)

        # ── Check for final answer ─────────────────────────────────────────────
        answer = parse_answer(assistant_text)
        if answer:
            print(f"\n{'='*60}")
            print(f"Final Answer: {answer}")
            print(f"{'='*60}\n")
            return answer

        # ── Parse action ──────────────────────────────────────────────────────
        parsed = parse_action(assistant_text)
        if not parsed:
            # Model didn't produce a valid action — nudge it
            observation = "Error: no valid Action found. Use format: Action: tool_name(argument)"
        else:
            tool_name, argument = parsed
            if verbose:
                print(f"\nObservation: [calling {tool_name}({argument!r})]")

            observation = execute_tool(tool_name, argument)

        if verbose:
            print(f"Observation: {observation}\n")

        # ── Append to message history ─────────────────────────────────────────
        # Combine assistant turn + observation into the conversation
        messages.append({"role": "assistant", "content": assistant_text})
        messages.append({"role": "user",      "content": f"Observation: {observation}"})

    return "Max steps reached without a final answer."


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "What is the square root of 144, and what does the file notes.txt say on its first line?"
    )
    run_react(question)
