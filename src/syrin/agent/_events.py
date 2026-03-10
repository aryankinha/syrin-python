"""Event emission use case: print_event for debug output.

Agent._emit_event stays in Agent (orchestrates events, domain events, media cost).
This module holds the debug-print formatting logic.
"""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any, cast

from syrin.events import EventContext


def print_event(agent: Any, event: str, ctx: EventContext) -> None:
    """Print event to console when debug=True. Used by Agent._emit_event."""
    is_tty = sys.stdout.isatty()

    RESET = "\033[0m" if is_tty else ""
    GREEN = "\033[92m" if is_tty else ""
    BLUE = "\033[94m" if is_tty else ""
    YELLOW = "\033[93m" if is_tty else ""
    CYAN = "\033[96m" if is_tty else ""
    RED = "\033[91m" if is_tty else ""

    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    event_str = str(event)
    if "start" in event_str or "init" in event_str:
        color = GREEN
        symbol = "▶"
    elif "end" in event_str or "complete" in event_str:
        color = BLUE
        symbol = "✓"
    elif "tool" in event_str:
        color = YELLOW
        symbol = "🔧"
    elif "llm" in event_str or "request" in event_str:
        color = CYAN
        symbol = "💬"
    elif "error" in event_str:
        color = RED
        symbol = "✗"
    else:
        color = ""
        symbol = "•"

    print(f"{color}{symbol} {timestamp} {event}{RESET}")

    indent = "     "
    if "input" in ctx:
        task = ctx["input"]
        if isinstance(task, str) and len(task) > 60:
            task = task[:57] + "..."
        print(f"{indent}Input: {task}")
    if "model" in ctx:
        print(f"{indent}Model: {ctx['model']}")
    if "cost" in ctx and ctx["cost"] is not None:
        cost_val = float(cast(float | int, ctx["cost"]))
        if cost_val > 0:
            print(f"{indent}Cost: ${cost_val:.6f}")
    if "tokens" in ctx and ctx["tokens"] is not None:
        print(f"{indent}Tokens: {ctx['tokens']}")
    if "iteration" in ctx:
        print(f"{indent}Iteration: {ctx['iteration']}")
    if "name" in ctx:
        print(f"{indent}Tool: {ctx['name']}")
    if "error" in ctx:
        print(f"{indent}{RED}Error: {ctx['error']}{RESET}")
    if "duration" in ctx and ctx["duration"] is not None:
        duration_ms = float(cast(float | int, ctx["duration"])) * 1000
        print(f"{indent}Duration: {duration_ms:.2f}ms")

    print()
