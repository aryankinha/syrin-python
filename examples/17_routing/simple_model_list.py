"""Minimal Agent routing — model list + RoutingConfig.

All models get GENERAL strength
by default. Best for simple cost/quality trade-off, not task-specific routing.

Features: model=[M1, M2, M3], RoutingConfig(routing_mode=...).

Run: python -m examples.17_routing.simple_model_list
Run with traces: python -m examples.17_routing.simple_model_list --trace
"""

from __future__ import annotations

import sys

from syrin import Agent
from syrin.model import Model
from syrin.router import RoutingConfig, RoutingMode


def main() -> None:
    # All models treated as GENERAL-capable; router picks by cost/priority
    models = [
        Model.Almock(pricing_tier="low", latency_min=0, latency_max=0),
        Model.Almock(pricing_tier="high", latency_min=0, latency_max=0),
    ]

    use_trace = "--trace" in sys.argv
    agent = Agent(
        model=models,
        model_router=RoutingConfig(routing_mode=RoutingMode.COST_FIRST),
        system_prompt="You are helpful.",
        debug=use_trace,
    )

    r = agent.response("Hello")
    print(f"Routed to: {r.routing_reason.selected_model if r.routing_reason else 'N/A'}")
    print(f"Content: {r.content[:50]}...")


if __name__ == "__main__":
    main()
