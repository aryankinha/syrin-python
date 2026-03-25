"""Tests for Agent routing integration."""

from __future__ import annotations

import pytest

from syrin import Agent
from syrin.enums import Media
from syrin.model import Model
from syrin.router import RoutingConfig, RoutingMode, TaskType, register_model_capabilities
from syrin.router.agent_integration import _profiles_from_models, build_router_from_models


def _almock(name: str = "test") -> Model:
    return Model.Almock(context_window=4096, latency_min=0, latency_max=0)


class TestProfilesFromModels:
    """_profiles_from_models internal helper."""

    def test_empty_list_returns_empty(self) -> None:
        assert _profiles_from_models([]) == []

    def test_single_model_creates_one_profile(self) -> None:
        m = _almock("a")
        profiles = _profiles_from_models([m])
        assert len(profiles) == 1
        assert profiles[0].model is m
        assert profiles[0].name in ("almock", "test")
        assert TaskType.GENERAL in profiles[0].strengths

    def test_multiple_models_creates_unique_names(self) -> None:
        profiles = _profiles_from_models([_almock(), _almock(), _almock()])
        names = [p.name for p in profiles]
        assert len(set(names)) == 3

    def test_custom_strengths(self) -> None:
        m = _almock()
        profiles = _profiles_from_models([m], strengths=[TaskType.CODE, TaskType.REASONING])
        assert profiles[0].strengths == [TaskType.CODE, TaskType.REASONING]

    def test_auto_detect_claude_strengths(self) -> None:
        m = Model.Anthropic("claude-sonnet-4", api_key="sk-fake")
        profiles = _profiles_from_models([m])
        assert TaskType.CODE in profiles[0].strengths
        assert TaskType.REASONING in profiles[0].strengths
        assert TaskType.PLANNING in profiles[0].strengths

    def test_auto_detect_gemini_vision_media(self) -> None:
        m = Model.Google("gemini-2.0-flash", api_key="fake")
        profiles = _profiles_from_models([m])
        from syrin.enums import Media

        assert Media.IMAGE in profiles[0].input_media
        assert Media.VIDEO in profiles[0].input_media
        assert TaskType.VISION in profiles[0].strengths

    def test_auto_detect_gpt4o_vision(self) -> None:
        m = Model.OpenAI("gpt-4o", api_key="sk-fake")
        profiles = _profiles_from_models([m])
        assert Media.IMAGE in profiles[0].input_media
        assert TaskType.VISION in profiles[0].strengths

    def test_model_strengths_override_inference(self) -> None:
        m = Model.Almock(strengths=[TaskType.CODE, TaskType.REASONING])
        profiles = _profiles_from_models([m])
        assert profiles[0].strengths == [TaskType.CODE, TaskType.REASONING]

    def test_model_input_media_override_inference(self) -> None:
        m = Model.Almock(input_media={Media.TEXT, Media.IMAGE})
        profiles = _profiles_from_models([m])
        assert profiles[0].input_media == {Media.TEXT, Media.IMAGE}

    def test_model_output_media_override_default(self) -> None:
        m = Model.Almock(output_media={Media.TEXT, Media.IMAGE})
        profiles = _profiles_from_models([m])
        assert profiles[0].output_media == {Media.TEXT, Media.IMAGE}

    def test_model_priority_and_supports_tools(self) -> None:
        m = Model.Almock(priority=90, supports_tools=False)
        profiles = _profiles_from_models([m])
        assert profiles[0].priority == 90
        assert profiles[0].supports_tools is False

    def test_model_routing_fields_with_openai_constructor(self) -> None:
        m = Model.OpenAI(
            "gpt-4o-mini",
            api_key="sk-fake",
            strengths=[TaskType.TRANSLATION],
            priority=80,
        )
        profiles = _profiles_from_models([m])
        assert profiles[0].strengths == [TaskType.TRANSLATION]
        assert profiles[0].priority == 80

    def test_register_model_capabilities_overrides_builtin(self) -> None:
        register_model_capabilities(
            "xyztest-reg",
            [TaskType.CODE, TaskType.REASONING],
            input_media={Media.TEXT, Media.IMAGE},
        )
        try:
            m = Model(provider="custom", model_id="xyztest-reg-v1")
            profiles = _profiles_from_models([m])
            assert TaskType.CODE in profiles[0].strengths
            assert TaskType.REASONING in profiles[0].strengths
            assert Media.IMAGE in profiles[0].input_media
        finally:
            from syrin.router.agent_integration import _USER_CAPABILITIES

            _USER_CAPABILITIES[:] = [
                (p, s, m) for p, s, m in _USER_CAPABILITIES if p != "xyztest-reg"
            ]


