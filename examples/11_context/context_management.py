"""Context management — tour of Syrin's context features.

This file runs a short tour: basics, snapshot/breakdown, manual compaction,
thresholds, and a custom ContextManager. For focused "best" examples, run:

  python -m examples.11_context.context_snapshot_demo      # Full snapshot & breakdown
  python -m examples.11_context.context_thresholds_compaction_demo  # Thresholds & compaction

Features covered here:
- Context(max_tokens=, reserve=) for window limits
- agent.context_stats and agent.context.snapshot() after response()
- ContextStats.breakdown (token counts by component; set after prepare)
- Manual compaction: MiddleOutTruncator, ContextCompactor
- ContextThreshold with actions at utilization %
- Custom ContextManager via Protocol
- Events: context.compact, context.threshold, context.snapshot

Run: python -m examples.11_context.context_management
Serve: python -m examples.11_context.context_management --serve  (requires syrin[serve])
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from examples.models.models import almock, gpt4_mini
from syrin import Agent
from syrin.model import Model

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Use real gpt-4o-mini when USE_REAL_MODEL=1 (e.g. USE_REAL_MODEL=1 python -m examples.11_context.context_management)
_model: Model = gpt4_mini if os.environ.get("USE_REAL_MODEL") == "1" else almock
from syrin.context import (
    Context,
    ContextCompactor,
    ContextManager,
    ContextPayload,
    ContextWindowCapacity,
    MiddleOutTruncator,
)
from syrin.context.counter import TokenCounter
from syrin.threshold import ContextThreshold


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def run_tour() -> None:
    # -------------------------------------------------------------------------
    # 1. Context basics — max_tokens, one response, then stats
    # -------------------------------------------------------------------------
    section("1. Context basics (max_tokens, stats after response)")

    agent = Agent(
        model=_model,
        system_prompt="You are a helpful assistant.",
        context=Context(max_tokens=80_000),
    )
    agent.response("What is 2+2? Answer in one sentence.")

    stats = agent.context_stats
    print(f"  Max tokens (window): {agent.context.max_tokens}")
    print(f"  Total tokens used:   {stats.total_tokens}")
    print(f"  Utilization:         {stats.utilization:.2%}")

    # -------------------------------------------------------------------------
    # 2. Snapshot and breakdown — full view of what's in the window
    # -------------------------------------------------------------------------
    section("2. Snapshot & breakdown (what's in the context window)")

    snap = agent.context.snapshot()
    print(f"  Utilization:     {snap.utilization_pct:.1f}%")
    print(f"  Context rot:     {snap.context_rot_risk}")
    print(
        f"  Breakdown:       system={snap.breakdown.system_tokens}, tools={snap.breakdown.tools_tokens}, messages={snap.breakdown.messages_tokens}"
    )
    print(f"  Why included:    {snap.why_included}")

    if stats.breakdown is not None:
        print(
            f"  stats.breakdown: same as snapshot (system={stats.breakdown.system_tokens}, messages={stats.breakdown.messages_tokens})"
        )

    print("\n  → Run context_snapshot_demo.py for a full snapshot report.")

    # -------------------------------------------------------------------------
    # 3. Manual compaction (MiddleOutTruncator, ContextCompactor)
    # -------------------------------------------------------------------------
    section("3. Manual compaction (MiddleOutTruncator, ContextCompactor)")

    counter = TokenCounter()
    messages: list[dict[str, str]] = [{"role": "system", "content": "You are helpful."}]
    for i in range(15):
        messages.append({"role": "user", "content": f"Message {i}: Tell me about topic {i}."})
        messages.append({"role": "assistant", "content": f"Response about topic {i}. " * 30})

    before = counter.count_messages(messages).total
    truncator = MiddleOutTruncator()
    result = truncator.compact(messages, 2000, counter)
    after = counter.count_messages(result.messages).total
    print(f"  MiddleOutTruncator: {before} → {after} tokens (budget 2000)")

    messages2 = [{"role": "system", "content": "You are helpful."}]
    for i in range(8):
        messages2.append({"role": "user", "content": f"User {i} " + "x" * 80})
        messages2.append({"role": "assistant", "content": f"Response {i} " + "y" * 80})
    before2 = counter.count_messages(messages2).total
    compact_result = ContextCompactor().compact(messages2, 3000)
    after2 = counter.count_messages(compact_result.messages).total
    print(f"  ContextCompactor:   {before2} → {after2} tokens (budget 3000)")

    # -------------------------------------------------------------------------
    # 4. Thresholds — run actions at utilization %
    # -------------------------------------------------------------------------
    section("4. Thresholds (actions at 50%, 70%, 100% utilization)")

    fired: list[int] = []
    agent2 = Agent(
        model=_model,
        system_prompt="You are helpful.",
        context=Context(
            max_tokens=5000,
            thresholds=[
                ContextThreshold(at=50, action=lambda _: fired.append(50)),
                ContextThreshold(at=70, action=lambda _: fired.append(70)),
                ContextThreshold(at=100, action=lambda _: fired.append(100)),
            ],
        ),
    )
    agent2.response("Hello!")
    print(
        f"  Thresholds configured at 50%, 70%, 100%. Fired this run: {fired or 'none (utilization below 50%)'}"
    )

    # -------------------------------------------------------------------------
    # 5. Custom ContextManager (Protocol)
    # -------------------------------------------------------------------------
    section("5. Custom ContextManager (Protocol)")

    class PassThroughContextManager(ContextManager):
        def prepare(
            self,
            messages: list[dict[str, Any]],
            system_prompt: str,
            tools: list[dict[str, Any]],
            memory_context: str,
            capacity: ContextWindowCapacity,
            context: Context | None = None,
        ) -> ContextPayload:
            tok = TokenCounter()
            n = tok.count_messages(messages).total
            if system_prompt:
                n += tok.count(system_prompt) + tok._role_overhead("system")
            n += tok.count_tools(tools)
            return ContextPayload(
                messages=messages,
                system_prompt=system_prompt,
                tools=tools,
                tokens=n,
            )

        def on_compact(self, _event: Any) -> None:
            pass

    agent3 = Agent(model=_model, context=PassThroughContextManager())
    agent3.response("Hi, custom manager!")
    print(
        "  Pass-through manager used; no compaction. Stats:",
        agent3.context_stats.total_tokens,
        "tokens",
    )

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    section("Summary")
    print("  • Context(max_tokens=, reserve=, thresholds=) controls the window.")
    print("  • After response(): agent.context_stats and agent.context.snapshot().")
    print("  • stats.breakdown and snapshot.breakdown: tokens by system/tools/memory/messages.")
    print("  • ContextThreshold(at=N, action=...) and evt.compact() for compaction.")
    print("  • Best examples: context_snapshot_demo.py, context_thresholds_compaction_demo.py")
    print()


def main() -> None:
    if "--serve" in sys.argv:
        from syrin import Agent, Context

        class ContextDemoAgent(Agent):
            _agent_name = "context-demo"
            _agent_description = "Agent with context management"
            model = _model
            system_prompt = "You are a helpful assistant."
            context = Context(max_tokens=1000)

        agent = ContextDemoAgent()
        print("Serving at http://localhost:8000/playground")
        agent.serve(port=8000, enable_playground=True, debug=True)
    else:
        run_tour()


if __name__ == "__main__":
    main()
