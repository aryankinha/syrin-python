"""Tests for GuardrailReport implementation.

Tests that GuardrailReport is properly populated during guardrail evaluation.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from syrin import Agent, Hook, Model
from syrin.enums import StopReason
from syrin.guardrails import Guardrail
from syrin.guardrails.decision import GuardrailDecision
from syrin.response import GuardrailReport

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def blocking_guardrail():
    """Guardrail that always blocks."""

    class AlwaysBlock(Guardrail):
        def __init__(self):
            self.name = "always_block"

        async def evaluate(self, context):
            return GuardrailDecision(
                passed=False,
                action="block",
                reason="Always blocks for testing",
            )

    return AlwaysBlock()


@pytest.fixture
def passing_guardrail():
    """Guardrail that always passes."""

    class AlwaysPass(Guardrail):
        def __init__(self):
            self.name = "always_pass"

        async def evaluate(self, context):
            return GuardrailDecision(passed=True, action="allow", reason="Always passes")

    return AlwaysPass()


# =============================================================================
# TESTS FOR GUARDRAIL REPORT
# =============================================================================


class TestGuardrailReport:
    """Tests for GuardrailReport population."""

    def test_guardrail_report_defaults(self):
        """Test GuardrailReport default values."""
        report = GuardrailReport()
        assert report.input_passed is True
        assert report.output_passed is True
        assert report.blocked is False
        assert report.blocked_stage is None
        assert report.input_guardrails == []
        assert report.output_guardrails == []
        assert report.passed is True

    def test_guardrail_report_passed_property(self):
        """Test GuardrailReport.passed property."""
        # All pass
        report = GuardrailReport(input_passed=True, output_passed=True, blocked=False)
        assert report.passed is True

        # Input blocked
        report = GuardrailReport(input_passed=False, output_passed=True, blocked=True)
        assert report.passed is False

        # Output blocked
        report = GuardrailReport(input_passed=True, output_passed=False, blocked=True)
        assert report.passed is False

    def test_input_guardrail_blocks_response(self, blocking_guardrail):
        """Test input guardrail blocks response completely."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [blocking_guardrail]

        agent = TestAgent()
        result = agent.response("Blocked input")

        assert result.stop_reason == StopReason.GUARDRAIL
        assert result.content == ""
        assert result.report.guardrail.blocked is True
        assert result.report.guardrail.blocked_stage == "input"
        assert result.report.guardrail.input_passed is False

    def test_input_guardrail_passes(self, passing_guardrail):
        """Test input guardrail passes and allows response."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail]

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Hello world",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test input")

        assert result.stop_reason == StopReason.END_TURN
        assert result.report.guardrail.input_passed is True
        assert result.report.guardrail.input_guardrails == ["always_pass"]

    def test_output_guardrail_blocks_response(self):
        """Test output guardrail blocks response."""

        # Create a guardrail that only blocks at output stage
        class OutputOnlyBlocker(Guardrail):
            def __init__(self):
                self.name = "output_blocker"

            async def evaluate(self, context):
                # Only block at output stage
                if context.stage.value == "output":
                    return GuardrailDecision(
                        passed=False,
                        action="block",
                        reason="Output blocked for testing",
                    )
                return GuardrailDecision(passed=True)

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [OutputOnlyBlocker()]

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Generated output",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test input")

        assert result.stop_reason == StopReason.GUARDRAIL
        assert result.report.guardrail.blocked is True
        assert result.report.guardrail.blocked_stage == "output"
        assert result.report.guardrail.output_passed is False


# =============================================================================
# TESTS FOR GUARDRAIL HOOKS
# =============================================================================


class TestGuardrailHooks:
    """Tests for guardrail hook emission."""

    def test_guardrail_input_hook_emitted(self, passing_guardrail):
        """Test GUARDRAIL_INPUT hook is emitted."""
        hooks_received = []

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail]

        agent = TestAgent()
        agent.events.on(Hook.GUARDRAIL_INPUT, lambda ctx: hooks_received.append(("input", ctx)))

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Hello",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            agent.response("Test input")

        assert len(hooks_received) == 1
        assert hooks_received[0][0] == "input"
        assert hooks_received[0][1].get("stage") == "input"

    def test_guardrail_output_hook_emitted(self, passing_guardrail):
        """Test GUARDRAIL_OUTPUT hook is emitted."""
        hooks_received = []

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail]

        agent = TestAgent()
        agent.events.on(Hook.GUARDRAIL_OUTPUT, lambda ctx: hooks_received.append(("output", ctx)))

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Hello",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            agent.response("Test input")

        assert len(hooks_received) == 1
        assert hooks_received[0][0] == "output"

    def test_guardrail_blocked_hook_emitted(self, blocking_guardrail):
        """Test GUARDRAIL_BLOCKED hook is emitted when blocked."""
        hooks_received = []

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [blocking_guardrail]

        agent = TestAgent()
        agent.events.on(Hook.GUARDRAIL_BLOCKED, lambda ctx: hooks_received.append(("blocked", ctx)))

        agent.response("Test input")

        assert len(hooks_received) == 1
        assert hooks_received[0][0] == "blocked"
        assert "reason" in hooks_received[0][1]
        assert hooks_received[0][1].get("stage") == "input"


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestGuardrailReportEdgeCases:
    """Edge case tests for GuardrailReport."""

    def test_guardrail_with_exception(self):
        """Test guardrail that raises exception."""

        class FailingGuardrail(Guardrail):
            def __init__(self):
                self.name = "failing"

            async def evaluate(self, context):
                raise RuntimeError("Guardrail failed!")

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [FailingGuardrail()]

        agent = TestAgent()

        # Should handle exception gracefully
        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Hello",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test input")

        # Exception should result in blocked
        assert result.stop_reason == StopReason.GUARDRAIL
        assert result.report.guardrail.blocked is True

    def test_multiple_guardrails_all_pass(self, passing_guardrail):
        """Test multiple guardrails all passing."""
        guardrail2 = Mock(spec=Guardrail)
        guardrail2.name = "second"

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail, guardrail2]

        agent = TestAgent()

        # Mock the second guardrail
        with (
            patch.object(
                agent._guardrails._guardrails[1],
                "evaluate",
                return_value=GuardrailDecision(passed=True),
            ),
            patch.object(
                agent._loop,
                "run",
                return_value=Mock(
                    content="Hello",
                    cost_usd=0.001,
                    token_usage={"input": 10, "output": 5, "total": 15},
                    tool_calls=[],
                    stop_reason="end_turn",
                    iterations=1,
                    latency_ms=100,
                ),
            ),
        ):
            result = agent.response("Test input")

        assert result.stop_reason == StopReason.END_TURN
        assert "always_pass" in result.report.guardrail.input_guardrails


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
