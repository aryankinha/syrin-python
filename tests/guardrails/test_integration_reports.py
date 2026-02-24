"""Tests for Guardrail Integration with Agent - Reports & Hooks.

Tests the new features:
- Class-level guardrail inheritance
- Guardrail hooks emission (GUARDRAIL_INPUT, GUARDRAIL_OUTPUT, GUARDRAIL_BLOCKED)
- AgentReport and sub-reports (GuardrailReport, TokenReport, etc.)
- Guardrail evaluation in _run_loop_response
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from syrin import Agent, Hook, Model
from syrin.enums import StopReason
from syrin.guardrails import Guardrail
from syrin.guardrails.decision import GuardrailDecision
from syrin.response import (
    AgentReport,
    BudgetStatus,
    CheckpointReport,
    ContextReport,
    GuardrailReport,
    MemoryReport,
    OutputReport,
    RateLimitReport,
    TokenReport,
)

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


@pytest.fixture
def content_guardrail():
    """Guardrail that blocks specific content."""

    class ContentBlocker(Guardrail):
        def __init__(self, blocked_words):
            self.blocked_words = [w.lower() for w in blocked_words]
            self.name = "content_blocker"

        async def evaluate(self, context):
            text = context.text.lower()
            for word in self.blocked_words:
                if word in text:
                    return GuardrailDecision(
                        passed=False,
                        action="block",
                        reason=f"Blocked word: {word}",
                    )
            return GuardrailDecision(passed=True, action="allow", reason="Clean")

    return ContentBlocker


# =============================================================================
# TESTS FOR CLASS-LEVEL GUARDRAIL INHERITANCE
# =============================================================================


class TestGuardrailClassInheritance:
    """Tests for class-level guardrail attribute inheritance."""

    def test_guardrail_set_at_class_level(self):
        """Test that guardrails defined on class are used."""
        guardrail = Mock(spec=Guardrail)
        guardrail.name = "test_guardrail"

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [guardrail]

        agent = TestAgent()
        assert len(agent._guardrails) == 1
        guardrails_list = list(agent._guardrails)
        assert guardrails_list[0].name == "test_guardrail"

    def test_guardrail_inheritance_in_subclass(self):
        """Test that subclasses inherit parent guardrails."""
        guardrail1 = Mock(spec=Guardrail)
        guardrail1.name = "parent_guardrail"

        class ParentAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [guardrail1]

        class ChildAgent(ParentAgent):
            pass

        child = ChildAgent()
        assert len(child._guardrails) == 1
        guardrails_list = list(child._guardrails)
        assert guardrails_list[0].name == "parent_guardrail"

    def test_guardrail_override_in_subclass(self):
        """Test that subclasses can override parent guardrails."""
        guardrail1 = Mock(spec=Guardrail)
        guardrail1.name = "parent"
        guardrail2 = Mock(spec=Guardrail)
        guardrail2.name = "child"

        class ParentAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [guardrail1]

        class ChildAgent(ParentAgent):
            guardrails = [guardrail2]

        child = ChildAgent()
        # Guardrails are merged, so we get both
        assert len(child._guardrails) == 2
        guardrails_list = list(child._guardrails)
        names = [g.name for g in guardrails_list]
        assert "parent" in names
        assert "child" in names

    def test_guardrail_instance_override_class(self):
        """Test that instance-level guardrails override class-level."""
        class_guardrail = Mock(spec=Guardrail)
        class_guardrail.name = "class_guardrail"
        instance_guardrail = Mock(spec=Guardrail)
        instance_guardrail.name = "instance_guardrail"

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [class_guardrail]

        agent = TestAgent(guardrails=[instance_guardrail])
        # Instance guardrails override class-level
        assert len(agent._guardrails) == 1
        guardrails_list = list(agent._guardrails)
        assert guardrails_list[0].name == "instance_guardrail"

    def test_empty_guardrails_list(self):
        """Test that empty guardrails list works."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = []

        agent = TestAgent()
        assert len(agent._guardrails) == 0

    def test_no_guardrails_attribute(self):
        """Test agent without guardrails attribute."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")

        agent = TestAgent()
        assert len(agent._guardrails) == 0


# =============================================================================
# TESTS FOR AGENT REPORT CLASSES
# =============================================================================


class TestAgentReport:
    """Tests for AgentReport and sub-report classes."""

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

    def test_token_report_defaults(self):
        """Test TokenReport default values."""
        report = TokenReport()
        assert report.input_tokens == 0
        assert report.output_tokens == 0
        assert report.total_tokens == 0
        assert report.cost_usd == 0.0

    def test_context_report_defaults(self):
        """Test ContextReport default values."""
        report = ContextReport()
        assert report.initial_tokens == 0
        assert report.final_tokens == 0
        assert report.max_tokens == 0
        assert report.compressions == 0
        assert report.offloads == 0

    def test_memory_report_defaults(self):
        """Test MemoryReport default values."""
        report = MemoryReport()
        assert report.recalls == 0
        assert report.stores == 0
        assert report.forgets == 0
        assert report.consolidated == 0

    def test_output_report_defaults(self):
        """Test OutputReport default values."""
        report = OutputReport()
        assert report.validated is False
        assert report.attempts == 0
        assert report.is_valid is True
        assert report.final_error is None

    def test_rate_limit_report_defaults(self):
        """Test RateLimitReport default values."""
        report = RateLimitReport()
        assert report.checks == 0
        assert report.throttles == 0
        assert report.exceeded is False

    def test_checkpoint_report_defaults(self):
        """Test CheckpointReport default values."""
        report = CheckpointReport()
        assert report.saves == 0
        assert report.loads == 0

    def test_agent_report_defaults(self):
        """Test AgentReport default values."""
        report = AgentReport()
        assert isinstance(report.guardrail, GuardrailReport)
        assert isinstance(report.context, ContextReport)
        assert isinstance(report.memory, MemoryReport)
        assert isinstance(report.tokens, TokenReport)
        assert isinstance(report.output, OutputReport)
        assert isinstance(report.ratelimits, RateLimitReport)
        assert isinstance(report.checkpoints, CheckpointReport)
        assert report.budget_remaining is None
        assert report.budget_used is None

    def test_agent_report_budget_property(self):
        """Test AgentReport.budget property."""
        report = AgentReport(budget_remaining=5.0, budget_used=3.0)
        budget = report.budget
        assert isinstance(budget, BudgetStatus)
        assert budget.remaining == 5.0
        assert budget.used == 3.0
        assert budget.total == 8.0
        assert budget.cost == 3.0

    def test_agent_report_budget_property_with_none(self):
        """Test AgentReport.budget property with None values."""
        report = AgentReport()
        budget = report.budget
        assert budget.remaining is None
        assert budget.used == 0.0
        assert budget.total is None


# =============================================================================
# TESTS FOR GUARDRAIL HOOKS EMISSION
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

    def test_no_hooks_when_no_guardrails(self):
        """Test no hooks emitted when agent has no guardrails."""
        hooks_received = []

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")

        agent = TestAgent()
        agent.events.on(Hook.GUARDRAIL_INPUT, lambda ctx: hooks_received.append(ctx))
        agent.events.on(Hook.GUARDRAIL_OUTPUT, lambda ctx: hooks_received.append(ctx))

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

        assert len(hooks_received) == 0


# =============================================================================
# TESTS FOR GUARDRAIL EVALUATION IN RESPONSE
# =============================================================================


class TestGuardrailInResponse:
    """Tests for guardrail evaluation during response()."""

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
                from syrin.guardrails.decision import GuardrailDecision

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

    def test_output_guardrail_not_checked_with_tool_calls(self, blocking_guardrail):
        """Test output guardrail not checked when response has tool calls."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [blocking_guardrail]

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[{"name": "test_tool", "arguments": {}}],
                stop_reason="tool_call",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test input")

        # Should not be blocked because output guardrail wasn't checked
        assert result.report.guardrail.output_passed is True

    def test_report_reset_between_calls(self, passing_guardrail):
        """Test report is reset between response() calls."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail]

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Response 1",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result1 = agent.response("First input")

        # Reset mock for second call
        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Response 2",
                cost_usd=0.002,
                token_usage={"input": 20, "output": 10, "total": 30},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=200,
            ),
        ):
            result2 = agent.response("Second input")

        # Each report should have its own data
        assert result1.report.tokens.input_tokens == 10
        assert result2.report.tokens.input_tokens == 20


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestGuardrailEdgeCases:
    """Edge case tests for guardrail integration."""

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

    def test_multiple_guardrails_one_blocks(self, passing_guardrail, blocking_guardrail):
        """Test multiple guardrails where one blocks."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail, blocking_guardrail]

        agent = TestAgent()
        result = agent.response("Test input")

        assert result.stop_reason == StopReason.GUARDRAIL
        assert result.report.guardrail.blocked is True
        # Both guardrails should be listed even though one blocked
        assert len(result.report.guardrail.input_guardrails) == 2

    def test_empty_response_content(self, passing_guardrail):
        """Test guardrail with empty response content."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail]

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="",
                cost_usd=0.001,
                token_usage={"input": 10, "output": 0, "total": 10},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test input")

        # Output guardrail should still be checked even with empty content
        assert result.report.guardrail.output_passed is True

    def test_very_long_input(self, passing_guardrail):
        """Test guardrail with very long input."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail]

        agent = TestAgent()

        long_input = "x" * 10000

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Hello",
                cost_usd=0.001,
                token_usage={"input": 10000, "output": 5, "total": 10005},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response(long_input)

        assert result.report.guardrail.input_passed is True

    def test_special_characters_in_input(self, passing_guardrail):
        """Test guardrail with special characters."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail]

        agent = TestAgent()

        special_input = "<script>alert('xss')</script> \"quoted\" 'single' \n\t"

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Safe",
                cost_usd=0.001,
                token_usage={"input": 50, "output": 5, "total": 55},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response(special_input)

        assert result.report.guardrail.input_passed is True

    def test_unicode_in_input(self, passing_guardrail):
        """Test guardrail with unicode characters."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail]

        agent = TestAgent()

        unicode_input = "Hello 👋 World 🌍 你好世界 Привет мир"

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Unicode response 👍",
                cost_usd=0.001,
                token_usage={"input": 30, "output": 20, "total": 50},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response(unicode_input)

        assert result.report.guardrail.input_passed is True
        assert result.report.guardrail.output_passed is True


