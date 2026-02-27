"""CLI REPL — interactive terminal serving."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from syrin.agent import Agent
    from syrin.serve.config import ServeConfig


def run_cli_repl(agent: Agent, config: ServeConfig) -> None:
    """Run interactive CLI REPL. Blocks until Ctrl+C.

    Prompts for input, runs agent, prints response and cost/budget per turn.
    """
    state = agent.budget_state
    budget_str = ""
    if state is not None and state.limit is not None:
        rem = state.remaining
        lim = state.limit
        rem_str = f"${rem:.2f}" if rem is not None else "—"
        lim_str = f"${lim:.2f}" if lim is not None else "—"
        budget_str = f"\nBudget: {rem_str} / {lim_str} remaining\n"

    print(f"[Syrin] {agent.name} agent ready. Type your message. Ctrl+C to exit.{budget_str}")

    while True:
        try:
            line = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break
        if not line:
            continue
        try:
            r = agent.response(line)
            print(str(r.content))
            cost_str = f"${r.cost:.4f}".rstrip("0").rstrip(".")
            if cost_str == "$":
                cost_str = "$0"
            tokens = r.tokens.total_tokens if r.tokens else 0
            parts = [f"Cost: {cost_str}", f"Tokens: {tokens}"]
            if r.budget_remaining is not None:
                parts.append(f"Budget remaining: ${r.budget_remaining:.2f}")
            print(" | ".join(parts))
        except KeyboardInterrupt:
            print("\nInterrupted.")
        except Exception as e:
            print(f"Error: {e}")
