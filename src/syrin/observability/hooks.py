"""Integration between observability and the Hook system.

This module provides a bridge between the new observability (spans, traces)
and the existing Hook enum-based lifecycle events.

Usage:
    >>> from syrin.observability.hooks import observe_hooks
    >>>
    >>> # Automatically emit spans for every hook
    >>> observe_hooks(agent)
    >>>
    >>> # Or use as context manager
    >>> with hook_observer(agent) as observer:
    ...     agent.run("Hello")
"""

from __future__ import annotations

import types
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from syrin.enums import Hook
from syrin.events import EventContext, Events


class HookObserver:
    """Bridge between Events system and observability spans.

    This observer automatically creates spans for lifecycle events,
    giving you both the simple event handling AND detailed tracing.
    """

    def __init__(self, events: Events) -> None:
        self._events = events
        self._handlers: dict[str, Callable[[EventContext], None]] = {}
        self._observability: types.ModuleType | None = None

    def attach(self) -> None:
        """Attach observers to all events."""
        # Import here to avoid circular imports
        import syrin.observability as obs

        self._observability = obs

        # Map events to span kinds
        event_to_kind = {
            Hook.AGENT_RUN_START: obs.SpanKind.AGENT,
            Hook.LLM_REQUEST_START: obs.SpanKind.LLM,
            Hook.LLM_REQUEST_END: obs.SpanKind.LLM,
            Hook.LLM_RETRY: obs.SpanKind.LLM,
            Hook.LLM_FALLBACK: obs.SpanKind.LLM,
            Hook.TOOL_CALL_START: obs.SpanKind.TOOL,
            Hook.TOOL_ERROR: obs.SpanKind.INTERNAL,
            Hook.AGENT_RUN_END: obs.SpanKind.AGENT,
            Hook.BUDGET_CHECK: obs.SpanKind.BUDGET,
            Hook.CIRCUIT_TRIP: obs.SpanKind.INTERNAL,
        }

        for event, kind in event_to_kind.items():
            handler = self._make_handler(event.value, kind)
            self._handlers[event.value] = handler
            self._events.on(event, handler)

    def _make_handler(
        self,
        event_name: str,
        _kind: object,
    ) -> Callable[[EventContext], None]:
        """Create a handler for a specific event."""
        obs = self._observability
        assert obs is not None

        def handler(ctx: EventContext) -> None:
            current = obs.current_span()
            if current:
                # Add event to current span
                current.add_event(event_name, dict(ctx))

                # Add relevant attributes based on event
                if event_name == "start" and "input" in ctx:
                    inp = ctx.get("input", "")
                    current.set_attribute(
                        "user.input", (inp if isinstance(inp, str) else str(inp))[:200]
                    )
                elif event_name == "response" and "cost" in ctx:
                    current.set_attribute(obs.SemanticAttributes.LLM_COST, ctx.get("cost", 0))
                elif event_name == "response" and "tokens" in ctx:
                    current.set_attribute(
                        obs.SemanticAttributes.LLM_TOKENS_TOTAL,
                        ctx.get("tokens", 0),
                    )
                elif event_name == "tool" and "name" in ctx:
                    current.set_attribute(obs.SemanticAttributes.TOOL_NAME, ctx.get("name"))
                elif event_name == "budget" and "remaining" in ctx:
                    current.set_attribute(
                        obs.SemanticAttributes.BUDGET_REMAINING,
                        ctx.get("remaining"),
                    )
                elif event_name == "llm_fallback" and "from_model" in ctx:
                    current.set_attribute(
                        obs.SemanticAttributes.LLM_FALLBACK_FROM,
                        ctx.get("from_model"),
                    )
                elif event_name == "llm_fallback" and "to_model" in ctx:
                    current.set_attribute(
                        obs.SemanticAttributes.LLM_FALLBACK_TO,
                        ctx.get("to_model"),
                    )
                elif event_name == "circuit_trip" and "error" in ctx:
                    current.set_attribute(obs.SemanticAttributes.ERROR_MESSAGE, ctx.get("error"))

        return handler

    def detach(self) -> None:
        """Remove all handlers."""
        # Events system doesn't have a remove method - handlers remain attached
        # but won't be called if the HookObserver is removed from the tracer
        pass


def observe_hooks(agent: object) -> HookObserver:
    """Attach observability to an agent's events.

    This function connects the observability system to an agent's
    lifecycle events, enriching spans with event data.

    Args:
        agent: An Agent instance with .events attribute

    Returns:
        HookObserver that can be used to manage the connection

    Example:
        >>> observe_hooks(my_agent)
        >>> result = my_agent.run("Hello")
        >>> # Spans now include event data from the Events system
    """
    if not hasattr(agent, "events"):
        raise ValueError("Agent must have an 'events' attribute")

    observer = HookObserver(agent.events)
    observer.attach()

    return observer


@contextmanager
def hook_observer(agent: object) -> Iterator[HookObserver]:
    """Context manager for observing hooks.

    Example:
        >>> with hook_observer(agent) as observer:
        ...     result = agent.run("Hello")
    """
    observer = observe_hooks(agent)
    try:
        yield observer
    finally:
        observer.detach()


__all__ = [
    "HookObserver",
    "observe_hooks",
    "hook_observer",
]