# =============================================================================
# REPORT DATA ACCURACY TESTS
# =============================================================================


class TestReportDataAccuracy:
    """Tests to verify report data is accurate."""

    def test_token_report_populated_correctly(self, passing_guardrail):
        """Test token report has correct data from response."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail]

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Hello",
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

    def test_budget_report_populated_correctly(self, passing_guardrail):
        """Test budget report has correct data."""
        from syrin import Budget

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail]
            budget = Budget(run=10.0)

        agent = TestAgent()

        with patch.object(
            agent._loop,
            "run",
            return_value=Mock(
                content="Hello",
                cost_usd=0.05,
                token_usage={"input": 10, "output": 5, "total": 15},
                tool_calls=[],
                stop_reason="end_turn",
                iterations=1,
                latency_ms=100,
            ),
        ):
            result = agent.response("Test")

        # Budget should be updated after the call
        assert result.budget_used is not None
        assert result.report.budget_used is not None

    def test_report_available_on_agent(self, passing_guardrail):
        """Test agent.report property returns current report."""

        class TestAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            guardrails = [passing_guardrail]

        agent = TestAgent()

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
            agent.response("Test")

        # After response, agent.report should have data
        assert isinstance(agent.report, AgentReport)
        assert agent.report.guardrail.input_passed is True


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
