"""Tests for _verification: _call_model timeout (1E)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from syrin.knowledge._verification import _call_model


class TestCallModelTimeout:
    """Timeout behavior of _call_model (1E)."""

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_string(self) -> None:
        """When model takes longer than timeout, return empty string (fallback)."""
        model = MagicMock()

        async def slow_complete(*args: object, **kwargs: object) -> object:
            await asyncio.sleep(60)
            return MagicMock(content="SUPPORTED")

        model.acomplete = AsyncMock(side_effect=slow_complete)
        out = await _call_model(model, "test", timeout=0.1)
        assert out == ""

    @pytest.mark.asyncio
    async def test_success_within_timeout(self) -> None:
        """Normal completion within timeout returns content."""
        model = MagicMock()
        model.acomplete = AsyncMock(return_value=MagicMock(content="SUPPORTED"))
        out = await _call_model(model, "test", timeout=30.0)
        assert out == "SUPPORTED"

    @pytest.mark.asyncio
    async def test_custom_timeout(self) -> None:
        """Custom timeout value is respected."""
        model = MagicMock()

        async def slow(*args: object, **kwargs: object) -> object:
            await asyncio.sleep(10)
            return MagicMock(content="ok")

        model.acomplete = AsyncMock(side_effect=slow)
        out = await _call_model(model, "test", timeout=0.05)
        assert out == ""
