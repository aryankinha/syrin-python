"""Budget guardrails — fanout cap, A2A message budget, retry cap, tool call storm.

Shows the static budget guardrail checks that protect against runaway costs
in dynamic multi-agent systems.

Key concepts:
  - BudgetGuardrails.check_fanout(items, max_agents=5) → DynamicFanoutError
  - A2AConfig(budget_per_message=0.05, max_messages_per_sender=10)
  - BudgetGuardrails.check_retry_budget(retry_spent, max_cost, max_ratio=0.3)
  - BudgetGuardrails.check_daily_limit(spent_today, daily_limit)
  - BudgetGuardrails.check_anomaly(actual, p95, AnomalyConfig(...))

Run:
    uv run python examples/budget_guardrails.py
"""

from __future__ import annotations

import asyncio

from syrin.budget._guardrails import (
    AnomalyConfig,
    BudgetGuardrails,
    BudgetLimitError,
    DynamicFanoutError,
    RetryBudgetExhausted,
)
from syrin.enums import Hook
from syrin.swarm import A2ABudgetExceededError, A2AConfig, A2ARouter

# ── Example 1: Dynamic fanout cap ─────────────────────────────────────────────
#
# When a dynamic step's lambda returns more agents than max_agents allows,
# DynamicFanoutError is raised immediately — before any agents are spawned.


async def example_fanout_cap() -> None:
    print("\n── Example 1: Dynamic fanout cap ────────────────────────────────")

    max_agents = 5

    # Good case: lambda returns 3 items — within the cap
    good_tasks = ["task A", "task B", "task C"]
    try:
        BudgetGuardrails.check_fanout(items=good_tasks, max_agents=max_agents)
        print(f"  3 tasks: OK (below cap of {max_agents})")
    except DynamicFanoutError as e:
        print(f"  ERROR: {e}")

    # Bad case: lambda returns 10 items — exceeds cap
    too_many_tasks = [f"task {i}" for i in range(10)]
    try:
        BudgetGuardrails.check_fanout(items=too_many_tasks, max_agents=max_agents)
        print("  10 tasks: unexpectedly OK")
    except DynamicFanoutError as e:
        print(f"  DynamicFanoutError: requested={e.requested}  max_allowed={e.max_allowed}")

    # Practical usage pattern in a workflow dynamic step:
    print("\n  Pattern in a dynamic step callback:")
    print("    def my_dynamic_step(previous_output):")
    print("        agents = router.plan(previous_output)  # LLM returns N agents")
    print("        BudgetGuardrails.check_fanout(agents, max_agents=5)  # guard first")
    print("        return agents  # only runs if <= 5")


# ── Example 2: A2A message budget ─────────────────────────────────────────────
#
# A2AConfig.budget_per_message and max_messages_per_sender prevent an agent
# from flooding the message bus.


async def example_a2a_budget() -> None:
    print("\n── Example 2: A2A message budget ────────────────────────────────")

    events: list[str] = []

    def fire_fn(hook: Hook, ctx: dict[str, object]) -> None:
        events.append(str(hook))

    config = A2AConfig(
        budget_per_message=0.05,  # each message costs $0.05 from sender's budget
        max_messages_per_sender=3,  # sender can send at most 3 messages per run
        audit_all=True,
    )

    router = A2ARouter(config=config, fire_event_fn=fire_fn)
    router.register("agent-a")
    router.register("agent-b")

    from syrin.enums import A2AChannel

    # Send messages within the limit
    for i in range(3):
        await router.send(
            from_agent="agent-a",
            to_agent="agent-b",
            content=f"Message {i + 1}",
            channel=A2AChannel.DIRECT,
        )
    print("  Sent 3 messages OK")
    print(f"  Sender spend: ${config.budget_per_message * 3:.4f}")

    # 4th message exceeds max_messages_per_sender
    try:
        await router.send(
            from_agent="agent-a",
            to_agent="agent-b",
            content="Overflow message",
            channel=A2AChannel.DIRECT,
        )
    except A2ABudgetExceededError as e:
        print(f"  A2ABudgetExceededError on message 4: sender={e.sender_id}")

    # Audit log shows all successful sends
    audit = router.audit_log()
    print(f"  Audit log entries: {len(audit)}")


# ── Example 3: Retry budget cap ───────────────────────────────────────────────
#
# Budget(max_retry_spend_ratio=0.3) means at most 30% of max_cost may be
# consumed by LLM retries. BudgetGuardrails.check_retry_budget enforces this.


