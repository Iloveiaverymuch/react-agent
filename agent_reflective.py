"""
ReAct Agent with Reflection — two modes:

  Mode A: FIXED — reflect every N steps (default N=3)
  Mode B: TRIGGERED — reflect only on tool error or stall (same action repeated)

Usage:
    from agent_reflective import run_react_reflective

    # Fixed interval
    run_react_reflective(question, reflect_mode="fixed", reflect_every=3)

    # Error/stall triggered
    run_react_reflective(question, reflect_mode="triggered")

Reference: Yao et al. ReAct (2023) + Shinn et al. Reflexion (2023)
"""

from __future__ import annotations

import re
import sys
import anthropic
from tools import execute_tool

# ── Prompts ───────────────────────────────────────────────────────────────────

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

REFLECT_PROMPT = """Before continuing, pause and reflect on your trajectory so far.

Review what you have done:
- What was the original question?
- What tools have you called and what did they return?
- Are you making real progress toward the answer, or repeating yourself?
- Have you hit any errors? What caused them?
- Is your current approach the best one, or should you try something different?

After reflecting, decide:
- If you are on track: continue with the next Thought + Action.
- If you are stuck or repeating: change strategy. Try a different tool, a different argument, or reason from what you already know.
- If you already have enough information: produce the Answer now.

Output your reflection as:
Reflect: <your self-critique and revised plan>

Then immediately continue with:
Thought: <next step>
Action: <tool_name>(<argument>)

OR if you have the answer:
Thought: I now have the final answer.
Answer: <your final answer>
"""

# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_action(text: str) -> tuple[str, str] | None:
    match = re.search(r"Action:\s*(\w+)\((.+?)\)\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None

def parse_answer(text: str) -> str | None:
    match = re.search(r"Answer:\s*(.+)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def parse_reflect_and_continue(text: str) -> tuple[str | None, str | None, tuple | None]:
    """Extract (reflect_text, answer, action) from a reflection response."""
    reflect = None
    rm = re.search(r"Reflect:\s*(.+?)(?=Thought:|$)", text, re.DOTALL)
    if rm:
        reflect = rm.group(1).strip()

    answer = parse_answer(text)
    action = parse_action(text)
    return reflect, answer, action

# ── Stall detection ───────────────────────────────────────────────────────────

def is_stalled(history: list[tuple[str, str]], window: int = 2) -> bool:
    """
    Detect if the agent is repeating the same Action in the last `window` steps.
    history = list of (tool_name, argument) tuples.
    """
    if len(history) < window:
        return False
    recent = history[-window:]
    return len(set(recent)) == 1  # all identical

# ── Core loop ─────────────────────────────────────────────────────────────────

def run_react_reflective(
    question: str,
    reflect_mode: str = "fixed",   # "fixed" or "triggered"
    reflect_every: int = 3,         # only used in fixed mode
    max_steps: int = 10,
    verbose: bool = True,
) -> str:
    """
    ReAct loop with optional reflection.

    reflect_mode="fixed":     inject reflection every `reflect_every` steps
    reflect_mode="triggered": inject reflection only on tool error or stall
    """
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]
    step = 0
    action_history: list[tuple[str, str]] = []  # for stall detection
    reflect_count = 0

    if verbose:
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        print(f"Mode: reflect_{reflect_mode}" + (f" (N={reflect_every})" if reflect_mode == "fixed" else ""))
        print(f"{'='*60}\n")

    while step < max_steps:
        step += 1

        # ── Decide whether to inject reflection ───────────────────────────────
        should_reflect = False

        if reflect_mode == "fixed":
            should_reflect = (step > 1) and ((step - 1) % reflect_every == 0)

        elif reflect_mode == "triggered":
            # Triggered on: last observation was an error, OR agent is stalling
            last_user = messages[-1]["content"] if messages else ""
            tool_errored = (
                "error" in last_user.lower() or
                "not found" in last_user.lower() or
                "no result" in last_user.lower()
            ) and last_user.startswith("Observation:")
            stalled = is_stalled(action_history, window=2)
            should_reflect = tool_errored or stalled

        # ── Inject reflection ─────────────────────────────────────────────────
        if should_reflect:
            reflect_count += 1
            if verbose:
                print(f"--- [REFLECT #{reflect_count}] ---")

            messages.append({"role": "user", "content": REFLECT_PROMPT})

            reflect_response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=messages,
                stop_sequences=["Observation:"],
            )
            reflect_text = reflect_response.content[0].text.strip()

            if verbose:
                print(reflect_text)

            reflect_note, answer, action = parse_reflect_and_continue(reflect_text)

            messages.append({"role": "assistant", "content": reflect_text})

            if answer:
                if verbose:
                    print(f"\n{'='*60}\nFinal Answer (post-reflect): {answer}\n{'='*60}\n")
                return answer

            if action:
                tool_name, argument = action
                observation = execute_tool(tool_name, argument)
                action_history.append((tool_name, argument))
                if verbose:
                    print(f"Observation: {observation}\n")
                messages.append({"role": "user", "content": f"Observation: {observation}"})
                continue

            # Reflect produced no action — fall through to normal step
            messages.append({"role": "user", "content": "Continue."})

        # ── Normal ReAct step ─────────────────────────────────────────────────
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
            stop_sequences=["Observation:"],
        )
        assistant_text = response.content[0].text.strip()

        if verbose:
            print(f"--- Step {step} ---")
            print(assistant_text)

        answer = parse_answer(assistant_text)
        if answer:
            if verbose:
                print(f"\n{'='*60}\nFinal Answer: {answer}\n{'='*60}\n")
            return answer

        parsed = parse_action(assistant_text)
        if not parsed:
            observation = "Error: no valid Action found. Use format: Action: tool_name(argument)"
        else:
            tool_name, argument = parsed
            action_history.append((tool_name, argument))
            observation = execute_tool(tool_name, argument)

        if verbose:
            print(f"Observation: {observation}\n")

        messages.append({"role": "assistant", "content": assistant_text})
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    return "Max steps reached without a final answer."


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "fixed"
    question = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else (
        "Read notes.txt, count how many key-value pairs it contains (lines with a colon), then multiply that count by 3."
    )
    run_react_reflective(question, reflect_mode=mode, verbose=True)
