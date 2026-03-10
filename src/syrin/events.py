"""Event system for Agent lifecycle using Hook enums.

This module provides the Events class for registering and triggering
hooks throughout the agent lifecycle.

Usage:
    from syrin import Agent, Hook
    from syrin.events import Events, EventContext

    # Register handler for a hook
    agent.events.on(Hook.AGENT_RUN_START, lambda ctx: print(f"Starting: {ctx.input}"))

    # Before/after hooks (can modify data!)
    agent.events.before(Hook.LLM_REQUEST_START, lambda ctx: ctx.update({"temperature": 0.5}))
    agent.events.after(Hook.LLM_REQUEST_END, lambda ctx: print(f"Response: {ctx.content}"))

    # Convenience methods
    agent.events.on_start(lambda ctx: print("Agent started"))
    agent.events.on_complete(lambda ctx: print("Agent completed"))
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from syrin.enums import Hook


class EventContext(dict[str, object]):
    """Context dictionary for events with dot notation access.

    Acts like a dict but allows accessing fields with dot notation.
    This makes event handlers more readable.

    Example:
        def on_start(ctx):
            print(f"Input: {ctx.input}")  # dot access
            print(f"Model: {ctx['model']}")  # dict access

    Attributes:
        All fields are dynamic based on the hook being triggered.
        See hooks.py for field documentation.
    """

    def __getattr__(self, key: str) -> object:
        try:
            return self[key]
        except KeyError as err:
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{key}'") from err

    def __setattr__(self, key: str, value: object) -> None:
        self[key] = value

    def __repr__(self) -> str:
        return f"EventContext({dict.__repr__(self)})"


class Events:
    """Event system for Agent using Hook enums.

    The Events class allows you to register handlers for various lifecycle
    events (hooks) in the agent execution. Handlers receive an EventContext
    containing relevant data for that hook.

    Handler Types:
        - on: Normal handlers run during the event
        - before: Run before the event, can modify context
        - after: Run after the event, for logging/metrics

    Note: Handlers are synchronous and run in the agent's execution path. Keep them fast
    (e.g. in-memory logging). Slow handlers (HTTP calls, DB writes) will block the agent.
    Use fire-and-forget (thread/async) in the handler for non-blocking side effects.

    Example:
        # Register normal handler
        agent.events.on(Hook.AGENT_RUN_START, lambda ctx: print(f"Start: {ctx.input}"))

        # Register before handler (can modify data!)
        agent.events.before(Hook.LLM_REQUEST_START, lambda ctx: ctx.update({"temp": 0.5}))

        # Register after handler (for logging)
        agent.events.after(Hook.LLM_REQUEST_END, lambda ctx: print(f"Tokens: {ctx.tokens}"))

        # Convenience methods
        agent.events.on_start(lambda ctx: print("Started"))
        agent.events.on_complete(lambda ctx: print("Completed"))
    """

    def __init__(self, emit_fn: Callable[[Hook, EventContext], None]) -> None:
        """Initialize events system.

        Args:
            emit_fn: Function to call when emitting events.
                    Typically the agent's _emit_event method.
        """
        from syrin.enums import Hook

        self._emit = emit_fn
        self._handlers: dict[Hook, list[Callable[[EventContext], None]]] = {
            hook: [] for hook in Hook
        }
        self._before_handlers: dict[Hook, list[Callable[[EventContext], None]]] = {
            hook: [] for hook in Hook
        }
        self._after_handlers: dict[Hook, list[Callable[[EventContext], None]]] = {
            hook: [] for hook in Hook
        }

    def on(self, hook: Hook, handler: Callable[[EventContext], None]) -> None:
        """Register a handler for a hook.

        Args:
            hook: Hook enum value (e.g., Hook.AGENT_RUN_START)
            handler: Callback function that receives EventContext

        Example:
            agent.events.on(Hook.AGENT_RUN_START, lambda ctx: print(f"Input: {ctx.input}"))
        """
        self._handlers[hook].append(handler)

    def on_all(self, handler: Callable[[Hook, EventContext], None]) -> None:
        """Register a handler for ALL hooks.

        Args:
            handler: Callback function that receives (hook_enum, EventContext)

        Example:
            def log_all(hook, ctx):
                print(f"[{hook.value}] {ctx}")
            agent.events.on_all(log_all)
        """
        for hook in self._handlers:

            def make_handler(h: Hook = hook) -> Callable[[EventContext], None]:
                def wrapper(ctx: EventContext) -> None:
                    handler(h, ctx)

                return wrapper

            self._handlers[hook].append(make_handler())

    def before(self, hook: Hook, handler: Callable[[EventContext], None]) -> None:
        """Register a BEFORE handler - runs before hook, can modify context.

        Useful for: modifying temperature, adding headers, validation, etc.

        Args:
            hook: Hook enum value
            handler: Callback that can modify the EventContext

        Example:
            def add_header(ctx):
                ctx["headers"] = {"X-Custom": "value"}
            agent.events.before(Hook.LLM_REQUEST_START, add_header)
        """
        self._before_handlers[hook].append(handler)

    def after(self, hook: Hook, handler: Callable[[EventContext], None]) -> None:
        """Register an AFTER handler - runs after hook.

        Useful for: logging, metrics, side effects

        Args:
            hook: Hook enum value
            handler: Callback for post-processing

        Example:
            def log_duration(ctx):
                print(f"Request took {ctx.duration_ms}ms")
            agent.events.after(Hook.LLM_REQUEST_END, log_duration)
        """
        self._after_handlers[hook].append(handler)

    def on_start(self, handler: Callable[[EventContext], None]) -> None:
        """Shortcut for agent.events.on(Hook.AGENT_RUN_START, handler)"""
        from syrin.enums import Hook

        self.on(Hook.AGENT_RUN_START, handler)

    def on_request(self, handler: Callable[[EventContext], None]) -> None:
        """Shortcut for agent.events.on(Hook.LLM_REQUEST_START, handler)"""
        from syrin.enums import Hook

        self.on(Hook.LLM_REQUEST_START, handler)

    def on_response(self, handler: Callable[[EventContext], None]) -> None:
        """Shortcut for agent.events.on(Hook.LLM_REQUEST_END, handler)"""
        from syrin.enums import Hook

        self.on(Hook.LLM_REQUEST_END, handler)

    def on_tool(self, handler: Callable[[EventContext], None]) -> None:
        """Shortcut for agent.events.on(Hook.TOOL_CALL_END, handler)"""
        from syrin.enums import Hook

        self.on(Hook.TOOL_CALL_END, handler)

    def on_error(self, handler: Callable[[EventContext], None]) -> None:
        """Shortcut for agent.events.on(Hook.TOOL_ERROR, handler)"""
        from syrin.enums import Hook

        self.on(Hook.TOOL_ERROR, handler)

    def on_complete(self, handler: Callable[[EventContext], None]) -> None:
        """Shortcut for agent.events.on(Hook.AGENT_RUN_END, handler)"""
        from syrin.enums import Hook

        self.on(Hook.AGENT_RUN_END, handler)

    def on_budget(self, handler: Callable[[EventContext], None]) -> None:
        """Shortcut for agent.events.on(Hook.BUDGET_CHECK, handler)"""
        from syrin.enums import Hook

        self.on(Hook.BUDGET_CHECK, handler)

    def _trigger_before(self, hook: Hook, ctx: EventContext) -> None:
        """Trigger before handlers. Internal use only."""
        for handler in self._before_handlers[hook]:
            handler(ctx)

    def _trigger_after(self, hook: Hook, ctx: EventContext) -> None:
        """Trigger after handlers. Internal use only."""
        for handler in self._after_handlers[hook]:
            handler(ctx)

    def _trigger(self, hook: Hook, ctx: EventContext) -> None:
        """Trigger event handlers. Internal use only."""
        for handler in self._handlers[hook]:
            handler(ctx)


__all__ = ["Events", "EventContext"]
