"""Pry — syrin's interactive agent debugger (like byebug for AI agents).

Demonstrates:
- Basic attach / detach lifecycle
- pry.debugpoint("label") to hard-pause and inspect state
- filter_mode to scope events: "all" | "errors" | "tools" | "memory"
- pause() / resume() to temporarily suppress events
- Chaining pry.attach(agent1).attach(agent2) for multi-agent monitoring
- JSON fallback in non-TTY environments (CI, piped output)

Run:
    python examples/10_observability/debug_ui.py          # plain stdout (json)
    python examples/10_observability/debug_ui.py --debug  # interactive TUI
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running directly: python examples/10_observability/debug_ui.py
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from examples.models.models import gpt4_mini  # noqa: E402
from syrin import Agent, Budget, tool  # noqa: E402
from syrin.debug import Pry  # noqa: E402

_PRY = Pry.from_debug_flag()

# ---------------------------------------------------------------------------
# Sample tools so we get tool-call events in the UI
# ---------------------------------------------------------------------------


@tool
def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


@tool
def reverse(text: str) -> str:
    """Reverse a string."""
    return text[::-1]


# ---------------------------------------------------------------------------
# 1. Basic usage — attach and run (real model, interactive TUI)
# ---------------------------------------------------------------------------


def demo_basic(debug: bool = False) -> None:
    print("\n=== 1. Basic Pry ===")

    agent = Agent(
        model=gpt4_mini,
        system_prompt="You are a helpful assistant.",
        tools=[word_count, reverse],
        budget=Budget(max_cost=0.10),
    )

    if debug:
        # pry.run() keeps TUI key loop responsive during agent execution.
        # ↑/↓ navigate stream, Tab/Shift+Tab switch right panel, ↵ detail, q quit.
        pry = _PRY or Pry()
        with pry:
            pry.attach(agent)
            pry.run(agent.run, "Count the words in: 'The quick brown fox'").join()
            pry.run(agent.run, "Reverse the string: 'hello world'").join()
            pry.wait()
    else:
        agent.run("Count the words in: 'The quick brown fox'")
        agent.run("Reverse the string: 'hello world'")


# ---------------------------------------------------------------------------
# 2. Filter mode — only show tool events
# ---------------------------------------------------------------------------


def demo_filter_tools() -> None:
    print("\n=== 2. filter_mode='tools' — only tool events ===")

    agent = Agent(
        model=gpt4_mini,
        system_prompt="You are a helpful assistant.",
        tools=[word_count],
    )

    pry = Pry(filter_mode="tools")
    pry.attach(agent)

    agent.run("How many words in 'syrin is great'?")

    pry.detach()


# ---------------------------------------------------------------------------
# 3. Filter mode — only show errors
# ---------------------------------------------------------------------------


def demo_filter_errors() -> None:
    print("\n=== 3. filter_mode='errors' — only error events ===")

    agent = Agent(
        model=gpt4_mini,
        system_prompt="You are a helpful assistant.",
        tools=[word_count],
    )

    pry = Pry(filter_mode="errors")
    pry.attach(agent)

    agent.run("What is 2 + 2?")  # No errors expected — UI stays silent

    pry.detach()


# ---------------------------------------------------------------------------
# 4. pause() / resume()
# ---------------------------------------------------------------------------


def demo_pause_resume() -> None:
    print("\n=== 4. pause() / resume() ===")

    agent = Agent(
        model=gpt4_mini,
        system_prompt="You are a helpful assistant.",
    )

    pry = Pry()
    pry.attach(agent)

    agent.run("First run — UI active")

    pry.pause()
    agent.run("Second run — UI paused, no events emitted")
    pry.resume()

    agent.run("Third run — UI active again")

    pry.detach()


# ---------------------------------------------------------------------------
# 5. Multi-agent — chain attach() calls
# ---------------------------------------------------------------------------


def demo_multi_agent() -> None:
    print("\n=== 5. Multi-agent monitoring ===")

    researcher = Agent(
        model=gpt4_mini,
        system_prompt="You research topics.",
    )
    writer = Agent(
        model=gpt4_mini,
        system_prompt="You write summaries.",
    )

    # Single UI watches both agents
    pry = Pry()
    pry.attach(researcher).attach(writer)

    researcher.run("Research: Python async patterns")
    writer.run("Summarize: Python async patterns")

    pry.detach()


# ---------------------------------------------------------------------------
# 6. JSON fallback — force structured output (useful for CI / log ingestion)
# ---------------------------------------------------------------------------


def demo_json_fallback() -> None:
    print("\n=== 6. JSON fallback (json_fallback=True) ===")

    agent = Agent(
        model=gpt4_mini,
        system_prompt="You are a helpful assistant.",
        tools=[word_count],
    )

    captured: list[str] = []
    pry = Pry(json_fallback=True, stream_override=captured)
    pry.attach(agent)

    agent.run("Count words: 'one two three'")

    pry.detach()

    print(f"Captured {len(captured)} JSON event(s):")
    for line in captured:
        print(f"  {line}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _debug = _PRY is not None
    demo_basic(debug=_debug)
    # demo_filter_tools()
    # demo_filter_errors()
    # demo_pause_resume()
    # demo_multi_agent()
    # demo_json_fallback()
