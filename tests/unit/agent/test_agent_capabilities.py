"""Tests for Agent capabilities: output_media → generation tools, FILE + input_file_rules."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from syrin import Agent, Model
from syrin.capabilities import InputFileRules
from syrin.enums import Media


def _mock_image_provider() -> MagicMock:
    """Minimal mock ImageGenerationProvider for tests."""
    from syrin.generation._result import GenerationResult

    prov = MagicMock()
    prov.generate.return_value = [
        GenerationResult(success=True, url="mock://test-image"),
    ]
    return prov


def _mock_video_provider() -> MagicMock:
    """Minimal mock VideoGenerationProvider for tests."""
    from syrin.generation._result import GenerationResult

    prov = MagicMock()
    prov.generate.return_value = GenerationResult(success=True, url="mock://test-video")
    return prov


def _mock_voice_provider() -> MagicMock:
    """Minimal mock VoiceGenerationProvider for tests."""
    from syrin.generation._result import GenerationResult

    prov = MagicMock()
    prov.generate.return_value = GenerationResult(success=True, url="data:audio/mpeg;base64,x")
    return prov


class TestAgentImageVideoGenerationParams:
    """image_generation and video_generation as separate explicit params on Agent."""

    def test_image_generation_explicit_adds_tool_without_output_media_image(self) -> None:
        """image_generation provided → generate_image tool added even when output_media lacks IMAGE."""
        from syrin.generation import ImageGenerator

        gen = ImageGenerator(provider=_mock_image_provider())
        agent = Agent(
            model=Model.Almock(),
            system_prompt="Hi",
            output_media={Media.TEXT},
            image_generation=gen,
        )
        assert agent._image_generator is gen
        assert "generate_image" in {t.name for t in agent._tools}

    def test_video_generation_explicit_adds_tool_without_output_media_video(self) -> None:
        """video_generation provided → generate_video tool added even when output_media lacks VIDEO."""
        from syrin.generation import VideoGenerator

        gen = VideoGenerator(provider=_mock_video_provider())
        agent = Agent(
            model=Model.Almock(),
            system_prompt="Hi",
            output_media={Media.TEXT},
            video_generation=gen,
        )
        assert agent._video_generator is gen
        assert "generate_video" in {t.name for t in agent._tools}

    def test_image_generation_explicit_overrides_default_when_output_media_has_image(
        self,
    ) -> None:
        """output_media has IMAGE + image_generation provided → uses provided, not default."""
        from syrin.generation import ImageGenerator

        gen = ImageGenerator(provider=_mock_image_provider())
        with patch.dict(os.environ, {"GEMINI_API_KEY": "x", "GOOGLE_API_KEY": "x"}, clear=False):
            agent = Agent(
                model=Model.Almock(),
                system_prompt="Hi",
                output_media={Media.TEXT, Media.IMAGE},
                image_generation=gen,
            )
        assert agent._image_generator is gen

    def test_both_image_and_video_generation_explicit(self) -> None:
        """Both image_generation and video_generation provided → both tools added."""
        from syrin.generation import ImageGenerator, VideoGenerator

        img_gen = ImageGenerator(provider=_mock_image_provider())
        vid_gen = VideoGenerator(provider=_mock_video_provider())
        agent = Agent(
            model=Model.Almock(),
            system_prompt="Hi",
            image_generation=img_gen,
            video_generation=vid_gen,
        )
        assert agent._image_generator is img_gen
        assert agent._video_generator is vid_gen
        assert "generate_image" in {t.name for t in agent._tools}
        assert "generate_video" in {t.name for t in agent._tools}

    def test_image_generation_invalid_type_raises(self) -> None:
        """image_generation with wrong type → TypeError."""
        with pytest.raises(TypeError, match="image_generation must be ImageGenerator"):
            Agent(
                model=Model.Almock(),
                system_prompt="Hi",
                image_generation="not_a_generator",
            )

    def test_video_generation_invalid_type_raises(self) -> None:
        """video_generation with wrong type → TypeError."""
        with pytest.raises(TypeError, match="video_generation must be VideoGenerator"):
            Agent(
                model=Model.Almock(),
                system_prompt="Hi",
                video_generation=123,
            )

    def test_voice_generation_explicit_adds_tool(self) -> None:
        """voice_generation provided → generate_voice tool added."""
        from syrin.generation import VoiceGenerator

        prov = _mock_voice_provider()
        gen = VoiceGenerator(provider=prov)
        agent = Agent(
            model=Model.Almock(),
            system_prompt="Hi",
            voice_generation=gen,
        )
        assert agent._voice_generator is gen
        assert "generate_voice" in {t.name for t in agent._tools}

    def test_voice_generation_invalid_type_raises(self) -> None:
        """voice_generation with wrong type → TypeError."""
        with pytest.raises(TypeError, match="voice_generation must be VoiceGenerator"):
            Agent(
                model=Model.Almock(),
                system_prompt="Hi",
                voice_generation="not_a_generator",
            )


class TestAgentOutputMediaGenerationTools:
    """output_media with IMAGE/VIDEO always wires generation tools; tool returns message if API key missing."""

    def test_output_media_default_text_only_no_generators(self) -> None:
        """Default output_media={TEXT} → no image/video generators or tools."""
        agent = Agent(model=Model.Almock(), system_prompt="Hi")
        assert agent._output_media == {Media.TEXT}
        assert agent._image_generator is None
        assert agent._video_generator is None
        tool_names = {t.name for t in agent._tools}
        assert "generate_image" not in tool_names
        assert "generate_video" not in tool_names

    def test_output_media_image_adds_generate_image_tool_when_key_set(self) -> None:
        """output_media={TEXT, IMAGE} → generate_image tool always added; returns message if no API key."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}, clear=False):
            agent = Agent(
                model=Model.Almock(),
                system_prompt="Hi",
                output_media={Media.TEXT, Media.IMAGE},
            )
            assert Media.IMAGE in agent._output_media
            assert "generate_image" in {t.name for t in agent._tools}
            # When generator is None, _execute_tool returns helpful message (lazy init also sees no key)
            result = agent._execute_tool("generate_image", {"prompt": "x", "aspect_ratio": "1:1"})
        assert (
            "Image generation" in result or "GOOGLE_API_KEY" in result or "not available" in result
        )

    def test_output_media_video_adds_generate_video_tool_when_key_set(self) -> None:
        """output_media={TEXT, VIDEO} → generate_video tool always added; returns message if no API key."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}, clear=False):
            agent = Agent(
                model=Model.Almock(),
                system_prompt="Hi",
                output_media={Media.TEXT, Media.VIDEO},
            )
            assert Media.VIDEO in agent._output_media
            assert "generate_video" in {t.name for t in agent._tools}
            result = agent._execute_tool("generate_video", {"prompt": "x", "aspect_ratio": "16:9"})
        assert (
            "Video generation" in result or "GOOGLE_API_KEY" in result or "not available" in result
        )


class TestAgentInputFileRules:
    """Media.FILE in input_media requires input_file_rules."""

    def test_file_in_input_media_without_rules_raises(self) -> None:
        """input_media containing FILE and no input_file_rules → ValueError."""
        with pytest.raises(ValueError, match="input_file_rules"):
            Agent(
                model=Model.Almock(),
                system_prompt="Hi",
                input_media={Media.TEXT, Media.FILE},
            )

    def test_file_in_input_media_with_empty_allowed_raises(self) -> None:
        """input_media containing FILE and input_file_rules with empty allowed_mime_types → ValueError."""
        with pytest.raises(ValueError, match="non-empty allowed_mime_types"):
            Agent(
                model=Model.Almock(),
                system_prompt="Hi",
                input_media={Media.TEXT, Media.FILE},
                input_file_rules=InputFileRules(allowed_mime_types=[], max_size_mb=5.0),
            )

    def test_file_in_input_media_with_rules_ok(self) -> None:
        """input_media={TEXT, FILE} and valid InputFileRules → OK."""
        agent = Agent(
            model=Model.Almock(),
            system_prompt="Hi",
            input_media={Media.TEXT, Media.FILE},
            input_file_rules=InputFileRules(
                allowed_mime_types=["application/pdf", "image/png"],
                max_size_mb=10.0,
            ),
        )
        assert Media.FILE in agent._input_media
        assert agent._input_file_rules is not None
        assert agent._input_file_rules.allowed_mime_types == ["application/pdf", "image/png"]
        assert agent._input_file_rules.max_size_mb == 10.0


class TestAgentDiscovery:
    """Capabilities are discoverable via _input_media, _output_media, _input_file_rules."""

    def test_input_output_media_stored(self) -> None:
        """Agent stores resolved input_media and output_media."""
        agent = Agent(
            model=Model.Almock(),
            system_prompt="Hi",
            input_media={Media.TEXT, Media.IMAGE},
            output_media={Media.TEXT, Media.IMAGE},
        )
        assert agent._input_media == {Media.TEXT, Media.IMAGE}
        assert agent._output_media == {Media.TEXT, Media.IMAGE}

    def test_input_file_rules_stored(self) -> None:
        """Agent stores input_file_rules when FILE in input_media."""
        rules = InputFileRules(allowed_mime_types=["application/pdf"], max_size_mb=5.0)
        agent = Agent(
            model=Model.Almock(),
            system_prompt="Hi",
            input_media={Media.TEXT, Media.FILE},
            input_file_rules=rules,
        )
        assert agent._input_file_rules is rules
