"""Budget: rate limits, token limits, and configurable month window.

Demonstrates:
- Rate limits (hour/day/week/month) in USD with optional month_days
- Token limits via TokenLimits (separate from Budget)
- calendar_month=True for current calendar month (vs rolling last N days)
- Using FileBudgetStore so rate limits persist across restarts

Run: python -m examples.core.budget_rate_limits_and_tokens
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from syrin import (
    Agent,
    Budget,
    Context,
    ContextBudget,
    Model,
    RateLimit,
    TokenRateLimit,
    raise_on_exceeded,
    warn_on_exceeded,
)
from syrin.budget_store import FileBudgetStore

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


def example_budget_plus_token_limits() -> None:
    """Budget (USD only) + TokenLimits (separate). Recommended way to cap both spend and usage."""
    print("\n" + "=" * 55)
    print("Budget (USD) + TokenLimits (separate)")
    print("=" * 55)

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are concise. Answer in one short paragraph.",
        budget=Budget(run=0.05, on_exceeded=warn_on_exceeded),
        context=Context(
            budget=ContextBudget(
                run=15_000,
                per=TokenRateLimit(hour=50_000, day=200_000),
                on_exceeded=warn_on_exceeded,
            )
        ),
    )
    print("1. Budget: run=$0.05 (USD only). Context.budget: run=15k, hour=50k, day=200k tokens.")
    result = agent.response("What is machine learning in one paragraph?")
    print(f"\n2. Response cost: ${result.cost:.6f}, tokens: {result.tokens.total_tokens}")
    print(f"   Summary: {agent.budget_summary}")


def example_rate_limits_plus_token_limits() -> None:
    """Combine Budget (USD rate limits) and TokenLimits (token caps)."""
    print("\n" + "=" * 55)
    print("Rate limits (USD) + TokenLimits (tokens)")
    print("=" * 55)

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are concise. Answer in one short paragraph.",
        budget=Budget(
            run=0.05,
            per=RateLimit(hour=2.00, day=10.00, month=100.00, month_days=30),
            on_exceeded=warn_on_exceeded,
        ),
        context=Context(
            budget=ContextBudget(
                run=15_000,
                per=TokenRateLimit(hour=50_000, day=200_000),
                on_exceeded=warn_on_exceeded,
            )
        ),
    )
    print("1. Budget: run=$0.05, per hour=$2, day=$10, month=$100 (USD)")
    print("   Context.budget: run=15k, hour=50k, day=200k tokens")
    print("   (Rate limits are in-memory; pass budget_store to persist across restarts)")

    result = agent.response("What is machine learning in one paragraph?")
    print(f"\n2. Response cost: ${result.cost:.6f}")
    print(f"   Summary: {agent.budget_summary}")


def example_persistent_rate_limits_with_file_store() -> None:
    """Use FileBudgetStore so hour/day/month limits apply across restarts."""
    print("\n" + "=" * 55)
    print("Persistent rate limits (FileBudgetStore)")
    print("=" * 55)

    store_path = Path(__file__).resolve().parent.parent / "data" / "budget_example.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)

    class PersistentBudgetAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are concise."
        budget = Budget(
            run=0.10,
            per=RateLimit(day=5.00, month=50.00, month_days=30),
            on_exceeded=raise_on_exceeded,
        )

    agent = PersistentBudgetAgent(
        budget_store=FileBudgetStore(store_path, single_file=True),
        budget_store_key="example_user",
    )
    print(f"1. Using FileBudgetStore at {store_path}")
    print("   budget_store_key='example_user' — use different keys per user/org for isolation")

    result = agent.response("Summarize Python in two sentences.")
    print(f"\n2. Cost: ${result.cost:.6f}")
    print(f"   Budget summary: {agent.budget_summary}")


def example_configurable_month_window() -> None:
    """month_days controls the length of the 'month' window (default 30)."""
    print("\n" + "=" * 55)
    print("Configurable month window (month_days)")
    print("=" * 55)

    # Last 7 days as "month" for a short rolling window
    r = RateLimit(month=20.00, month_days=7)
    print("1. RateLimit(month=20, month_days=7) → 'month' = last 7 days")
    assert r.month_days == 7

    # Default is 30
    r2 = RateLimit(month=100.0)
    print(f"2. RateLimit(month=100) → month_days defaults to {r2.month_days}")


def example_calendar_month() -> None:
    """Use calendar_month=True for current calendar month (e.g. 1–30 Nov) instead of last N days."""
    print("\n" + "=" * 55)
    print("Calendar month (current month only)")
    print("=" * 55)

    r = RateLimit(month=500.00, calendar_month=True)
    print("1. RateLimit(month=500, calendar_month=True) → month = current calendar month only")
    assert r.calendar_month is True


if __name__ == "__main__":
    example_budget_plus_token_limits()
    example_rate_limits_plus_token_limits()
    example_persistent_rate_limits_with_file_store()
    example_configurable_month_window()
    example_calendar_month()