async def example_retry_cap() -> None:
    print("\n── Example 3: Retry spend cap ───────────────────────────────────")

    max_cost = 1.00
    max_retry_ratio = 0.30  # 30% of $1.00 = $0.30 max for retries

    # Under cap: $0.20 in retries on a $1.00 budget — OK
    try:
        BudgetGuardrails.check_retry_budget(
            retry_spent=0.20,
            max_cost=max_cost,
            max_ratio=max_retry_ratio,
        )
        print(f"  $0.20 retries on $1.00 budget: OK (limit=${max_cost * max_retry_ratio:.2f})")
    except RetryBudgetExhausted as e:
        print(f"  ERROR: {e}")

    # Over cap: $0.35 in retries on a $1.00 budget — raises
    try:
        BudgetGuardrails.check_retry_budget(
            retry_spent=0.35,
            max_cost=max_cost,
            max_ratio=max_retry_ratio,
        )
        print("  $0.35 retries: unexpectedly OK")
    except RetryBudgetExhausted as e:
        print(f"  RetryBudgetExhausted: spent=${e.retry_spent:.4f}  limit=${e.limit:.4f}")


# ── Example 4: Daily limit check ──────────────────────────────────────────────


async def example_daily_limit() -> None:
    print("\n── Example 4: Daily limit check ─────────────────────────────────")

    daily_limit = 50.00

    # Within limit — OK
    try:
        BudgetGuardrails.check_daily_limit(spent_today=42.30, daily_limit=daily_limit)
        print("  $42.30 of $50.00 daily budget: OK")
    except BudgetLimitError:
        print("  ERROR")

    # Exceeded — raises
    try:
        BudgetGuardrails.check_daily_limit(spent_today=50.01, daily_limit=daily_limit)
    except BudgetLimitError as e:
        print(
            f"  BudgetLimitError: spent=${e.spent:.2f}  limit=${e.limit:.2f}  type={e.limit_type}"
        )

    # Daily limit approaching hook (80% threshold)
    approaching_events: list[dict[str, object]] = []

    def fire_fn(hook: Hook, ctx: dict[str, object]) -> None:
        approaching_events.append({"hook": str(hook), **ctx})

    BudgetGuardrails.check_daily_approaching(
        spent_today=43.00,
        daily_limit=daily_limit,
        fire_fn=fire_fn,
        threshold_pct=0.80,
    )

    if approaching_events:
        evt = approaching_events[0]
        print(f"  DAILY_LIMIT_APPROACHING hook: pct_used={evt.get('pct_used', 0):.1f}%")


# ── Example 5: Anomaly detection ──────────────────────────────────────────────
#
# BudgetGuardrails.check_anomaly fires Hook.BUDGET_ANOMALY when
# actual_cost > threshold_multiplier * p95_cost.


async def example_anomaly_detection() -> None:
    print("\n── Example 5: Budget anomaly detection ──────────────────────────")

    anomaly_config = AnomalyConfig(threshold_multiplier=2.0)
    anomaly_events: list[dict[str, object]] = []

    def fire_fn(hook: Hook, ctx: dict[str, object]) -> None:
        if hook == Hook.BUDGET_ANOMALY:
            anomaly_events.append(dict(ctx))

    p95_estimate = 0.05  # expected p95 cost = $0.05

    # Normal cost — no anomaly
    BudgetGuardrails.check_anomaly(
        actual=0.04, p95=p95_estimate, config=anomaly_config, fire_fn=fire_fn
    )
    print("  $0.04 actual vs $0.05 p95: no anomaly")

    # Anomalous cost — more than 2x p95
    BudgetGuardrails.check_anomaly(
        actual=0.15, p95=p95_estimate, config=anomaly_config, fire_fn=fire_fn
    )

    if anomaly_events:
        evt = anomaly_events[0]
        print(
            f"  BUDGET_ANOMALY: actual=${evt.get('actual'):.4f}  "
            f"p95=${evt.get('p95'):.4f}  "
            f"threshold=${evt.get('threshold'):.4f}  "
            f"multiplier={evt.get('threshold_multiplier')}"
        )


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    await example_fanout_cap()
    await example_a2a_budget()
    await example_retry_cap()
    await example_daily_limit()
    await example_anomaly_detection()
    print("\nAll budget guardrail examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
