"""Context Management Example.

Demonstrates:
- Using Context for automatic context window management
- Understanding context stats and token usage
- Custom context managers via Protocol
- Auto-compaction at thresholds

Run: python -m examples.advanced.context
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from syrin import Agent, Model
from syrin.context import (
    Context,
    ContextBudget,
    ContextCompactor,
    ContextManager,
    ContextPayload,
    MiddleOutTruncator,
)
from syrin.context.counter import TokenCounter
from syrin.enums import Hook
from syrin.threshold import ContextThreshold

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


def example_default_context() -> None:
    """Default context management - just works."""
    print("\n" + "=" * 50)
    print("Default Context Management")
    print("=" * 50)

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
    )

    messages = agent._build_messages("Hello!")
    print(f"Messages built: {len(messages)}")

    print(f"Context config: {agent.context}")
    print(f"Context stats: {agent.context_stats}")
    print(f"Total tokens: {agent.context_stats.total_tokens}")
    print(f"Max tokens: {agent.context_stats.max_tokens}")
    print(f"Utilization: {agent.context_stats.utilization:.2%}")


def example_custom_context() -> None:
    """Custom context with specific limits."""
    print("\n" + "=" * 50)
    print("Custom Context")
    print("=" * 50)

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
        context=Context(
            max_tokens=80000,
            auto_compact_at=0.75,
        ),
    )

    print(f"Max tokens: {agent.context.max_tokens}")
    print(f"Auto compact at: {agent.context.auto_compact_at:.0%}")

    messages = agent._build_messages("What is Python?")
    print(f"Messages built: {len(messages)}")
    print(f"Context stats: {agent.context_stats}")


def example_context_stats() -> None:
    """Understanding context stats."""
    print("\n" + "=" * 50)
    print("Context Stats")
    print("=" * 50)

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant that answers questions.",
        context=Context(max_tokens=128000),
    )

    stats = agent.context_stats

    print(f"Total tokens used: {stats.total_tokens}")
    print(f"Max context window: {stats.max_tokens}")
    print(f"Utilization: {stats.utilization:.4%}")
    print(f"Was compacted: {stats.compacted}")
    print(f"Compaction count: {stats.compaction_count}")
    print(f"Compaction method: {stats.compaction_method}")


def example_compaction() -> None:
    """Manual compaction for long conversations."""
    print("\n" + "=" * 50)
    print("Manual Compaction")
    print("=" * 50)

    counter = TokenCounter()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
    ]

    for i in range(20):
        messages.append({"role": "user", "content": f"Message {i}: Tell me about topic {i}."})
        messages.append({"role": "assistant", "content": f"Response about topic {i}. " * 50})

    before_count = counter.count_messages(messages).total
    print(f"Tokens before compaction: {before_count}")

    truncator = MiddleOutTruncator()
    budget = 2000

    result = truncator.compact(messages, budget, counter)
    after_count = counter.count_messages(result.messages).total

    print(f"Tokens after compaction: {after_count}")
    print(f"Method used: {result.method}")
    print(f"Messages reduced from {len(messages)} to {len(result.messages)}")


def example_custom_context_manager() -> None:
    """Creating a custom context manager via Protocol."""
    print("\n" + "=" * 50)
    print("Custom Context Manager")
    print("=" * 50)

    class MyContextManager(ContextManager):
        """Custom context manager that always keeps system prompt first."""

        def prepare(
            self,
            messages: list[dict[str, Any]],
            system_prompt: str,
            tools: list[dict[str, Any]],
            memory_context: str,
            budget: ContextBudget,
        ) -> ContextPayload:
            counter = TokenCounter()

            system_msg = {"role": "system", "content": system_prompt}
            other_msgs = [m for m in messages if m.get("role") != "system"]

            available = budget.available
            kept = [system_msg]

            for msg in reversed(other_msgs):
                msg_tokens = counter.count(str(msg))
                if available >= msg_tokens:
                    kept.insert(0, msg)
                    available -= msg_tokens
                else:
                    break

            all_tokens = counter.count_messages(kept).total

            return ContextPayload(
                messages=kept,
                system_prompt=system_prompt,
                tools=tools,
                tokens=all_tokens,
            )

        def on_compact(self, event: Any) -> None:
            print(f"Compaction happened: {event.method}")

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
        context=MyContextManager(),
    )

    messages = agent._build_messages("Hello!")
    print("Custom context manager works!")
    print(f"Messages: {len(messages)}")


def example_context_with_events() -> None:
    """Context with observability via debug mode."""
    print("\n" + "=" * 50)
    print("Context with Events and Debug Mode")
    print("=" * 50)

    compact_events = []

    def on_compact(ctx):
        compact_events.append(ctx)
        print(f"Compaction event: {ctx}")

    # Create agent with debug mode for visibility
    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
        context=Context(max_tokens=128000),
        debug=True,
    )

    # Register for context events
    agent.events.on(Hook.CONTEXT_COMPRESS, on_compact)

    messages = agent._build_messages("Hi there!")
    print(f"Built {len(messages)} messages")
    print(f"Stats: {agent.context_stats}")
    print(f"Compact events: {len(compact_events)}")


def example_compaction_events() -> None:
    """Demonstrate compaction events with long conversations."""
    print("\n" + "=" * 50)
    print("Compaction Events")
    print("=" * 50)

    compact_events = []

    def on_compact(ctx):
        compact_events.append(ctx)
        print(f"COMPACTED: {ctx['method']}")
        print(f"  Tokens: {ctx['tokens_before']} -> {ctx['tokens_after']}")
        print(f"  Messages: {ctx['messages_before']} -> {ctx['messages_after']}")

    # Small budget to force compaction
    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
        context=Context(max_tokens=5000),
    )

    agent.events.on(Hook.CONTEXT_COMPRESS, on_compact)

    # Build many messages to trigger compaction
    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for i in range(50):
        messages.append({"role": "user", "content": f"Message {i}: " + "x" * 500})

    # Use context manager directly
    agent._context_manager.prepare(
        messages=messages,
        system_prompt="You are a helpful assistant.",
        tools=[],
        memory_context="",
    )

    print(f"Compact events received: {len(compact_events)}")
    print(f"Final stats: {agent.context_stats}")


def example_context_thresholds() -> None:
    """Context thresholds using ContextThreshold class."""
    print("\n" + "=" * 50)
    print("Context Thresholds")
    print("=" * 50)

    threshold_events = []

    def on_threshold(ctx):
        threshold_events.append(ctx)
        print(f"THRESHOLD: {ctx.percentage}%")

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
        context=Context(
            max_tokens=5000,
            thresholds=[
                ContextThreshold(at=50, action=on_threshold),
                ContextThreshold(at=70, action=lambda _: print("High context usage!")),
                ContextThreshold(at=100, action=lambda _: print("Context full!")),
            ],
        ),
    )

    agent.events.on(Hook.CONTEXT_COMPRESS, on_threshold)

    # Build many messages to exceed thresholds
    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for i in range(50):
        messages.append({"role": "user", "content": f"Message {i}: " + "x" * 500})

    agent._context_manager.prepare(
        messages=messages,
        system_prompt="You are a helpful assistant.",
        tools=[],
        memory_context="",
    )

    print(f"\nThreshold events received: {len(threshold_events)}")
    print(f"Thresholds triggered in stats: {agent.context_stats.thresholds_triggered}")
    print(f"Utilization: {agent.context_stats.utilization:.1%}")


def example_custom_threshold_handler() -> None:
    """Custom threshold handler."""
    print("\n" + "=" * 50)
    print("Custom Threshold Handler")
    print("=" * 50)

    custom_calls = []

    def my_handler(ctx):
        custom_calls.append(ctx)
        print(f"CUSTOM HANDLER called: {ctx}")

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
        context=Context(
            max_tokens=5000,
            thresholds=[
                ContextThreshold(at=50, action=my_handler),
            ],
        ),
    )

    messages = [{"role": "system", "content": "You are helpful."}]
    for i in range(50):
        messages.append({"role": "user", "content": f"Message {i}: " + "x" * 500})

    agent._context_manager.prepare(
        messages=messages,
        system_prompt="You are a helpful assistant.",
        tools=[],
        memory_context="",
    )

    print(f"Custom handler calls: {len(custom_calls)}")
    print(f"Thresholds triggered: {agent.context_stats.thresholds_triggered}")


def example_budget_detection() -> None:
    """Context auto-detects model context window."""
    print("\n" + "=" * 50)
    print("Budget Detection")
    print("=" * 50)

    agent = Agent(
        model=Model(MODEL_ID),
        system_prompt="You are a helpful assistant.",
    )

    budget = agent.context.get_budget(agent._model)
    print(f"Auto-detected max tokens: {budget.max_tokens}")
    print(f"Available for messages: {budget.available}")
    print(f"Auto-compact at: {budget.auto_compact_at:.0%}")


def example_long_conversation() -> None:
    """Simulating a long conversation with compaction."""
    print("\n" + "=" * 50)
    print("Long Conversation Simulation")
    print("=" * 50)

    counter = TokenCounter()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
    ]

    for i in range(10):
        messages.append({"role": "user", "content": f"User message number {i} - " + "x" * 100})
        messages.append(
            {"role": "assistant", "content": f"Assistant response number {i} - " + "y" * 100}
        )

    tokens_before = counter.count_messages(messages).total
    print(f"Tokens before: {tokens_before}")

    compact_result = ContextCompactor().compact(messages, 3000)
    tokens_after = counter.count_messages(compact_result.messages).total

    print(f"Tokens after: {tokens_after}")
    print(f"Method: {compact_result.method}")
    print(f"Reduced by: {tokens_before - tokens_after} tokens")


if __name__ == "__main__":
    example_default_context()
    example_custom_context()
    example_context_stats()
    example_compaction()
    example_custom_context_manager()
    example_context_with_events()
    example_compaction_events()
    example_context_thresholds()
    example_custom_threshold_handler()
    example_budget_detection()
    example_long_conversation()
