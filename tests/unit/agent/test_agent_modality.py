"""Tests for Agent input_media/output_media validation at construction."""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.enums import Media
from syrin.exceptions import ModalityNotSupportedError
from syrin.router import ModelRouter, RoutingConfig, TaskType


class TestAgentMediaValidation:
    """Media validation when using router with input_media/output_media."""

    def test_agent_single_model_no_router_no_media_validation(self) -> None:
        """Single model, no router → no media validation; input/output_media stored."""
        agent = Agent(
            model=Model.Almock(),
            system_prompt="Hi",
            input_media={Media.TEXT, Media.IMAGE},
            output_media={Media.IMAGE},
        )
        assert agent._router is None
        assert agent._input_media == {Media.TEXT, Media.IMAGE}
        assert agent._output_media == {Media.IMAGE}

    def test_agent_router_profiles_cover_text_input(self) -> None:
        """Router with profiles supporting TEXT → OK when input_media={TEXT}."""
        m = Model.Almock(
            profile_name="general",
            strengths=[TaskType.GENERAL],
            input_media={Media.TEXT},
            output_media={Media.TEXT},
        )
        models_list = [m]
        router = ModelRouter(models=models_list)
        agent = Agent(
            model=[m],
            system_prompt="Hi",
            model_router=RoutingConfig(router=router),
            input_media={Media.TEXT},
        )
        assert agent._router is not None

    def test_agent_router_profiles_cover_image_input(self) -> None:
        """Router with IMAGE-capable profile → input_media={TEXT,IMAGE} OK."""
        m = Model.Almock(
            profile_name="vision",
            strengths=[TaskType.VISION],
            input_media={Media.TEXT, Media.IMAGE},
            output_media={Media.TEXT},
        )
        models_list = [m]
        router = ModelRouter(models=models_list)
        agent = Agent(
            model=[m],
            system_prompt="Hi",
            model_router=RoutingConfig(router=router),
            input_media={Media.TEXT, Media.IMAGE},
        )
        assert agent._router is not None

    def test_agent_input_media_not_supported_raises(self) -> None:
        """input_media={IMAGE} but no profile supports IMAGE → ModalityNotSupportedError."""
        m = Model.Almock(
            profile_name="text-only",
            strengths=[TaskType.GENERAL],
            input_media={Media.TEXT},
            output_media={Media.TEXT},
        )
        models_list = [m]
        router = ModelRouter(models=models_list)
        with pytest.raises(ModalityNotSupportedError, match="image"):
            Agent(
                model=[m],
                system_prompt="Hi",
                model_router=RoutingConfig(router=router),
                input_media={Media.IMAGE},
            )

    def test_agent_output_media_not_supported_raises(self) -> None:
        """output_media={IMAGE} but no profile supports IMAGE output → ModalityNotSupportedError."""
        m = Model.Almock(
            profile_name="text-only",
            strengths=[TaskType.GENERAL],
            input_media={Media.TEXT},
            output_media={Media.TEXT},
        )
        models_list = [m]
        router = ModelRouter(models=models_list)
        with pytest.raises(ModalityNotSupportedError, match="image"):
            Agent(
                model=[m],
                system_prompt="Hi",
                model_router=RoutingConfig(router=router),
                output_media={Media.IMAGE},
            )

    def test_agent_media_validation_derived_from_profiles(self) -> None:
        """No input/output_media → default TEXT; capabilities derived at route time."""
        m = Model.Almock(
            profile_name="general",
            strengths=[TaskType.GENERAL],
            input_media={Media.TEXT},
            output_media={Media.TEXT},
        )
        models_list = [m]
        router = ModelRouter(models=models_list)
        agent = Agent(
            model=[m],
            system_prompt="Hi",
            model_router=RoutingConfig(router=router),
        )
        assert agent._router is not None
        assert agent._input_media == {Media.TEXT}
        assert agent._output_media == {Media.TEXT}

    def test_agent_optional_input_media_none_uses_default(self) -> None:
        """input_media=None → default {Media.TEXT}."""
        m = Model.Almock(
            profile_name="general",
            strengths=[TaskType.GENERAL],
            input_media={Media.TEXT},
            output_media={Media.TEXT},
        )
        models_list = [m]
        router = ModelRouter(models=models_list)
        agent = Agent(
            model=[m],
            system_prompt="Hi",
            model_router=RoutingConfig(router=router),
            input_media=None,
        )
        assert agent._router is not None
        assert agent._input_media == {Media.TEXT}


class TestAgentMultimodalInput:
    """Tests for agent.response accepting MultimodalInput (str | list[dict])."""

    def test_agent_response_accepts_str(self) -> None:
        """agent.response accepts str input (existing behavior)."""
        agent = Agent(model=Model.Almock(), system_prompt="Hi")
        r = agent.response("Hello")
        assert r.content is not None
        assert isinstance(r.content, str)

    def test_agent_response_accepts_multimodal_content_parts(self) -> None:
        """agent.response accepts list[dict] (content parts) as MultimodalInput."""
        agent = Agent(model=Model.Almock(), system_prompt="Hi")
        content_parts: list[dict[str, object]] = [
            {"type": "text", "text": "What is in this image?"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw"}},
        ]
        r = agent.response(content_parts)
        assert r.content is not None
