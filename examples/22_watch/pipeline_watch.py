"""Pipeline Watch — Trigger a Pipeline via cron, webhook, or queue.

Demonstrates:
- pipeline.watch(protocol=CronProtocol(...)) — Pipeline reacts to schedules
- Pipeline and DynamicPipeline both inherit Watchable
- watch_handler() routes each trigger through all agents sequentially
- on_trigger / on_result / on_error callbacks on the pipeline level

Run:
    python examples/22_watch/pipeline_watch.py

The pipeline fires once immediately (run_on_start=True) via CronProtocol.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from examples.models.models import almock  # noqa: E402
from syrin import Agent  # noqa: E402
from syrin.agent.multi_agent import Pipeline  # noqa: E402
from syrin.watch import CronProtocol, TriggerEvent  # noqa: E402

# ---------------------------------------------------------------------------
# Agents used in the pipeline
# ---------------------------------------------------------------------------


class ResearchAgent(Agent):
    _agent_name = "researcher"
    model = almock
    system_prompt = "You research topics and return key findings in 1-2 sentences."


class SummaryAgent(Agent):
    _agent_name = "summarizer"
    model = almock
    system_prompt = "You condense research into a 1-sentence executive brief."


# ---------------------------------------------------------------------------
# Demo: Pipeline with CronProtocol
# ---------------------------------------------------------------------------


async def demo_pipeline_cron() -> None:
    print("=" * 60)
    print("Pipeline.watch() with CronProtocol")
    print("=" * 60)

    # Pre-configure agents — required for pipeline.watch()/trigger()
    pipeline = Pipeline(agents=[ResearchAgent, SummaryAgent])

    run_count = 0
    stop_event = asyncio.Event()

    def on_trigger(event: TriggerEvent) -> None:
        print(f"  → pipeline trigger: {event.input!r}")

    def on_result(event: TriggerEvent, result: object) -> None:
        nonlocal run_count
        run_count += 1
        content = getattr(result, "content", str(result))
        cost = getattr(result, "cost", 0.0)
        print(f"  [{run_count}] result (${cost:.4f}): {content[:120]}")
        stop_event.set()  # Stop after first successful result

    def on_error(event: TriggerEvent, exc: Exception) -> None:
        print(f"  ✗ error: {exc}")
        stop_event.set()

    # CronProtocol: run_on_start=True fires once immediately without waiting
    protocol = CronProtocol(
        schedule="* * * * *",
        input="Summarize the latest AI developments",
        timezone="UTC",
        run_on_start=True,
    )

    # pipeline.watch() — works because Pipeline inherits Watchable
    pipeline.watch(
        protocol=protocol,
        on_trigger=on_trigger,
        on_result=on_result,
        on_error=on_error,
    )

    handler = pipeline.watch_handler(
        concurrency=1,
        timeout=30.0,
        on_result=on_result,
        on_error=on_error,
    )

    proto_task = asyncio.create_task(protocol.start(handler))
    await stop_event.wait()
    await protocol.stop()
    proto_task.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await proto_task

    print(f"\n  Pipeline processed {run_count} run(s)\n")


# ---------------------------------------------------------------------------
# Usage note: DynamicPipeline.watch()
# ---------------------------------------------------------------------------


def demo_dynamic_pipeline_note() -> None:
    print("=" * 60)
    print("DynamicPipeline.watch() (usage pattern)")
    print("=" * 60)
    print("""
DynamicPipeline also inherits Watchable:

    from syrin.agent.multi_agent import DynamicPipeline
    from syrin.watch import WebhookProtocol

    pipeline = DynamicPipeline(
        agents=[ResearchAgent, AnalystAgent, WriterAgent],
        model=Model.OpenAI("gpt-4o-mini", api_key="..."),
    )

    protocol = WebhookProtocol(
        path="/pipeline/trigger",
        port=9090,
        input_field="task",
        secret="my-hmac-secret",   # HMAC validation — rejects tampered POSTs
    )

    pipeline.watch(
        protocol=protocol,
        concurrency=3,
        timeout=120.0,
        on_trigger=lambda e: print(f"Triggered: {e.input[:60]}"),
        on_result=lambda e, r: print(f"Done: {getattr(r, 'content', '')[:80]}"),
        on_error=lambda e, exc: print(f"Error: {exc}"),
    )

    handler = pipeline.watch_handler(concurrency=3, timeout=120.0)
    await protocol.start(handler)

Test with curl:
    curl -X POST http://localhost:9090/pipeline/trigger \\
        -H "Content-Type: application/json" \\
        -d '{"task": "Research and summarize AI chip trends"}'
""")


async def main() -> None:
    await demo_pipeline_cron()
    demo_dynamic_pipeline_note()

    print("=" * 60)
    print("Both Pipeline and DynamicPipeline inherit Watchable.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
