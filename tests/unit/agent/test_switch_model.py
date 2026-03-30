"""Tests for agent.switch_model(model, reason=) and the Hook.MODEL_SWITCHED lifecycle event."""

from __future__ import annotations

from syrin.enums import Hook
from syrin.model import Model


class TestModelSwitchedHookExists:
    def test_hook_enum_has_model_switched(self) -> None:
        assert hasattr(Hook, "MODEL_SWITCHED")

    def test_hook_value_is_string(self) -> None:
        assert isinstance(Hook.MODEL_SWITCHED.value, str)


class TestSwitchModelSignature:
    def test_switch_model_accepts_reason(self) -> None:
        """switch_model must accept a reason= keyword argument."""
        import inspect

        from syrin.agent import Agent

        sig = inspect.signature(Agent.switch_model)
        assert "reason" in sig.parameters

    def test_reason_has_default(self) -> None:
        import inspect

        from syrin.agent import Agent

        sig = inspect.signature(Agent.switch_model)
        param = sig.parameters["reason"]
        assert param.default == ""


class TestSwitchModelEmitsHook:
    def _make_agent(self) -> object:
        from syrin.agent import Agent
        from syrin.model import Model

        return Agent(model=Model.OpenAI("gpt-4o-mini"))

    def test_switch_model_emits_model_switched_hook(self) -> None:
        agent = self._make_agent()
        emitted: list[tuple[object, object]] = []

        from syrin.enums import Hook

        agent.events.on(Hook.MODEL_SWITCHED, lambda ctx: emitted.append((Hook.MODEL_SWITCHED, ctx)))

        new_model = Model.OpenAI("gpt-4o")
        agent.switch_model(new_model)

        assert len(emitted) == 1
        assert emitted[0][0] == Hook.MODEL_SWITCHED

    def test_hook_context_carries_from_model(self) -> None:
        agent = self._make_agent()
        contexts: list[object] = []

        from syrin.enums import Hook

        agent.events.on(Hook.MODEL_SWITCHED, lambda ctx: contexts.append(ctx))

        old_model_id = agent._model_config.model_id if agent._model_config else None
        agent.switch_model(Model.OpenAI("gpt-4o"))

        ctx = contexts[0]
        assert hasattr(ctx, "from_model")
        assert ctx.from_model == old_model_id

    def test_hook_context_carries_to_model(self) -> None:
        agent = self._make_agent()
        contexts: list[object] = []

        from syrin.enums import Hook

        agent.events.on(Hook.MODEL_SWITCHED, lambda ctx: contexts.append(ctx))
        agent.switch_model(Model.OpenAI("gpt-4o"))

        ctx = contexts[0]
        assert hasattr(ctx, "to_model")
        assert "gpt-4o" in str(ctx.to_model)

    def test_hook_context_carries_reason(self) -> None:
        agent = self._make_agent()
        contexts: list[object] = []

        from syrin.enums import Hook

        agent.events.on(Hook.MODEL_SWITCHED, lambda ctx: contexts.append(ctx))
        agent.switch_model(Model.OpenAI("gpt-4o"), reason="budget exceeded")

        ctx = contexts[0]
        assert hasattr(ctx, "reason")
        assert ctx.reason == "budget exceeded"

    def test_reason_defaults_to_empty_string_in_hook(self) -> None:
        agent = self._make_agent()
        contexts: list[object] = []

        from syrin.enums import Hook

        agent.events.on(Hook.MODEL_SWITCHED, lambda ctx: contexts.append(ctx))
        agent.switch_model(Model.OpenAI("gpt-4o"))

        ctx = contexts[0]
        assert ctx.reason == ""
