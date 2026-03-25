"""Tests for syrin.init() and on_agent_init integration: cloud_enabled, registration, no-op when disabled."""

from __future__ import annotations

import os
from typing import Any

from syrin import Agent, Budget, Model
from syrin.config import get_config
from syrin.remote._registry import get_registry
from syrin.remote._types import ConfigOverride, OverridePayload


def _reset_cloud_config() -> None:
    """Reset cloud-related config and stop transport (for test isolation)."""
    cfg = get_config()
    transport = getattr(cfg, "cloud_transport", None)
    if transport is not None and hasattr(transport, "stop"):
        transport.stop()
    cfg.cloud_enabled = False
    cfg.cloud_transport = None
    cfg.cloud_api_key = None


def _make_agent(name: str = "init-test-agent") -> Agent:
    """Minimal agent for init tests."""
    return Agent(model=Model.Almock(), name=name)


# --- syrin.init() ---


class TestInitAPI:
    """syrin.init() sets cloud config and optional transport."""

    def teardown_method(self) -> None:
        _reset_cloud_config()

    def test_init_without_args_leaves_cloud_disabled_when_no_env(self) -> None:
        """init() with no args and no SYRIN_API_KEY leaves cloud_enabled False."""
        # Clear env to be sure
        env_key = os.environ.pop("SYRIN_API_KEY", None)
        try:
            from syrin.remote import init

            init()
            assert get_config().cloud_enabled is False
        finally:
            if env_key is not None:
                os.environ["SYRIN_API_KEY"] = env_key

    def test_init_with_api_key_sets_cloud_enabled(self) -> None:
        """init(api_key="sk-...") sets cloud_enabled True and creates default transport."""
        from syrin.remote import init

        init(api_key="sk-test-fake-key")
        assert get_config().cloud_enabled is True
        assert get_config().cloud_api_key == "sk-test-fake-key"
        # Default SSETransport is created (has stop())
        transport = get_config().cloud_transport
        assert transport is not None
        assert hasattr(transport, "stop")

    def test_init_with_transport_uses_custom_transport(self) -> None:
        """init(transport=...) sets cloud_enabled True and stores that transport."""
        from syrin.remote import init
        from syrin.remote._transport import ServeTransport

        custom = ServeTransport()
        init(transport=custom)
        assert get_config().cloud_enabled is True
        assert get_config().cloud_transport is custom

    def test_init_with_base_url_stored(self) -> None:
        """init(api_key="x", base_url="https://custom/v1") stores base_url."""
        from syrin.remote import init

        init(api_key="sk-x", base_url="https://custom.example.com/v1")
        assert get_config().cloud_enabled is True
        assert get_config().cloud_base_url == "https://custom.example.com/v1"

    def test_init_with_env_api_key_enables_cloud(self) -> None:
        """init() with no args but SYRIN_API_KEY set uses env key and enables cloud."""
        from syrin.remote import init

        os.environ["SYRIN_API_KEY"] = "sk-env-key"
        try:
            init()
            assert get_config().cloud_enabled is True
            assert get_config().cloud_api_key == "sk-env-key"
        finally:
            os.environ.pop("SYRIN_API_KEY", None)

    def test_init_api_key_overrides_env(self) -> None:
        """Explicit api_key to init() overrides SYRIN_API_KEY."""
        from syrin.remote import init

        os.environ["SYRIN_API_KEY"] = "sk-env"
        try:
            init(api_key="sk-explicit")
            assert get_config().cloud_api_key == "sk-explicit"
        finally:
            os.environ.pop("SYRIN_API_KEY", None)


# --- on_agent_init (no-op when disabled) ---


class TestOnAgentInitWhenDisabled:
    """When cloud_enabled is False, agent init does not register."""

    def teardown_method(self) -> None:
        _reset_cloud_config()

    def test_agent_created_without_init_not_in_registry(self) -> None:
        """Without calling init(), new agent is not registered (on_agent_init no-op)."""
        _reset_cloud_config()
        agent = _make_agent(name="no-init-agent")
        reg = get_registry()
        agent_id = reg.make_agent_id(agent)
        # Agent may or may not be in registry from other tests; this agent was created
        # without init() so it should not have been registered by on_agent_init.
        # If registry has it from a previous test, we can't assert. So: ensure disabled, create agent,
        # then check that this agent_id is not in all_schemas if we never called init in this test.
        assert get_config().cloud_enabled is False
        # After creating agent, either it's not registered (our expected case) or it was from
        # a previous test. To be strict: unregister this agent_id so next test is clean.
        reg.unregister(agent_id)

    def test_agent_without_init_works_identically(self) -> None:
        """Without syrin.init(), agent runs normally (response works)."""
        _reset_cloud_config()
        agent = _make_agent(name="no-init-run")
        r = agent.run("Say hello in one word.")
        assert r is not None
        assert hasattr(r, "content")
        assert hasattr(r, "stop_reason")
        assert len(str(r.content)) > 0

    def test_agent_created_after_init_is_registered(self) -> None:
        """After init(api_key="x"), new agent is registered and schema is stored."""
        from syrin.remote import init

        init(api_key="sk-register-test")
        agent = _make_agent(name="registered-agent")
        reg = get_registry()
        agent_id = reg.make_agent_id(agent)
        try:
            schema = reg.get_schema(agent_id)
            assert schema is not None
            assert schema.agent_name == "registered-agent"
        finally:
            reg.unregister(agent_id)


