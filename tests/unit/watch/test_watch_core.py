"""Tests for the Watchable mixin, WatchProtocol, TriggerEvent, and the
agent.watch() / agent.trigger() / agent.watch_handler() API."""

from __future__ import annotations

import asyncio

import pytest

# ─── TriggerEvent ─────────────────────────────────────────────────────────────


class TestTriggerEvent:
    def test_trigger_event_importable(self) -> None:
        from syrin.watch import TriggerEvent

        assert TriggerEvent is not None

    def test_trigger_event_fields(self) -> None:
        from syrin.watch import TriggerEvent

        e = TriggerEvent(input="hello", source="cron", metadata={}, trigger_id="abc")
        assert e.input == "hello"
        assert e.source == "cron"
        assert e.metadata == {}
        assert e.trigger_id == "abc"

    def test_trigger_event_auto_trigger_id(self) -> None:
        """trigger_id has a default (UUID)."""
        from syrin.watch import TriggerEvent

        e = TriggerEvent(input="hello", source="cron")
        assert e.trigger_id  # not empty
        assert len(e.trigger_id) > 0

    def test_trigger_event_default_metadata(self) -> None:
        from syrin.watch import TriggerEvent

        e = TriggerEvent(input="x", source="test")
        assert isinstance(e.metadata, dict)


# ─── WatchProtocol ────────────────────────────────────────────────────────────


class TestWatchProtocol:
    def test_watch_protocol_importable(self) -> None:
        from syrin.watch import WatchProtocol

        assert WatchProtocol is not None

    def test_watch_protocol_has_start_and_stop(self) -> None:

        from syrin.watch import WatchProtocol

        assert hasattr(WatchProtocol, "start")
        assert hasattr(WatchProtocol, "stop")


# ─── Watchable mixin ──────────────────────────────────────────────────────────


class TestWatchableMixin:
    def test_watchable_importable(self) -> None:
        from syrin.watch import Watchable

        assert Watchable is not None

    def test_agent_is_watchable(self) -> None:
        from syrin.agent import Agent
        from syrin.watch import Watchable

        assert issubclass(Agent, Watchable)

    def test_watchable_has_watch_method(self) -> None:
        from syrin.watch import Watchable

        assert hasattr(Watchable, "watch")

    def test_watchable_has_trigger_method(self) -> None:
        from syrin.watch import Watchable

        assert hasattr(Watchable, "trigger")

    def test_watchable_has_watch_handler_method(self) -> None:
        from syrin.watch import Watchable

        assert hasattr(Watchable, "watch_handler")


# ─── agent.watch() ────────────────────────────────────────────────────────────


class TestAgentWatch:
    def test_watch_raises_on_both_protocol_and_protocols(self) -> None:
        from syrin.agent import Agent
        from syrin.model import Model

        class DummyProtocol:
            async def start(self, handler: object) -> None:
                pass

            async def stop(self) -> None:
                pass

        agent = Agent(model=Model.OpenAI("gpt-4o-mini"))
        p = DummyProtocol()
        with pytest.raises(ValueError, match="mutually exclusive"):
            agent.watch(protocol=p, protocols=[p])

    def test_watch_stores_protocols(self) -> None:
        from syrin.agent import Agent
        from syrin.model import Model

        class DummyProtocol:
            async def start(self, handler: object) -> None:
                pass

            async def stop(self) -> None:
                pass

        agent = Agent(model=Model.OpenAI("gpt-4o-mini"))
        p = DummyProtocol()
        agent.watch(protocol=p)
        assert len(agent._watch_protocols) == 1


# ─── agent.trigger() ──────────────────────────────────────────────────────────


class TestAgentTrigger:
    @pytest.mark.asyncio
    async def test_trigger_is_async(self) -> None:
        from syrin.watch import Watchable

        assert asyncio.iscoroutinefunction(Watchable.trigger)

    def test_trigger_signature(self) -> None:
        import inspect

        from syrin.watch import Watchable

        sig = inspect.signature(Watchable.trigger)
        assert "input" in sig.parameters
        assert "source" in sig.parameters
        assert "metadata" in sig.parameters


# ─── agent.watch_handler() ────────────────────────────────────────────────────


class TestWatchHandler:
    def test_watch_handler_is_callable(self) -> None:
        from syrin.agent import Agent
        from syrin.model import Model

        agent = Agent(model=Model.OpenAI("gpt-4o-mini"))
        handler = agent.watch_handler()
        assert callable(handler)

    def test_watch_handler_returns_coroutine_function(self) -> None:
        from syrin.agent import Agent
        from syrin.model import Model

        agent = Agent(model=Model.OpenAI("gpt-4o-mini"))
        handler = agent.watch_handler()
        assert asyncio.iscoroutinefunction(handler)


# ─── Hook enum values ─────────────────────────────────────────────────────────


class TestWatchHooks:
    def test_watch_trigger_hook_exists(self) -> None:
        from syrin.enums import Hook

        assert hasattr(Hook, "WATCH_TRIGGER")
        assert isinstance(Hook.WATCH_TRIGGER.value, str)

    def test_watch_error_hook_exists(self) -> None:
        from syrin.enums import Hook

        assert hasattr(Hook, "WATCH_ERROR")
        assert isinstance(Hook.WATCH_ERROR.value, str)
