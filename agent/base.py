"""
ReAct Agent — Thought → Action → Observation loop
Raw Python, no framework. ~150 LOC.

---------------------------------------------------------------------------
WHAT IS A ReAct AGENT?
---------------------------------------------------------------------------
A ReAct agent (Reasoning + Acting) solves problems by alternating between:

  1. Thought  — the model reasons about what to do next
  2. Action   — the model calls a tool (e.g. search, read a file, run code)
  3. Observation — the real result of that tool call is fed back to the model

This continues until the model produces a final "Answer:".

The key insight: by forcing the model to show its reasoning (Thought) and
wait for real tool results (Observation), we get far more reliable behaviour
than asking it to answer in one shot.

Reference: Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models"
           https://arxiv.org/abs/2210.03629

Usage (from repo root):
    python -m agent.base "What is the square root of the number of lines in data/notes.txt?"
"""

# ── Imports ───────────────────────────────────────────────────────────────────
# `from __future__ import annotations` enables the newer Python 3.10+ type hint
# syntax (e.g. `str | None`, `tuple[str, str]`) on Python 3.8 and 3.9 as well.
# It must be the very first import.
from __future__ import annotations

import re           # Regular expressions — used to parse the model's output
import os           # Operating system utilities (not directly used here but
                    # kept for potential path operations in tools)
import sys          # Access to command-line arguments (sys.argv)
import anthropic    # Official Anthropic Python SDK — sends messages to Claude

# Import our tool registry and the single dispatch function.
# tools/ package re-exports the current v2 tools (web_search, file_read, run_python).
from tools import TOOLS, execute_tool

# ── System Prompt ─────────────────────────────────────────────────────────────
# The system prompt is the "instruction manual" given to Claude before the
# conversation starts. It tells the model:
#   - what role to play (ReAct agent)
#   - what tools are available and when to use each
#   - what output format to follow (Thought / Action / Answer)
#
# IMPORTANT: The tool descriptions here are written for the *agent*, not a
# human developer. They say "use this for X, NOT for Y" so the model picks
# the right tool without guessing.