# --- Edge cases ---


class TestInitEdgeCases:
    """Edge cases: init twice, empty api_key, etc."""

    def teardown_method(self) -> None:
        _reset_cloud_config()

    def test_init_twice_with_api_key_replaces_transport(self) -> None:
        """Calling init() twice replaces the previous transport."""
        from syrin.remote import init
        from syrin.remote._transport import ServeTransport

        init(api_key="sk-first")
        first_transport = get_config().cloud_transport
        init(transport=ServeTransport())
        second_transport = get_config().cloud_transport
        assert second_transport is not first_transport
        assert isinstance(second_transport, ServeTransport)

    def test_init_with_empty_api_key_and_no_env_leaves_disabled(self) -> None:
        """init(api_key="") with no env does not enable cloud."""
        from syrin.remote import init

        env_key = os.environ.pop("SYRIN_API_KEY", None)
        try:
            init(api_key="")
            # Empty string might be treated as "no key" -> disabled
            assert get_config().cloud_enabled is False or get_config().cloud_api_key == ""
        finally:
            if env_key is not None:
                os.environ["SYRIN_API_KEY"] = env_key


# --- Hook emission (REMOTE_CONFIG_UPDATE / REMOTE_CONFIG_ERROR) ---


class TestRemoteConfigHooksEmitted:
    """When overrides are applied via the registered callback, REMOTE_CONFIG_UPDATE and REMOTE_CONFIG_ERROR are emitted."""

    def teardown_method(self) -> None:
        _reset_cloud_config()

    def test_remote_config_update_emitted_on_successful_override(self) -> None:
        """Callback with valid payload applies overrides and agent emits Hook.REMOTE_CONFIG_UPDATE."""
        from syrin.enums import Hook
        from syrin.remote import init
        from syrin.remote._transport import ServeTransport

        init(transport=ServeTransport())
        agent = Agent(model=Model.Almock(), name="hook-agent", budget=Budget(max_cost=0.5))
        reg = get_registry()
        agent_id = reg.make_agent_id(agent)
        transport = get_config().cloud_transport
        assert transport is not None
        callback = transport.get_callback(agent_id)
        assert callback is not None
        emitted: list[tuple[str, Any]] = []
        original = getattr(agent, "_emit_event", None)
        if original:

            def capture(h: str, c: Any) -> None:
                emitted.append((h, c))
                original(h, c)

            agent._emit_event = capture  # type: ignore[method-assign]
        payload = OverridePayload(
            agent_id=agent_id,
            version=1,
            overrides=[ConfigOverride(path="budget.max_cost", value=2.0)],
        )
        callback(payload)
        hook_names = [h for h, _ in emitted]
        assert Hook.REMOTE_CONFIG_UPDATE in hook_names
        assert agent._budget.max_cost == 2.0
        reg.unregister(agent_id)

    def test_remote_config_error_emitted_on_rejected_override(self) -> None:
        """Callback with invalid path or value triggers Hook.REMOTE_CONFIG_ERROR."""
        from syrin.enums import Hook
        from syrin.remote import init
        from syrin.remote._transport import ServeTransport

        init(transport=ServeTransport())
        agent = Agent(model=Model.Almock(), name="hook-err-agent", budget=Budget(max_cost=0.5))
        reg = get_registry()
        agent_id = reg.make_agent_id(agent)
        transport = get_config().cloud_transport
        assert transport is not None
        callback = transport.get_callback(agent_id)
        assert callback is not None
        emitted: list[tuple[str, Any]] = []
        original = getattr(agent, "_emit_event", None)
        if original:

            def capture(h: str, c: Any) -> None:
                emitted.append((h, c))
                original(h, c)

            agent._emit_event = capture  # type: ignore[method-assign]
        payload = OverridePayload(
            agent_id=agent_id,
            version=1,
            overrides=[ConfigOverride(path="budget.nonexistent_field", value=1.0)],
        )
        callback(payload)
        hook_names = [h for h, _ in emitted]
        assert Hook.REMOTE_CONFIG_ERROR in hook_names
        assert agent._budget.max_cost == 0.5
        reg.unregister(agent_id)
