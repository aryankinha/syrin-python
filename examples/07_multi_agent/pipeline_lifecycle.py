"""Workflow lifecycle — play(), pause, resume, cancel on a 3-agent chain.

Key concepts shown here:
- wf.play(task)             — start in background, return RunHandle
- await wf.pause()          — request pause after current agent completes
- await wf.resume()         — resume a paused workflow
- await wf.cancel()         — stop the workflow; resume() raises WorkflowCancelledError
- await handle.wait()       — block until done, return Response
- handle.status             — current WorkflowStatus

Run:
    OPENAI_API_KEY=sk-... uv run python examples/07_multi_agent/pipeline_lifecycle.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from syrin import Agent, Budget, Model
from syrin.workflow import Workflow
from syrin.workflow.exceptions import WorkflowCancelledError

if not os.environ.get("OPENAI_API_KEY"):
    sys.exit("OPENAI_API_KEY is required. Set it and re-run.")

_MODEL = Model.OpenAI("gpt-4o-mini")


class ResearchAgent(Agent):
    """Gathers market research on the given topic."""

    model = _MODEL
    system_prompt = (
        "You are a research analyst. Summarise the 3 most important market trends "
        "and key data points for the given topic."
    )


class AnalysisAgent(Agent):
    """Analyses the research findings and extracts strategic insights."""

    model = _MODEL
    system_prompt = (
        "You are a strategic analyst. Given market research, identify the 2 most "
        "important strategic implications and rate the investment opportunity (High/Medium/Low)."
    )


class WriterAgent(Agent):
    """Drafts the final executive report."""

    model = _MODEL
    system_prompt = (
        "You write concise executive reports. Given strategic analysis, produce a "
        "one-paragraph recommendation for the C-suite."
    )


def _make_workflow(budget: Budget | None = None) -> Workflow:
    wf = Workflow("market-research", budget=budget) if budget else Workflow("market-research")
    return wf.step(ResearchAgent).step(AnalysisAgent).step(WriterAgent)


# ── Example 1: play() + wait() ────────────────────────────────────────────────


async def example_play_and_wait() -> None:
    print("\n── Example 1: play() + handle.wait() ────────────────────────────")

    wf = _make_workflow(budget=Budget(max_cost=1.00))
    handle = wf.play("AI market trends")

    print(f"  Status immediately after play(): {handle.status}")

    result = await handle.wait()
    print(f"  Status after wait(): {handle.status}")
    print(f"  Result: {result.content[:120]}...")
    print(f"  Cost:   ${result.cost:.6f}")


# ── Example 2: pause() + resume() ────────────────────────────────────────────


async def example_pause_resume() -> None:
    print("\n── Example 2: pause() + resume() ────────────────────────────────")

    wf = _make_workflow()
    handle = wf.play("Cloud infrastructure investment analysis")

    await asyncio.sleep(0.1)
    await wf.pause()
    print(f"  Requested pause. Status: {handle.status}")

    await asyncio.sleep(0.05)
    print("  (Paused — simulating human review...)")

    await wf.resume()
    print(f"  Resumed. Status: {handle.status}")

    result = await handle.wait()
    print(f"  Final status: {handle.status}")
    print(f"  Result: {result.content[:100]}...")


# ── Example 3: cancel() ───────────────────────────────────────────────────────


async def example_cancel() -> None:
    print("\n── Example 3: cancel() ───────────────────────────────────────────")

    wf = _make_workflow()
    handle = wf.play("AI market trends")

    await asyncio.sleep(0.1)
    await wf.cancel()
    print(f"  Status after cancel(): {handle.status}")

    try:
        await wf.resume()
    except WorkflowCancelledError as exc:
        print(f"  resume() raised WorkflowCancelledError (expected): {exc}")

    try:
        await handle.wait()
    except WorkflowCancelledError:
        print("  handle.wait() raised WorkflowCancelledError (expected)")
    except Exception as exc:
        print(f"  handle.wait() raised {type(exc).__name__}: {exc}")


# ── Example 4: pause() → cancel() ────────────────────────────────────────────


async def example_pause_then_cancel() -> None:
    print("\n── Example 4: pause() then cancel() ─────────────────────────────")

    wf = _make_workflow()
    handle = wf.play("Renewable energy market")

    await asyncio.sleep(0.1)
    await wf.pause()
    print(f"  Paused. Status: {handle.status}")

    await wf.cancel()
    print(f"  Cancelled. Status: {handle.status}")

    try:
        await handle.wait()
    except (WorkflowCancelledError, Exception) as exc:
        print(f"  handle.wait() raised {type(exc).__name__} (expected)")


# ── Example 5: Status polling ──────────────────────────────────────────────────


async def example_status_polling() -> None:
    print("\n── Example 5: Status polling ─────────────────────────────────────")

    wf = _make_workflow()
    handle = wf.play("Healthcare AI technology adoption")

    statuses_seen: list[str] = []
    for _ in range(8):
        current = str(handle.status)
        if not statuses_seen or statuses_seen[-1] != current:
            statuses_seen.append(current)
        await asyncio.sleep(0.05)

    await handle.wait()
    statuses_seen.append(str(handle.status))

    unique: list[str] = []
    for s in statuses_seen:
        if not unique or unique[-1] != s:
            unique.append(s)

    print(f"  Status transitions: {' → '.join(unique)}")


# ── Example 6: Pre-configured workflow with visualize() ───────────────────────


async def example_preconfigured_agents() -> None:
    print("\n── Example 6: Pre-configured workflow + visualize() ─────────────")

    wf = _make_workflow(budget=Budget(max_cost=2.00))

    print("  Workflow graph:")
    wf.visualize()

    handle = wf.play("FinTech disruption landscape 2025")
    result = await handle.wait()
    print(f"\n  Status: {handle.status}")
    print(f"  Cost:   ${result.cost:.6f}")
    print(f"  Result: {result.content[:120]}...")


async def main() -> None:
    await example_play_and_wait()
    await example_pause_resume()
    await example_cancel()
    await example_pause_then_cancel()
    await example_status_polling()
    await example_preconfigured_agents()
    print("\nAll workflow lifecycle examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
