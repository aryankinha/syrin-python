"""Base class for voice generation providers (Template Method pattern).

Subclasses implement _get_api_key_env(), _get_package_name(), _synthesize().
The base handles: key validation, result building, error handling, async wrapping.
"""

from __future__ import annotations

import asyncio
import base64
from abc import ABC, abstractmethod

from syrin.cost import calculate_voice_cost
from syrin.generation._result import GenerationResult


class BaseVoiceProvider(ABC):
    """Base class for TTS providers. Implements the Template Method pattern.

    Subclasses must implement:
        _get_api_key_env: Return the env var name for the API key (e.g. "OPENAI_API_KEY").
        _get_package_name: Return the pip install hint (e.g. "syrin[openai]").
        _synthesize: Perform the actual API call and return (audio_bytes, model_id, mime_type).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "",
        **kwargs: object,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._kwargs = kwargs

    @abstractmethod
    def _get_api_key_env(self) -> str:
        """Return the environment variable name for the API key."""
        ...

    @abstractmethod
    def _get_package_name(self) -> str:
        """Return the pip install hint for missing dependencies."""
        ...

    @abstractmethod
    def _synthesize(
        self,
        text: str,
        *,
        api_key: str,
        voice_id: str,
        speed: float,
        language: str,
        output_format: str,
        model_id: str,
        **kwargs: object,
    ) -> tuple[bytes, str, str]:
        """Perform the actual TTS API call.

        Args:
            text: Text to speak.
            api_key: Validated API key.
            voice_id: Resolved voice identifier.
            speed: Speech rate.
            language: Language code.
            output_format: Desired output format (mp3, wav, etc.).
            model_id: Resolved model identifier.
            **kwargs: Provider-specific options.

        Returns:
            Tuple of (audio_bytes, model_id_for_cost, mime_type).

        Raises:
            ImportError: If provider SDK not installed.
            Exception: On API errors.
        """
        ...

    def _resolve_api_key(self) -> str | None:
        """Resolve API key from instance or environment."""
        import os

        key = self.api_key or os.environ.get(self._get_api_key_env())
        if key and str(key).strip():
            return key
        return None

    def generate(
        self,
        text: str,
        *,
        voice_id: str = "default",
        speed: float = 1.0,
        language: str = "en",
        output_format: str = "mp3",
        **kwargs: object,
    ) -> GenerationResult:
        """Generate speech audio from text.

        Args:
            text: Text to speak.
            voice_id: Voice identifier (provider-specific). "default" uses provider default.
            speed: Speech rate (0.5–2.0).
            language: Language code (e.g. "en", "hi").
            output_format: Audio format (mp3, wav, pcm, opus).
            **kwargs: Provider-specific options.

        Returns:
            GenerationResult with audio data or error.
        """
        key = self._resolve_api_key()
        if not key:
            env_var = self._get_api_key_env()
            return GenerationResult(
                success=False,
                error=f"TTS requires {env_var} or api_key=.",
            )

        model_id = kwargs.pop("model", None) or self.model

        try:
            audio_bytes, cost_model, mime = self._synthesize(
                text,
                api_key=key,
                voice_id=voice_id,
                speed=speed,
                language=language,
                output_format=output_format,
                model_id=model_id,  # type: ignore[arg-type]
                **kwargs,
            )
        except ImportError as e:
            pkg = self._get_package_name()
            return GenerationResult(
                success=False,
                error=f"Missing dependency. pip install {pkg}. {e!s}",
            )
        except Exception as e:
            return GenerationResult(success=False, error=str(e))

        if not audio_bytes:
            return GenerationResult(success=False, error="No audio in response")

        b64 = base64.b64encode(audio_bytes).decode("ascii")
        url = f"data:{mime};base64,{b64}"
        cost_usd = calculate_voice_cost(cost_model, len(text))

        return GenerationResult(
            success=True,
            url=url,
            content_type=mime,
            content_bytes=audio_bytes,
            metadata={"cost_usd": cost_usd, "model_name": model_id},
        )

    async def _asynthesize(
        self,
        text: str,
        *,
        api_key: str,
        voice_id: str,
        speed: float,
        language: str,
        output_format: str,
        model_id: str,
        **kwargs: object,
    ) -> tuple[bytes, str, str] | None:
        """Optional native async synthesis. Override in providers with async SDKs.

        Returns:
            Same as _synthesize(), or None to fall back to threaded sync.
        """
        return None

    async def generate_async(
        self,
        text: str,
        *,
        voice_id: str = "default",
        speed: float = 1.0,
        language: str = "en",
        output_format: str = "mp3",
        **kwargs: object,
    ) -> GenerationResult:
        """Async variant — uses native async if provider supports it, else threads."""
        key = self._resolve_api_key()
        if not key:
            env_var = self._get_api_key_env()
            return GenerationResult(
                success=False,
                error=f"TTS requires {env_var} or api_key=.",
            )

        model_id = kwargs.pop("model", None) or self.model

        try:
            result = await self._asynthesize(
                text,
                api_key=key,
                voice_id=voice_id,
                speed=speed,
                language=language,
                output_format=output_format,
                model_id=model_id,  # type: ignore[arg-type]
                **kwargs,
            )
            if result is not None:
                audio_bytes, cost_model, mime = result
            else:
                # Fall back to threaded sync
                audio_bytes, cost_model, mime = await asyncio.to_thread(
                    self._synthesize,
                    text,
                    api_key=key,
                    voice_id=voice_id,
                    speed=speed,
                    language=language,
                    output_format=output_format,
                    model_id=model_id,  # type: ignore[arg-type]
                    **kwargs,
                )
        except ImportError as e:
            pkg = self._get_package_name()
            return GenerationResult(
                success=False,
                error=f"Missing dependency. pip install {pkg}. {e!s}",
            )
        except Exception as e:
            return GenerationResult(success=False, error=str(e))

        if not audio_bytes:
            return GenerationResult(success=False, error="No audio in response")

        b64 = base64.b64encode(audio_bytes).decode("ascii")
        url = f"data:{mime};base64,{b64}"
        cost_usd = calculate_voice_cost(cost_model, len(text))

        return GenerationResult(
            success=True,
            url=url,
            content_type=mime,
            content_bytes=audio_bytes,
            metadata={"cost_usd": cost_usd, "model_name": model_id},
        )