class TestBuildRouterFromModels:
    """build_router_from_models helper."""

    def test_build_without_config(self) -> None:
        models = [_almock("a"), _almock("b")]
        router = build_router_from_models(models)
        assert router is not None
        assert len(router._profiles) == 2

    def test_build_with_model_router_uses_explicit_router(self) -> None:
        explicit = build_router_from_models([_almock()])
        cfg = RoutingConfig(router=explicit)
        router = build_router_from_models([_almock(), _almock()], routing_config=cfg)
        assert router is explicit

    def test_build_with_model_router_force_model(self) -> None:
        forced = _almock("forced")
        cfg = RoutingConfig(force_model=forced)
        router = build_router_from_models([_almock()], routing_config=cfg)
        model, _, reason = router.route("hello")
        assert model is forced
        assert reason.reason == "Routing bypassed via force_model"


class TestAgentModelList:
    """Agent with model list."""

    def test_single_model_list_no_routing(self) -> None:
        agent = Agent(model=[Model.Almock()], system_prompt="Hi")
        assert agent._router is None
        r = agent.run("hello")
        assert r.content
        assert r.model

    def test_model_list_with_model_router(self) -> None:
        agent = Agent(
            model=[Model.Almock(), Model.Almock(latency_min=0, latency_max=0)],
            model_router=RoutingConfig(routing_mode=RoutingMode.COST_FIRST),
            system_prompt="Hi",
        )
        assert agent._router is not None
        r = agent.run("hello")
        assert r.content
        assert r.model

    def test_empty_model_list_raises(self) -> None:
        with pytest.raises(TypeError, match="cannot be empty"):
            Agent(model=[], system_prompt="Hi")

    def test_invalid_model_in_list_raises(self) -> None:
        with pytest.raises(TypeError, match=r"model\[0\] must be Model"):
            Agent(model=["not-a-model"], system_prompt="Hi")


class TestAgentTaskOverride:
    """Agent task_type override in response/arun."""

    def test_task_override_passed_to_router(self) -> None:
        from syrin.router.router import ModelRouter

        code_m = Model.Almock(profile_name="code", strengths=[TaskType.CODE])
        general_m = Model.Almock(profile_name="general", strengths=[TaskType.GENERAL])
        models_list = [code_m, general_m]
        router = ModelRouter(models=models_list)
        agent = Agent(
            model=models_list,
            model_router=RoutingConfig(router=router),
            system_prompt="Hi",
        )
        r = agent.run("hello", task_type=TaskType.CODE)
        assert r.content
        assert r.task_type == TaskType.CODE
        assert r.routing_reason is not None
        assert r.routing_reason.selected_model == "code"


class TestAgentResponseRoutingMetadata:
    """Response routing metadata."""

    def test_response_has_routing_reason_when_routing(self) -> None:
        agent = Agent(
            model=[Model.Almock(), Model.Almock()],
            model_router=RoutingConfig(routing_mode=RoutingMode.COST_FIRST),
            system_prompt="Hi",
        )
        r = agent.run("hello")
        assert r.routing_reason is not None
        assert r.routing_reason.task_type is not None
        assert r.model_used is not None