SYSTEM_PROMPT = """You are a ReAct agent. You solve problems by interleaving Thought, Action, and Observation steps.

You have access to these tools:
- web_search(query) — search the web for factual information; do NOT use for math or local files
- file_read(file_path) — read a local file; do NOT use for web content or computation
- run_python(code) — execute Python for any math, counting, data processing, or string operations

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

# ── Parser: extract Action ────────────────────────────────────────────────────

def parse_action(text: str) -> tuple[str, str] | None:
    """
    Parse the model's output to extract a tool call.

    The model outputs lines like:
        Action: web_search(What is the capital of France?)
        Action: file_read(notes.txt)
        Action: run_python(2 ** 10)

    This function uses a regex to extract:
        - tool_name  (e.g. "web_search")
        - argument   (e.g. "What is the capital of France?")

    Returns a (tool_name, argument) tuple, or None if no valid Action is found.
    The `re.MULTILINE` flag makes `$` match end-of-line rather than end-of-string,
    so we correctly capture single-line Action entries in a longer response.
    """
    match = re.search(r"Action:\s*(\w+)\((.+?)\)\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None


def parse_answer(text: str) -> str | None:
    """
    Check whether the model has produced a final answer.

    The model signals it is done by outputting:
        Answer: <the answer text here>

    `re.DOTALL` makes `.` match newlines too, so multi-line answers are captured
    in full (not just the first line).

    Returns the answer string, or None if not yet present.
    """
    match = re.search(r"Answer:\s*(.+)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


# ── ReAct Loop ────────────────────────────────────────────────────────────────

def run_react(question: str, max_steps: int = 10, verbose: bool = True) -> str:
    """
    Run the full ReAct loop for a given question.

    How it works:
      1. We start with the user's question as the first message.
      2. We call Claude (Haiku — fast and cheap for looping agents).
         We pass `stop_sequences=["Observation:"]` so the model STOPS generating
         as soon as it would write "Observation:". This prevents the model from
         making up its own tool results.
      3. We parse the model's output:
         - If it contains "Answer:" → we're done, return it.
         - If it contains "Action:" → execute the named tool with the argument.
         - Otherwise → nudge the model to produce a valid Action.
      4. We append the model's output and the real observation to the message
         history, then loop back to step 2.
      5. If we hit max_steps without an Answer, we bail out gracefully.

    Parameters:
        question  — the task or question to solve
        max_steps — safety limit to prevent infinite loops (default: 10)
        verbose   — if True, print each step to the terminal

    Returns:
        The final answer string (or a timeout message).
    """
    # Anthropic client — reads ANTHROPIC_API_KEY from the environment automatically
    client = anthropic.Anthropic()

    # The conversation history. We start with just the user's question.
    # Claude's API uses a list of {"role": ..., "content": ...} dicts.
    messages = [{"role": "user", "content": question}]

    step = 0  # Counter to enforce max_steps

    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print(f"{'='*60}\n")

    while step < max_steps:
        step += 1

        # ── LLM call ──────────────────────────────────────────────────────────
        # We send the full conversation history each time (Claude's API is stateless).
        # `stop_sequences=["Observation:"]` is the critical trick:
        #   - Without it, the model would continue past "Action: ..." and write
        #     "Observation: <invented result>" — hallucinating the tool output.
        #   - With it, the model stops at the word "Observation:" and waits for
        #     the real result to be injected by our code.
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",   # fast + cheap for agent loops
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
            stop_sequences=["Observation:"],      # stop before hallucinating obs
        )

        # The model's response is a list of content blocks. We take the first
        # (and usually only) text block and strip whitespace.
        assistant_text = response.content[0].text.strip()

        if verbose:
            print(f"--- Step {step} ---")
            print(assistant_text)

        # ── Check for final answer ─────────────────────────────────────────────
        # If the model wrote "Answer: ...", we're done — return it immediately.
        answer = parse_answer(assistant_text)
        if answer:
            print(f"\n{'='*60}")
            print(f"Final Answer: {answer}")
            print(f"{'='*60}\n")
            return answer

        # ── Parse and execute the action ──────────────────────────────────────
        # Try to extract the tool call from the model's output.
        parsed = parse_action(assistant_text)
        if not parsed:
            # The model didn't produce a valid "Action: tool(arg)" line.
            # Return an error observation to nudge it back on track.
            observation = "Error: no valid Action found. Use format: Action: tool_name(argument)"
        else:
            tool_name, argument = parsed
            if verbose:
                print(f"\nObservation: [calling {tool_name}({argument!r})]")

            # execute_tool dispatches to the correct function in tools_v2.py
            # and returns a plain string — the "real" observation.
            observation = execute_tool(tool_name, argument)

        if verbose:
            print(f"Observation: {observation}\n")

        # ── Append to conversation history ────────────────────────────────────
        # Claude is stateless — we maintain the full history ourselves.
        # We add two turns:
        #   1. The assistant's Thought + Action
        #   2. The user's "Observation: <result>" (which triggers the next step)
        #
        # Note: we prefix with "Observation:" in the user turn because the model
        # was trained to expect observations in this format. It also matches the
        # stop_sequence we set, completing the Thought→Action→Observation cycle.
        messages.append({"role": "assistant", "content": assistant_text})
        messages.append({"role": "user",      "content": f"Observation: {observation}"})

    # If we exit the loop without an answer, return a safe fallback.
    return "Max steps reached without a final answer."


# ── Entry point ───────────────────────────────────────────────────────────────
# When run directly (`python agent.py "..."`) this block executes.
# When imported as a module (e.g. in run_evals.py), it is skipped.

if __name__ == "__main__":
    # Join all command-line arguments into a single question string.
    # If no arguments are given, use a default demo question.
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "What is the square root of 144, and what does the file data/notes.txt say on its first line?"
    )
    run_react(question)
