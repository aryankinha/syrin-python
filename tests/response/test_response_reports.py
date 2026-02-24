"""Tests for Response Reports - OutputReport, ContextReport, CheckpointReport.

Tests that these reports are properly populated during agent execution.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from syrin import Agent, Model
from syrin.response import CheckpointReport, ContextReport, OutputReport, TokenReport

# =============================================================================
# TESTS FOR OUTPUT REPORT
# =============================================================================


class TestOutputReport:
    """Tests for OutputReport population."""

    def test_output_validation_tracked(self):
        """Test that output validation is tracked in report."""
        from pydantic import BaseModel

        class OutputModel(BaseModel):
            result: str

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini", output=OutputModel)

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content='{"result": "success"}',
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test")

        # Output report should be populated
        assert result.report.output.validated is True
        assert result.report.output.attempts >= 1
        assert result.report.output.is_valid is True
        assert result.report.output.final_error is None

    def test_output_validation_failure_tracked(self):
        """Test that output validation failure is tracked."""
        from pydantic import BaseModel

        class OutputModel(BaseModel):
            result: str

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini", output=OutputModel)

        agent = TestAgent()

        # Return invalid JSON
        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="not valid json",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test")

        # Output report should show failure
        assert result.report.output.validated is True
        assert result.report.output.attempts > 0
        assert result.report.output.is_valid is False
        assert result.report.output.final_error is not None

    def test_no_output_validation_without_output_type(self):
        """Test that output report is not populated when no output type."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Simple response",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test")

        # Output report should have defaults
        assert result.report.output.validated is False
        assert result.report.output.attempts == 0


# =============================================================================
# EDGE CASE TESTS FOR OUTPUT REPORT
# =============================================================================


class TestOutputReportEdgeCases:
    """Edge case tests for OutputReport."""

    def test_output_report_empty_content(self):
        """Test OutputReport with empty content."""
        report = OutputReport()
        assert report.validated is False
        assert report.attempts == 0
        assert report.is_valid is True
        assert report.final_error is None

    def test_output_report_max_retries_exceeded(self):
        """Test OutputReport when max retries are exceeded."""
        from pydantic import BaseModel

        class OutputModel(BaseModel):
            result: str

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini", output=OutputModel)

        agent = TestAgent()

        # Return invalid JSON that will fail all retries
        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="not valid json",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test")

        # Should show validation attempts were made
        assert result.report.output.validated is True
        assert result.report.output.attempts > 0
        assert result.report.output.is_valid is False
        assert result.report.output.final_error is not None

    def test_output_report_nested_model(self):
        """Test OutputReport with nested Pydantic models."""
        from pydantic import BaseModel

        class Address(BaseModel):
            city: str
            country: str

        class Person(BaseModel):
            name: str
            address: Address

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini", output=Person)

        agent = TestAgent()

        # Return valid nested JSON
        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content='{"name": "John", "address": {"city": "NYC", "country": "USA"}}',
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test")

        assert result.report.output.validated is True
        assert result.report.output.is_valid is True
        assert result.report.output.final_error is None

    def test_output_report_unicode_content(self):
        """Test OutputReport with unicode content."""
        from pydantic import BaseModel

        class OutputModel(BaseModel):
            message: str

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini", output=OutputModel)

        agent = TestAgent()

        # Return unicode JSON
        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content='{"message": "Hello 👋 World 🌍 你好"}',
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test")

        assert result.report.output.validated is True
        assert result.report.output.is_valid is True

    def test_output_report_special_characters(self):
        """Test OutputReport with special characters in JSON."""
        from pydantic import BaseModel

        class OutputModel(BaseModel):
            code: str

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini", output=OutputModel)

        agent = TestAgent()

        # Return JSON with special characters
        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content='{"code": "console.log(\\"Hello\\nWorld\\")"}',
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test")

        assert result.report.output.validated is True


# =============================================================================
# TESTS FOR CONTEXT REPORT
# =============================================================================


class TestContextReport:
    """Tests for ContextReport."""

    def test_context_report_defaults(self):
        """Test ContextReport default values."""
        report = ContextReport()
        assert report.initial_tokens == 0
        assert report.final_tokens == 0
        assert report.max_tokens == 0
        assert report.compressions == 0
        assert report.offloads == 0

    def test_context_report_exists_in_response(self):
        """Test that ContextReport exists in agent response."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Response",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test")

        assert hasattr(result.report, "context")
        assert isinstance(result.report.context, ContextReport)


# =============================================================================
# EDGE CASE TESTS FOR CONTEXT REPORT
# =============================================================================


class TestContextReportEdgeCases:
    """Edge case tests for ContextReport."""

    def test_context_report_compression_tracking(self):
        """Test ContextReport compression tracking."""
        report = ContextReport(compressions=5, initial_tokens=1000, final_tokens=500)
        assert report.compressions == 5
        assert report.initial_tokens == 1000
        assert report.final_tokens == 500
        assert report.initial_tokens > report.final_tokens

    def test_context_report_offload_tracking(self):
        """Test ContextReport offload tracking."""
        report = ContextReport(offloads=3)
        assert report.offloads == 3

    def test_context_report_token_growth(self):
        """Test ContextReport with token growth."""
        # Tokens can grow if context expands
        report = ContextReport(initial_tokens=100, final_tokens=500)
        assert report.final_tokens > report.initial_tokens


# =============================================================================
# TESTS FOR CHECKPOINT REPORT
# =============================================================================


class TestCheckpointReport:
    """Tests for CheckpointReport."""

    def test_checkpoint_report_defaults(self):
        """Test CheckpointReport default values."""
        report = CheckpointReport()
        assert report.saves == 0
        assert report.loads == 0

    def test_checkpoint_report_exists_in_response(self):
        """Test that CheckpointReport exists in agent response."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Response",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test")

        assert hasattr(result.report, "checkpoints")
        assert isinstance(result.report.checkpoints, CheckpointReport)


# =============================================================================
# EDGE CASE TESTS FOR CHECKPOINT REPORT
# =============================================================================


class TestCheckpointReportEdgeCases:
    """Edge case tests for CheckpointReport."""

    def test_checkpoint_report_multiple_operations(self):
        """Test CheckpointReport with multiple save/load operations."""
        report = CheckpointReport(saves=10, loads=5)
        assert report.saves == 10
        assert report.loads == 5

    def test_checkpoint_report_more_loads_than_saves(self):
        """Test CheckpointReport when loads exceed saves."""
        # This is valid - could load from previous runs
        report = CheckpointReport(saves=3, loads=10)
        assert report.loads > report.saves


# =============================================================================
# TESTS FOR TOKEN REPORT
# =============================================================================


class TestTokenReport:
    """Tests for TokenReport."""

    def test_token_report_defaults(self):
        """Test TokenReport default values."""
        report = TokenReport()
        assert report.input_tokens == 0
        assert report.output_tokens == 0
        assert report.total_tokens == 0
        assert report.cost_usd == 0.0

    def test_token_report_populated_in_response(self):
        """Test that TokenReport is populated in agent response."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Response",
                cost_usd=0.05,
                token_usage={"input": 100, "output": 50, "total": 150},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test")

        assert result.report.tokens.input_tokens == 100
        assert result.report.tokens.output_tokens == 50
        assert result.report.tokens.total_tokens == 150
        assert result.report.tokens.cost_usd == 0.05


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
