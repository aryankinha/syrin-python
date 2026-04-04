"""Budget anomaly detection — AnomalyConfig, Hook.BUDGET_ANOMALY, alerting.

Detects when a run's actual cost is suspiciously high compared to the
historical p95 estimate — a signal that something may have gone wrong
(infinite loop, unexpected token explosion, misconfigured agent, etc.).

Key concepts:
  - Budget(anomaly_detection=AnomalyConfig(threshold_multiplier=2.0))
  - Hook.BUDGET_ANOMALY — fires when actual_cost > threshold_multiplier * p95
  - EventContext: actual, p95, threshold, threshold_multiplier
  - Integrating with alerting (log, Slack, PagerDuty, etc.)

Run:
    uv run python examples/budget_anomaly.py
"""

from __future__ import annotations

import asyncio
import logging

from syrin import Agent, Budget, Model
from syrin.budget._guardrails import AnomalyConfig, BudgetGuardrails
from syrin.enums import Hook
from syrin.response import Response
from syrin.workflow import Workflow

logger = logging.getLogger(__name__)


# ── Agent definitions ─────────────────────────────────────────────────────────


class NormalAgent(Agent):
    """Agent with predictable, low cost output."""

    model = Model.mock(latency_seconds=0.05, lorem_length=6)
    system_prompt = "You produce concise summaries."
    output_tokens_estimate = 200  # helps the estimator establish p95

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content=f"Normal output for: {input_text[:40]}", cost=0.003)


class AnomalousAgent(Agent):
    """Agent that occasionally produces unexpectedly large outputs."""

    model = Model.mock(latency_seconds=0.05, lorem_length=6)
    system_prompt = "You produce detailed analysis."
    output_tokens_estimate = 200  # baseline hint

    async def arun(self, input_text: str) -> Response[str]:
        # Simulate a runaway response — 10x the expected cost
        return Response(content="Very long anomalous output... " * 50, cost=0.08)


# ── Example 1: Detect anomaly via BudgetGuardrails.check_anomaly() ────────────
#
# This is the direct API. In practice the workflow executor calls this
# automatically when Budget(anomaly_detection=...) is set.


async def example_direct_anomaly_check() -> None:
    print("\n── Example 1: Direct anomaly check ──────────────────────────────")

    anomaly_config = AnomalyConfig(threshold_multiplier=2.0)
    anomaly_events: list[dict[str, object]] = []

    def fire_fn(hook: Hook, ctx: dict[str, object]) -> None:
        if hook == Hook.BUDGET_ANOMALY:
            anomaly_events.append(dict(ctx))

    p95_reference = 0.005  # typical p95 cost for this agent

    # Normal run: $0.004 — below 2x threshold ($0.01)
    BudgetGuardrails.check_anomaly(
        actual=0.004, p95=p95_reference, config=anomaly_config, fire_fn=fire_fn
    )
    print("  Normal run ($0.004): no anomaly")

    # Anomalous run: $0.015 — above 2x threshold ($0.01)
    BudgetGuardrails.check_anomaly(
        actual=0.015, p95=p95_reference, config=anomaly_config, fire_fn=fire_fn
    )

    if anomaly_events:
        evt = anomaly_events[0]
        print(
            f"  BUDGET_ANOMALY detected:"
            f"\n    actual:     ${evt['actual']:.4f}"
            f"\n    p95:        ${evt['p95']:.4f}"
            f"\n    threshold:  ${evt['threshold']:.4f}  ({anomaly_config.threshold_multiplier}× p95)"
            f"\n    multiplier: {evt['threshold_multiplier']}"
        )


# ── Example 2: Hook.BUDGET_ANOMALY on an Agent ────────────────────────────────
#
# When Budget(anomaly_detection=...) is attached, the agent fires
# Hook.BUDGET_ANOMALY automatically if its actual cost exceeds the threshold.


