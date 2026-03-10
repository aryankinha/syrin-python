"""Tests for VoiceGenerationProvider, VoiceGenerator, and generate_voice tool."""

from __future__ import annotations

import base64
from typing import Any

import pytest

from syrin.agent._helpers import _make_generate_voice_tool
from syrin.enums import Hook
from syrin.generation import VoiceGenerator, register_voice_provider
from syrin.generation._result import GenerationResult


class MockVoiceProvider:
    """Mock voice provider for tests. No external deps."""

    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str = "default",
        model: str = "mock",
        **kwargs: Any,
    ) -> None:
        self.voice_id = voice_id
        self.model = model

    def generate(
        self,
        text: str,
        *,
        voice_id: str = "default",
        speed: float = 1.0,
        language: str = "en",
        **kwargs: Any,
    ) -> GenerationResult:
        if not text:
            return GenerationResult(success=False, error="Empty text")
        fake_audio = b"\x00\x01\x02"
        b64 = base64.b64encode(fake_audio).decode("ascii")
        return GenerationResult(
            success=True,
            url=f"data:audio/mpeg;base64,{b64}",
            content_type="audio/mpeg",
            content_bytes=fake_audio,
            metadata={"cost_usd": 0.001, "model_name": self.model},
        )

    async def generate_async(
        self,
        text: str,
        *,
        voice_id: str = "default",
        speed: float = 1.0,
        language: str = "en",
        **kwargs: Any,
    ) -> GenerationResult:
        return self.generate(text, voice_id=voice_id, speed=speed, language=language, **kwargs)


def _setup_mock_voice_provider() -> None:
    register_voice_provider("mock", MockVoiceProvider)


def _teardown_mock_voice_provider() -> None:
    from syrin.generation._registry import _VOICE_PROVIDERS

    _VOICE_PROVIDERS.pop("mock", None)


class TestVoiceGeneratorStaticConstructors:
    """VoiceGenerator.OpenAI(), .ElevenLabs(), etc."""

    def test_openai_static_constructor(self) -> None:
        """VoiceGenerator.OpenAI returns VoiceGenerator with OpenAI provider."""
        gen = VoiceGenerator.OpenAI(api_key="test-key")
        assert gen.voice_model == "tts-1"
        assert gen.provider is not None

    def test_elevenlabs_static_constructor(self) -> None:
        """VoiceGenerator.ElevenLabs returns VoiceGenerator."""
        gen = VoiceGenerator.ElevenLabs(api_key="test-key")
        assert gen.voice_model == "eleven_flash_v2_5"
        assert gen.provider is not None

    def test_from_provider_mock(self) -> None:
        """VoiceGenerator.from_provider with registered mock."""
        _setup_mock_voice_provider()
        try:
            gen = VoiceGenerator.from_provider("mock", api_key="x")
            assert gen.voice_model == "default"
            result = gen.generate("Hello")
            assert result.success
            assert "data:audio" in result.url
        finally:
            _teardown_mock_voice_provider()

    def test_unregistered_provider_raises(self) -> None:
        """VoiceGenerator.UnknownProvider raises AttributeError."""
        with pytest.raises(AttributeError, match="UnknownProvider"):
            VoiceGenerator.UnknownProvider(api_key="x")  # type: ignore[attr-defined]


class TestVoiceGeneratorGenerate:
    """VoiceGenerator.generate() with mock provider."""

    def test_generate_returns_result(self) -> None:
        """generate() returns GenerationResult."""
        _setup_mock_voice_provider()
        try:
            gen = VoiceGenerator.from_provider("mock")
            result = gen.generate("Hello world")
            assert result.success
            assert result.url.startswith("data:audio")
            assert result.content_bytes == b"\x00\x01\x02"
        finally:
            _teardown_mock_voice_provider()

    def test_generate_emits_hooks(self) -> None:
        """generate(emit=...) emits START and END hooks."""
        _setup_mock_voice_provider()
        try:
            gen = VoiceGenerator.from_provider("mock")
            events: list[tuple[str, dict[str, object]]] = []

            def capture(h: str, ctx: dict[str, object]) -> None:
                events.append((h, ctx))

            gen.generate("Hi", emit=capture)
            assert len(events) >= 2
            hooks = [e[0] for e in events]
            assert Hook.GENERATION_VOICE_START.value in hooks
            assert Hook.GENERATION_VOICE_END.value in hooks
        finally:
            _teardown_mock_voice_provider()

    def test_generate_empty_text_fails(self) -> None:
        """generate('') returns error result."""
        _setup_mock_voice_provider()
        try:
            gen = VoiceGenerator.from_provider("mock")
            result = gen.generate("")
            assert not result.success
            assert "Empty" in result.error or "empty" in result.error.lower()
        finally:
            _teardown_mock_voice_provider()


class TestGenerateVoiceTool:
    """_make_generate_voice_tool and tool execution."""

    def test_tool_with_generator_returns_url(self) -> None:
        """Tool with configured generator returns data URL."""
        _setup_mock_voice_provider()
        try:
            gen = VoiceGenerator.from_provider("mock")
            tool = _make_generate_voice_tool(
                get_generator=lambda: gen,
                emit=None,
            )
            out = tool.func(text="Hello")
            assert "data:audio" in out
            assert "Generated audio" in out
        finally:
            _teardown_mock_voice_provider()

    def test_tool_with_no_generator_returns_error(self) -> None:
        """Tool with get_generator returning None returns helpful error."""
        tool = _make_generate_voice_tool(get_generator=lambda: None, emit=None)
        out = tool.func(text="Hello")
        assert "not available" in out or "Voice generation" in out
        assert "data:audio" not in out

    def test_tool_schema_has_required_text(self) -> None:
        """Tool schema requires 'text' parameter."""
        tool = _make_generate_voice_tool(get_generator=lambda: None, emit=None)
        assert "required" in tool.parameters_schema
        assert "text" in tool.parameters_schema["required"]
        assert tool.name == "generate_voice"
