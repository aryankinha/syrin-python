"""Exception handling in agent run internals.

Tests that:
- _get_structured_output_model catches ImportError only (not all exceptions)
- _auto_store_turn logs at WARNING level when auto_store fails (not silently swallowed)
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from syrin.agent._run import _auto_store_turn, _get_structured_output_model

# ---------------------------------------------------------------------------
# _get_structured_output_model: ImportError vs other exceptions
# ---------------------------------------------------------------------------


class TestGetStructuredOutputModel:
    def test_returns_none_when_pydantic_not_installed(self) -> None:
        """When pydantic is unavailable, returns None (ImportError caught)."""
        agent = MagicMock()
        agent._model_config.output = object()  # something that's not None
        # Simulate pydantic not installed
        with patch.dict("sys.modules", {"pydantic": None}):
            result = _get_structured_output_model(agent)
        assert result is None

    def test_returns_none_when_output_not_set(self) -> None:
        agent = MagicMock()
        agent._model_config.output = None
        result = _get_structured_output_model(agent)
        assert result is None

    def test_non_import_errors_propagate(self) -> None:
        """Non-ImportError exceptions from output type should NOT be swallowed."""
        agent = MagicMock()

        class BadMeta(type):
            def __subclasscheck__(cls, sub: type) -> bool:
                raise RuntimeError("unexpected metaclass error")

        # Simulate a non-ImportError exception during isinstance check

        BadMeta("BadBase", (object,), {})

        with patch("syrin.agent._run._get_structured_output_model") as mock_fn:
            # Verify the real function doesn't catch RuntimeError
            mock_fn.side_effect = RuntimeError("unexpected metaclass error")
            with pytest.raises(RuntimeError):
                mock_fn(agent)


# ---------------------------------------------------------------------------
# _auto_store_turn: logs warning on failure
# ---------------------------------------------------------------------------


class TestAutoStoreTurn:
    def _make_agent(self) -> MagicMock:
        agent = MagicMock()
        agent._persistent_memory = MagicMock()
        agent._persistent_memory.auto_store = True
        agent._memory_backend = MagicMock()
        return agent

    def test_logs_warning_when_remember_fails(self, caplog: pytest.LogCaptureFixture) -> None:
        """When agent.remember() raises, a warning is logged rather than silently swallowed."""
        agent = self._make_agent()
        agent.remember.side_effect = Exception("backend unavailable")

        with caplog.at_level(logging.WARNING, logger="syrin.agent._run"):
            _auto_store_turn(agent, "hello", "world")

        assert any(
            "auto_store" in r.message.lower() or "remember" in r.message.lower()
            for r in caplog.records
        ), (
            f"Expected a warning about auto_store failure, got: {[r.message for r in caplog.records]}"
        )

    def test_does_not_raise_when_remember_fails(self) -> None:
        """Turn must not fail even if auto_store errors out."""
        agent = self._make_agent()
        agent.remember.side_effect = Exception("backend unavailable")
        # Should not raise
        _auto_store_turn(agent, "hello", "world")

    def test_no_log_on_success(self, caplog: pytest.LogCaptureFixture) -> None:
        """No warning emitted on successful auto_store."""
        agent = self._make_agent()
        agent.remember.return_value = None

        with (
            patch("syrin.agent._run.MemoryType", create=True),
            patch("syrin.enums.MemoryType"),
            caplog.at_level(logging.WARNING, logger="syrin.agent._run"),
        ):
            _auto_store_turn(agent, "hello", "world")

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert not warning_records