async def example_agent_anomaly_hook() -> None:
    print("\n── Example 2: Hook.BUDGET_ANOMALY on an agent ───────────────────")

    anomaly_log: list[dict[str, object]] = []

    def on_anomaly(ctx: object) -> None:
        entry = {
            "actual": ctx.get("actual"),  # type: ignore[union-attr]
            "p95": ctx.get("p95"),  # type: ignore[union-attr]
            "threshold": ctx.get("threshold"),  # type: ignore[union-attr]
        }
        anomaly_log.append(entry)
        print(
            f"  [ANOMALY] actual=${entry['actual'] or 0:.4f}  "
            f"p95=${entry['p95'] or 0:.4f}  "
            f"threshold=${entry['threshold'] or 0:.4f}"
        )

    agent = AnomalousAgent(
        budget=Budget(
            max_cost=1.00,
            anomaly_detection=AnomalyConfig(threshold_multiplier=2.0),
        )
    )

    agent.events.on(Hook.BUDGET_ANOMALY, on_anomaly)

    agent.run("Produce a detailed analysis of AI agent frameworks")

    if not anomaly_log:
        # AnomalousAgent returns cost=0.08; if estimation history has p95 < 0.04,
        # the hook fires. On first run, history is empty and the default p95
        # fallback is used instead.
        print("  (Anomaly hook fires after cost history is established)")
        print("  Run the agent multiple times to build a p95 baseline.")


# ── Example 3: Workflow with anomaly detection ────────────────────────────────


async def example_workflow_anomaly() -> None:
    print("\n── Example 3: Workflow with anomaly detection ───────────────────")

    anomaly_events: list[str] = []

    wf = (
        Workflow(
            "anomaly-demo",
            budget=Budget(
                max_cost=1.00,
                anomaly_detection=AnomalyConfig(threshold_multiplier=1.5),
            ),
        )
        .step(NormalAgent)
        .step(AnomalousAgent)  # this step will trigger the anomaly check
        .step(NormalAgent)
    )

    wf.events.on(
        Hook.BUDGET_ANOMALY,
        lambda ctx: anomaly_events.append(
            f"actual=${ctx.get('actual', 0):.4f} threshold=${ctx.get('threshold', 0):.4f}"
        ),
    )

    result = await wf.run("Run the anomaly detection pipeline")
    print(f"  Workflow completed. Cost: ${result.cost:.4f}")
    print(f"  Anomaly events: {anomaly_events or ['none (no history yet)']}")


# ── Example 4: Alerting integration patterns ─────────────────────────────────
#
# Hook handlers are plain Python callables — plug in any alerting system.


async def example_alerting_integration() -> None:
    print("\n── Example 4: Alerting integration patterns ─────────────────────")

    # Pattern A: Python logging
    def alert_via_logging(ctx: object) -> None:
        actual = ctx.get("actual", 0)  # type: ignore[union-attr]
        threshold = ctx.get("threshold", 0)  # type: ignore[union-attr]
        logger.warning(
            "BUDGET_ANOMALY: cost $%.4f exceeded threshold $%.4f — investigate",
            actual,
            threshold,
        )

    # Pattern B: Print to stdout (webhook replacement in this example)
    def alert_via_webhook(ctx: object) -> None:
        actual = ctx.get("actual", 0)  # type: ignore[union-attr]
        agent_name = ctx.get("agent_name", "unknown")  # type: ignore[union-attr]
        print(
            f"  [WEBHOOK] Would POST: {{'agent': '{agent_name}', "
            f"'anomaly_cost': {actual:.4f}, "
            f"'severity': 'high'}}"
        )

    # Pattern C: Conditional escalation
    def alert_with_escalation(ctx: object) -> None:
        actual = ctx.get("actual", 0)  # type: ignore[union-attr]
        p95 = ctx.get("p95", 0.001)  # type: ignore[union-attr]
        ratio = actual / p95 if p95 > 0 else 0

        if ratio >= 5.0:
            print(f"  [ESCALATE] Severity=CRITICAL: {ratio:.1f}× p95 — page on-call")
        elif ratio >= 2.0:
            print(f"  [ALERT]    Severity=HIGH: {ratio:.1f}× p95 — notify team Slack")
        else:
            print(f"  [WARN]     Severity=LOW: {ratio:.1f}× p95 — log only")

    # Demonstrate pattern C with simulated anomaly data
    from syrin.events import EventContext

    simulated_ctx = EventContext({"actual": 0.25, "p95": 0.05, "threshold": 0.10})
    alert_with_escalation(simulated_ctx)

    print("\n  Common alerting patterns:")
    print("    agent.events.on(Hook.BUDGET_ANOMALY, alert_via_logging)")
    print("    agent.events.on(Hook.BUDGET_ANOMALY, alert_via_webhook)")
    print("    agent.events.on(Hook.BUDGET_ANOMALY, alert_with_escalation)")


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    await example_direct_anomaly_check()
    await example_agent_anomaly_hook()
    await example_workflow_anomaly()
    await example_alerting_integration()
    print("\nAll budget anomaly examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
