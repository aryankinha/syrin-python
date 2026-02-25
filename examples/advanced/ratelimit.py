"""Rate limit examples - Proactive API rate limit management.

This module demonstrates the rate limiting features of Syrin, which provides
proactive rate limit management with threshold actions using RateLimitThreshold.

Key concepts:
- APIRateLimit: Configuration for RPM, TPM, RPD limits
- RateLimitThreshold: Threshold for rate limits with metric specification
- ThresholdContext: Context passed to threshold actions
- ThresholdMetric: Enum for metric types
"""

from examples.models.models import almock
from syrin import Agent
from syrin.enums import ThresholdMetric
from syrin.ratelimit import (
    APIRateLimit,
    create_rate_limit_manager,
)
from syrin.threshold import RateLimitThreshold, ThresholdContext


def example_simple_limits():
    """Example 1: Simple rate limits without thresholds."""
    print("\n=== Example 1: Simple Rate Limits ===")

    agent = Agent(
        model=almock,
        rate_limit=APIRateLimit(
            rpm=500,
            tpm=150000,
        ),
    )

    print(f"Rate limit: {agent.rate_limit}")
    print(f"Stats: {agent.rate_limit_stats}")


def example_with_threshold():
    """Example 2: Rate limit with threshold."""
    print("\n=== Example 2: Threshold ===")

    def on_warning(ctx: ThresholdContext):
        print(f"WARNING: {ctx.metric} at {ctx.percentage}%")

    Agent(
        model=almock,
        rate_limit=APIRateLimit(
            rpm=100,
            thresholds=[
                RateLimitThreshold(at=80, action=on_warning, metric=ThresholdMetric.RPM),
            ],
        ),
    )

    print("Agent created with warn at 80% RPM")


def example_with_switch_model():
    """Example 3: Auto-switch model when limit reached."""
    print("\n=== Example 3: Auto-switch Model ===")

    Agent(
        model=almock,
        rate_limit=APIRateLimit(
            rpm=100,
            thresholds=[
                RateLimitThreshold(
                    at=100,
                    action=lambda ctx: ctx.parent.switch_model("openai/gpt-4o-mini"),
                    metric=ThresholdMetric.RPM,
                ),
            ],
        ),
    )

    print("Agent will switch to gpt-4o-mini when RPM limit reached")


def example_multiple_thresholds():
    """Example 4: Multiple thresholds with different actions."""
    print("\n=== Example 4: Multiple Thresholds ===")

    Agent(
        model=almock,
        rate_limit=APIRateLimit(
            rpm=500,
            tpm=150000,
            thresholds=[
                RateLimitThreshold(
                    at=50,
                    action=lambda ctx: print(f"RPM: {ctx.percentage}%"),
                    metric=ThresholdMetric.RPM,
                ),
                RateLimitThreshold(
                    at=100, action=lambda _: print("RPM hit limit!"), metric=ThresholdMetric.RPM
                ),
                RateLimitThreshold(
                    at=70,
                    action=lambda ctx: print(f"TPM: {ctx.percentage}%"),
                    metric=ThresholdMetric.TPM,
                ),
            ],
        ),
    )

    print("Agent configured with multiple thresholds")


def example_standalone_manager():
    """Example 5: Using rate limit manager directly."""
    print("\n=== Example 5: Standalone Manager ===")

    manager = create_rate_limit_manager(
        APIRateLimit(
            rpm=100,
            tpm=50000,
        )
    )

    for _ in range(50):
        manager.record(tokens_used=500)

    allowed, reason = manager.check()

    print(f"Allowed: {allowed}")
    print(f"Reason: {reason}")
    print(f"Stats: {manager.stats}")

    triggered = manager.get_triggered_threshold()
    if triggered:
        print(f"Triggered: at {triggered.at}% metric={triggered.metric}")


def example_events():
    """Example 6: Listening to rate limit events."""
    print("\n=== Example 6: Rate Limit Events ===")

    events_received = []

    def on_event(event: str, ctx: dict):
        events_received.append((event, ctx))
        print(f"Event: {event} - {ctx}")

    agent = Agent(
        model=almock,
        rate_limit=APIRateLimit(
            rpm=100,
            thresholds=[
                RateLimitThreshold(at=50, action=lambda _: None, metric=ThresholdMetric.RPM),
            ],
        ),
    )

    if hasattr(agent, "events"):
        agent.events.on("ratelimit.threshold", on_event)
        agent.events.on("ratelimit.exceeded", on_event)

    print("Event handlers registered")


def example_rpd_limit():
    """Example 7: Daily request limits."""
    print("\n=== Example 7: Daily Request Limits (RPD) ===")

    Agent(
        model=almock,
        rate_limit=APIRateLimit(
            rpd=1000,
            thresholds=[
                RateLimitThreshold(
                    at=90,
                    action=lambda ctx: print(f"RPD at {ctx.percentage}%"),
                    metric=ThresholdMetric.RPD,
                ),
            ],
        ),
    )

    print("Daily limit: 1000 requests")


if __name__ == "__main__":
    example_simple_limits()
    example_with_threshold()
    example_with_switch_model()
    example_multiple_thresholds()
    example_standalone_manager()
    example_events()
    example_rpd_limit()

    print("\n=== All examples completed ===")
