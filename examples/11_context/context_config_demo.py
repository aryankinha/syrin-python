"""Context — context window config with 3–5 knobs for 90% of cases.

Shows:
- Context(max_tokens, reserve, thresholds, token_limits, auto_compact_at)
- Pass via config=AgentConfig(context=Context(...))
- Use when you only need window size, reserve, thresholds, token caps, or proactive compaction

Run: python -m examples.11_context.context_config_demo
"""

from __future__ import annotations

from examples.models.models import almock
from syrin import Agent, AgentConfig
from syrin.context import Context


def main() -> None:
    print("=" * 60)
    print("Context — simple context config (max_tokens, reserve, auto_compact_at)")
    print("=" * 60)

    agent = Agent(
        model=almock,
        system_prompt="You are a helpful assistant. Be brief.",
        config=AgentConfig(
            context=Context(
                max_tokens=8000,
                reserve=2000,
                auto_compact_at=0.6,
            )
        ),
    )

    r = agent.run("Say hello in one word.")
    print(f"\nReply: {r.content}")
    print(
        f"Context stats: tokens={agent.context_stats.total_tokens}, utilization={agent.context_stats.utilization:.2%}"
    )
    print(
        "\nContextConfig builds a full Context internally; use it when you only need the main knobs."
    )


if __name__ == "__main__":
    main()
