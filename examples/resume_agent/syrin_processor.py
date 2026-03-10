"""Pipecat FrameProcessor that wraps Syrin agent as an LLM.

Receives LLMContextFrame, extracts the last user message, calls Syrin agent,
streams response as LLMTextFrame for TTS.
"""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)

# Pipecat imports (optional - only needed when running voice server)
try:
    from pipecat.frames.frames import (
        Frame,
        LLMContextFrame,
        LLMFullResponseEndFrame,
        LLMFullResponseStartFrame,
        LLMTextFrame,
    )
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

    PIPECAT_AVAILABLE = True
except ImportError:
    PIPECAT_AVAILABLE = False
    FrameProcessor = object  # type: ignore
    Frame = object
    FrameDirection = object
    LLMContextFrame = object
    LLMFullResponseEndFrame = object
    LLMFullResponseStartFrame = object
    LLMTextFrame = object


def _get_last_user_text(frame: Any) -> str | None:
    """Extract the last user message text from LLMContextFrame."""
    if not hasattr(frame, "context"):
        return None
    ctx = frame.context
    messages = (
        getattr(ctx, "get_messages", None) and ctx.get_messages() or getattr(ctx, "messages", None)
    )
    if not messages:
        return None
    for msg in reversed(messages):
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
        if role == "user" and content:
            return (
                content
                if isinstance(content, str)
                else (content[0].get("text", "") if content else "")
            )
    return None


class SyrinLLMProcessor(FrameProcessor):
    """Custom Pipecat processor: Syrin agent as LLM.

    When receiving LLMContextFrame, calls the Syrin agent and streams
    LLMTextFrame chunks for TTS.
    """

    def __init__(self, agent: Any):
        if not PIPECAT_AVAILABLE:
            raise RuntimeError(
                "Pipecat is not installed. Run: pip install 'pipecat-ai[deepgram,elevenlabs,twilio]'"
            )
        super().__init__()
        self._agent = agent

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMContextFrame):
            user_text = _get_last_user_text(frame)
            if user_text and user_text.strip():
                _log.info("Syrin processing: %s", user_text[:80])
                try:
                    await self.push_frame(LLMFullResponseStartFrame(), direction)
                    # When agent has tools, use arun() so tool calls are executed and we get
                    # the real reply. astream() does not run tools and would return the
                    # "use POST /chat for full tool execution" fallback.
                    agent_tools = getattr(self._agent, "_tools", None) or getattr(
                        self._agent, "tools", None
                    )
                    if agent_tools and len(agent_tools) > 0:
                        result = await self._agent.arun(user_text)
                        text = (result.content or "").strip()
                        if text:
                            await self.push_frame(LLMTextFrame(text=text), direction)
                    else:
                        async for chunk in self._agent.astream(user_text):
                            chunk_text = (
                                getattr(chunk, "text", None) or getattr(chunk, "content", "") or ""
                            )
                            if chunk_text:
                                await self.push_frame(LLMTextFrame(text=chunk_text), direction)
                    await self.push_frame(LLMFullResponseEndFrame(), direction)
                except Exception as e:
                    _log.exception("Syrin agent error: %s", e)
                    await self.push_frame(
                        LLMTextFrame(text="Sorry, I had a brief issue. Could you repeat that?"),
                        direction,
                    )
                    await self.push_frame(LLMFullResponseEndFrame(), direction)
            # Do not forward LLMContextFrame downstream; we produced the response
            return
        await self.push_frame(frame, direction)
