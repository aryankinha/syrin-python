"""Comprehensive test suite for Syrin Guardrails v2.0.

Test Driven Development approach - all tests written before implementation.
"""

from __future__ import annotations

import asyncio
from unittest.mock import Mock

import pytest

# =============================================================================
# TESTS FOR GUARDRAIL CONTEXT
# =============================================================================


class TestGuardrailContext:
    """Tests for the GuardrailContext dataclass."""

    def test_context_creation_minimal(self):
        """Test creating context with minimal required fields."""
        from syrin.guardrails.context import GuardrailContext

        context = GuardrailContext(text="Hello world")

        assert context.text == "Hello world"
        assert context.stage is not None
        assert context.metadata == {}
        assert context.conversation is None
        assert context.user is None
        assert context.agent is None

    def test_context_creation_full(self):
        """Test creating context with all fields."""
        from syrin.enums import GuardrailStage
        from syrin.guardrails.context import GuardrailContext

        mock_conversation = Mock()
        mock_user = Mock()
        mock_agent = Mock()
        mock_budget = Mock()
        mock_action = Mock()

        context = GuardrailContext(
            text="Transfer $500",
            stage=GuardrailStage.ACTION,
            conversation=mock_conversation,
            user=mock_user,
            agent=mock_agent,
            budget=mock_budget,
            action=mock_action,
            metadata={"request_id": "abc123"},
        )

        assert context.text == "Transfer $500"
        assert context.stage == GuardrailStage.ACTION
        assert context.conversation == mock_conversation
        assert context.user == mock_user
        assert context.agent == mock_agent
        assert context.budget == mock_budget
        assert context.action == mock_action
        assert context.metadata == {"request_id": "abc123"}

    def test_context_immutability(self):
        """Test that context is immutable (frozen dataclass)."""
        from syrin.guardrails.context import GuardrailContext

        context = GuardrailContext(text="Hello")

        # Attempting to modify should raise error
        with pytest.raises((AttributeError, TypeError)):
            context.text = "Modified"

    def test_context_copy(self):
        """Test copying context creates independent copy."""
        from syrin.guardrails.context import GuardrailContext

        original = GuardrailContext(text="Original", metadata={"key": "value"})

        copied = original.copy()

        assert copied.text == original.text
        assert copied.metadata == original.metadata
        assert copied is not original

    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        from syrin.enums import GuardrailStage
        from syrin.guardrails.context import GuardrailContext

        context = GuardrailContext(
            text="Test", stage=GuardrailStage.INPUT, metadata={"key": "value"}
        )

        result = context.to_dict()

        assert isinstance(result, dict)
        assert result["text"] == "Test"
        assert result["stage"] == "input"
        assert result["metadata"] == {"key": "value"}


# =============================================================================
# TESTS FOR GUARDRAIL DECISION
# =============================================================================


class TestGuardrailDecision:
    """Tests for the GuardrailDecision dataclass."""

    def test_decision_creation_passed(self):
        """Test creating a passed decision."""
        from syrin.enums import DecisionAction
        from syrin.guardrails.decision import GuardrailDecision

        decision = GuardrailDecision(passed=True, rule="content_check", confidence=0.95)

        assert decision.passed is True
        assert decision.rule == "content_check"
        assert decision.confidence == 0.95
        assert decision.action == DecisionAction.PASS

    def test_decision_creation_blocked(self):
        """Test creating a blocked decision."""
        from syrin.enums import DecisionAction
        from syrin.guardrails.decision import GuardrailDecision

        decision = GuardrailDecision(
            passed=False,
            rule="blocked_word",
            reason="Word 'password' is not allowed",
            confidence=1.0,
            action=DecisionAction.BLOCK,
            alternatives=["Use 'credential' instead"],
            metadata={"word": "password", "position": 8},
        )

        assert decision.passed is False
        assert decision.rule == "blocked_word"
        assert decision.reason == "Word 'password' is not allowed"
        assert decision.action == DecisionAction.BLOCK
        assert decision.alternatives == ["Use 'credential' instead"]
        assert decision.metadata["word"] == "password"

    def test_decision_default_action(self):
        """Test that default action is derived from passed status."""
        from syrin.enums import DecisionAction
        from syrin.guardrails.decision import GuardrailDecision

        pass_decision = GuardrailDecision(passed=True)
        assert pass_decision.action == DecisionAction.PASS

        block_decision = GuardrailDecision(passed=False)
        assert block_decision.action == DecisionAction.BLOCK

    def test_decision_to_dict(self):
        """Test converting decision to dictionary."""
        from syrin.guardrails.decision import GuardrailDecision

        decision = GuardrailDecision(
            passed=False, rule="test", reason="test reason", confidence=0.9
        )

        result = decision.to_dict()

        assert result["passed"] is False
        assert result["rule"] == "test"
        assert result["confidence"] == 0.9
        assert isinstance(result, dict)

    def test_decision_with_latency_and_budget(self):
        """Test decision with latency and budget tracking."""
        from syrin.guardrails.decision import GuardrailDecision

        decision = GuardrailDecision(passed=True, latency_ms=12.5, budget_consumed=0.001)

        assert decision.latency_ms == 12.5
        assert decision.budget_consumed == 0.001


# =============================================================================
# TESTS FOR BASE GUARDRAIL CLASS
# =============================================================================


class TestGuardrailBase:
    """Tests for the Guardrail abstract base class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        from syrin.guardrails.context import GuardrailContext

        return GuardrailContext(text="Test text")

    @pytest.mark.asyncio
    async def test_guardrail_must_implement_evaluate(self, mock_context):
        """Test that concrete guardrails must implement evaluate."""
        from syrin.guardrails.base import Guardrail

        class IncompleteGuardrail(Guardrail):
            pass

        with pytest.raises(TypeError):
            IncompleteGuardrail()

    @pytest.mark.asyncio
    async def test_guardrail_evaluate_returns_decision(self, mock_context):
        """Test that evaluate returns a GuardrailDecision."""
        from syrin.guardrails.base import Guardrail
        from syrin.guardrails.decision import GuardrailDecision

        class TestGuardrail(Guardrail):
            async def evaluate(self, context):
                return GuardrailDecision(passed=True)

        guardrail = TestGuardrail()
        result = await guardrail.evaluate(mock_context)

        assert isinstance(result, GuardrailDecision)
        assert result.passed is True

    def test_guardrail_name_default(self):
        """Test default name is class name."""
        from syrin.guardrails.base import Guardrail
        from syrin.guardrails.decision import GuardrailDecision

        class MyCustomGuardrail(Guardrail):
            async def evaluate(self, context):
                return GuardrailDecision(passed=True)

        guardrail = MyCustomGuardrail()
        assert guardrail.name == "MyCustomGuardrail"

    def test_guardrail_name_custom(self):
        """Test custom name can be set."""
        from syrin.guardrails.base import Guardrail
        from syrin.guardrails.decision import GuardrailDecision

        class MyGuardrail(Guardrail):
            async def evaluate(self, context):
                return GuardrailDecision(passed=True)

        guardrail = MyGuardrail(name="custom_name")
        assert guardrail.name == "custom_name"

    def test_guardrail_budget_cost_default(self):
        """Test default budget cost is 0."""
        from syrin.guardrails.base import Guardrail
        from syrin.guardrails.decision import GuardrailDecision

        class TestGuardrail(Guardrail):
            async def evaluate(self, context):
                return GuardrailDecision(passed=True)

        guardrail = TestGuardrail()
        assert guardrail.budget_cost == 0.0


# =============================================================================
# TESTS FOR CONTENT FILTER GUARDRAIL
# =============================================================================


class TestContentFilterGuardrail:
    """Tests for the ContentFilter guardrail."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        from syrin.guardrails.context import GuardrailContext

        return GuardrailContext(text="Hello world")

    @pytest.mark.asyncio
    async def test_content_filter_no_blocked_words(self, mock_context):
        """Test text without blocked words passes."""
        from syrin.guardrails.built_in.content import ContentFilter

        guardrail = ContentFilter(blocked_words=["badword"])
        mock_context = mock_context.copy()
        mock_context = mock_context.__class__(text="Hello world")

        result = await guardrail.evaluate(mock_context)

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_content_filter_blocked_word_found(self):
        """Test text with blocked word is blocked."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext

        guardrail = ContentFilter(blocked_words=["password", "secret"])
        context = GuardrailContext(text="My password is 12345")

        result = await guardrail.evaluate(context)

        assert result.passed is False
        assert "password" in result.reason.lower()
        assert result.metadata["word"] == "password"

    @pytest.mark.asyncio
    async def test_content_filter_case_insensitive(self):
        """Test blocked words are case insensitive."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext

        guardrail = ContentFilter(blocked_words=["PASSWORD"])
        context = GuardrailContext(text="My password is secret")

        result = await guardrail.evaluate(context)

        assert result.passed is False
        assert result.metadata["word"] == "password"

    @pytest.mark.asyncio
    async def test_content_filter_multiple_words(self):
        """Test blocking when multiple blocked words present."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext

        guardrail = ContentFilter(blocked_words=["bad", "worse", "terrible"])
        context = GuardrailContext(text="This is terrible and bad")

        result = await guardrail.evaluate(context)

        assert result.passed is False
        # Should find the first one
        assert result.metadata["word"] in ["bad", "terrible"]

    @pytest.mark.asyncio
    async def test_content_filter_empty_list(self):
        """Test with empty blocked words list allows everything."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext

        guardrail = ContentFilter(blocked_words=[])
        context = GuardrailContext(text="Anything goes here")

        result = await guardrail.evaluate(context)

        assert result.passed is True


# =============================================================================
# TESTS FOR PII SCANNER GUARDRAIL
# =============================================================================


class TestPIIScannerGuardrail:
    """Tests for the PIIScanner guardrail."""

    @pytest.mark.asyncio
    async def test_pii_scanner_no_pii(self):
        """Test text without PII passes."""
        from syrin.guardrails.built_in.pii import PIIScanner
        from syrin.guardrails.context import GuardrailContext

        guardrail = PIIScanner()
        context = GuardrailContext(text="Hello, how are you?")

        result = await guardrail.evaluate(context)

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_pii_scanner_email_detected(self):
        """Test email detection."""
        from syrin.guardrails.built_in.pii import PIIScanner
        from syrin.guardrails.context import GuardrailContext

        guardrail = PIIScanner()
        context = GuardrailContext(text="Contact me at john@example.com")

        result = await guardrail.evaluate(context)

        assert result.passed is False
        assert "email" in result.reason.lower()
        assert "john@example.com" in str(result.metadata)

    @pytest.mark.asyncio
    async def test_pii_scanner_phone_detected(self):
        """Test phone number detection."""
        from syrin.guardrails.built_in.pii import PIIScanner
        from syrin.guardrails.context import GuardrailContext

        guardrail = PIIScanner()
        context = GuardrailContext(text="Call me at 555-123-4567")

        result = await guardrail.evaluate(context)

        assert result.passed is False
        assert "phone" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_pii_scanner_ssn_detected(self):
        """Test SSN detection."""
        from syrin.guardrails.built_in.pii import PIIScanner
        from syrin.guardrails.context import GuardrailContext

        guardrail = PIIScanner()
        context = GuardrailContext(text="My SSN is 123-45-6789")

        result = await guardrail.evaluate(context)

        assert result.passed is False
        assert "ssn" in result.reason.lower() or "social" in result.reason.lower()


# =============================================================================
# TESTS FOR PARALLEL EVALUATION ENGINE
# =============================================================================


class TestParallelEvaluationEngine:
    """Tests for the parallel guardrail evaluation engine."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        from syrin.guardrails.context import GuardrailContext

        return GuardrailContext(text="Test")

    @pytest.fixture
    def fast_passing_guardrail(self):
        """Create a fast passing guardrail."""
        from syrin.guardrails.base import Guardrail
        from syrin.guardrails.decision import GuardrailDecision

        class FastPass(Guardrail):
            async def evaluate(self, context):
                await asyncio.sleep(0.01)  # 10ms
                return GuardrailDecision(passed=True, rule="fast_pass")

        return FastPass()

    @pytest.fixture
    def slow_passing_guardrail(self):
        """Create a slow passing guardrail."""
        from syrin.guardrails.base import Guardrail
        from syrin.guardrails.decision import GuardrailDecision

        class SlowPass(Guardrail):
            async def evaluate(self, context):
                await asyncio.sleep(0.05)  # 50ms
                return GuardrailDecision(passed=True, rule="slow_pass")

        return SlowPass()

    @pytest.fixture
    def blocking_guardrail(self):
        """Create a blocking guardrail."""
        from syrin.guardrails.base import Guardrail
        from syrin.guardrails.decision import GuardrailDecision

        class Blocker(Guardrail):
            async def evaluate(self, context):
                return GuardrailDecision(
                    passed=False, rule="always_block", reason="Blocked for testing"
                )

        return Blocker()

    @pytest.mark.asyncio
    async def test_parallel_evaluation_all_pass(self, mock_context, fast_passing_guardrail):
        """Test parallel evaluation when all guardrails pass."""
        from syrin.guardrails.engine import ParallelEvaluationEngine

        engine = ParallelEvaluationEngine()
        guardrails = [fast_passing_guardrail, fast_passing_guardrail]

        result = await engine.evaluate(mock_context, guardrails)

        assert result.passed is True
        assert len(result.decisions) == 2

    @pytest.mark.asyncio
    async def test_parallel_evaluation_one_fails(
        self, mock_context, fast_passing_guardrail, blocking_guardrail
    ):
        """Test parallel evaluation when one guardrail fails."""
        from syrin.guardrails.engine import ParallelEvaluationEngine

        engine = ParallelEvaluationEngine()
        guardrails = [fast_passing_guardrail, blocking_guardrail, fast_passing_guardrail]

        result = await engine.evaluate(mock_context, guardrails)

        assert result.passed is False
        assert len(result.decisions) == 3

        # Check that blocking decision is in results
        block_decisions = [d for d in result.decisions if not d.passed]
        assert len(block_decisions) == 1
        assert block_decisions[0].rule == "always_block"

    @pytest.mark.asyncio
    async def test_parallel_evaluation_is_actually_parallel(
        self, mock_context, slow_passing_guardrail
    ):
        """Test that guardrails run in parallel (not sequentially)."""
        import time

        from syrin.guardrails.engine import ParallelEvaluationEngine

        engine = ParallelEvaluationEngine()
        guardrails = [slow_passing_guardrail, slow_passing_guardrail, slow_passing_guardrail]

        start = time.time()
        result = await engine.evaluate(mock_context, guardrails)
        elapsed = time.time() - start

        # If sequential: ~150ms (3 * 50ms)
        # If parallel: ~50ms (max of all)
        assert elapsed < 0.15, f"Took {elapsed}s, expected < 0.15s for parallel execution"
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_parallel_evaluation_timeout(self, mock_context):
        """Test timeout handling for slow guardrails."""
        from syrin.guardrails.base import Guardrail
        from syrin.guardrails.decision import GuardrailDecision
        from syrin.guardrails.engine import ParallelEvaluationEngine

        class VerySlowGuardrail(Guardrail):
            async def evaluate(self, context):
                await asyncio.sleep(1.0)  # 1 second
                return GuardrailDecision(passed=True)

        engine = ParallelEvaluationEngine(timeout=0.1)  # 100ms timeout
        guardrails = [VerySlowGuardrail()]

        result = await engine.evaluate(mock_context, guardrails)

        # Should have timed out
        assert result.passed is False  # Timeout = fail by default
        timeout_decisions = [d for d in result.decisions if d.rule == "timeout"]
        assert len(timeout_decisions) == 1

    @pytest.mark.asyncio
    async def test_parallel_evaluation_empty_list(self, mock_context):
        """Test evaluation with empty guardrail list."""
        from syrin.guardrails.engine import ParallelEvaluationEngine

        engine = ParallelEvaluationEngine()
        result = await engine.evaluate(mock_context, [])

        assert result.passed is True
        assert len(result.decisions) == 0


# =============================================================================
# TESTS FOR BUDGET AWARENESS
# =============================================================================


class TestBudgetAwareness:
    """Tests for budget-aware guardrail operations."""

    @pytest.mark.asyncio
    async def test_guardrail_consumes_budget(self):
        """Test that guardrail evaluation consumes budget."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext

        # Mock budget
        mock_budget = Mock()
        mock_budget.remaining = 1.0
        mock_budget.consume = Mock()

        guardrail = ContentFilter(blocked_words=["test"])
        context = GuardrailContext(text="test word", budget=mock_budget)

        await guardrail.evaluate(context)

        # Budget should have been checked (even if 0 cost)
        # In real implementation, this would consume budget

    @pytest.mark.asyncio
    async def test_guardrail_fails_when_budget_exhausted(self):
        """Test that expensive guardrail fails when budget exhausted."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext

        mock_budget = Mock()
        mock_budget.remaining = 0.0  # No budget

        ContentFilter(blocked_words=["bad"])
        GuardrailContext(text="Some text", budget=mock_budget)

        # In real implementation, should check budget before evaluation
        # and fail if insufficient


# =============================================================================
# TESTS FOR GUARDRAIL CHAIN
# =============================================================================


class TestGuardrailChain:
    """Tests for the GuardrailChain class."""

    @pytest.fixture
    def mock_context(self):
        from syrin.guardrails.context import GuardrailContext

        return GuardrailContext(text="Test")

    @pytest.mark.asyncio
    async def test_chain_empty_passes(self, mock_context):
        """Test empty chain passes."""
        from syrin.guardrails.chain import GuardrailChain

        chain = GuardrailChain()
        result = await chain.evaluate(mock_context)

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_chain_stops_on_first_failure(self, mock_context):
        """Test chain stops evaluating after first failure."""
        from syrin.guardrails.base import Guardrail
        from syrin.guardrails.chain import GuardrailChain
        from syrin.guardrails.decision import GuardrailDecision

        call_count = 0

        class CountingGuardrail(Guardrail):
            def __init__(self, should_pass):
                super().__init__()
                self.should_pass = should_pass

            async def evaluate(self, context):
                nonlocal call_count
                call_count += 1
                return GuardrailDecision(passed=self.should_pass, rule=f"guardrail_{call_count}")

        chain = GuardrailChain(
            [
                CountingGuardrail(should_pass=True),
                CountingGuardrail(should_pass=False),  # This should stop the chain
                CountingGuardrail(should_pass=True),  # This should NOT be called
            ]
        )

        result = await chain.evaluate(mock_context)

        assert result.passed is False
        assert call_count == 2  # Third one should not be called
        assert result.rule == "guardrail_2"


# =============================================================================
# TESTS FOR AGENT INTEGRATION
# =============================================================================


class TestAgentIntegration:
    """Tests for guardrail integration with Agent class."""

    @pytest.mark.asyncio
    async def test_agent_with_guardrails_in_input_stage(self):
        """Test guardrails run on user input."""

        # This will test that guardrails are called during agent.run()
        # Implementation will mock the LLM call
        pass

    @pytest.mark.asyncio
    async def test_agent_with_guardrails_in_output_stage(self):
        """Test guardrails run on LLM output."""
        pass

    @pytest.mark.asyncio
    async def test_agent_with_guardrails_in_action_stage(self):
        """Test guardrails run before tool execution."""
        pass

    def test_agent_guardrail_config_validation(self):
        """Test that invalid guardrail configs raise errors."""
        pass


# =============================================================================
# TESTS FOR OBSERVABILITY & HOOKS
# =============================================================================


class TestObservability:
    """Tests for observability features."""

    @pytest.mark.asyncio
    async def test_guardrail_emits_span(self):
        """Test that guardrail evaluation creates a trace span."""
        pass

    @pytest.mark.asyncio
    async def test_guardrail_emits_hook_on_violation(self):
        """Test that blocked guardrail emits violation hook."""
        pass

    @pytest.mark.asyncio
    async def test_guardrail_emits_metrics(self):
        """Test that guardrail updates metrics."""
        pass

    def test_guardrail_decision_in_response(self):
        """Test that response includes guardrail decisions."""
        pass


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_empty_text(self):
        """Test guardrails with empty text."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext

        guardrail = ContentFilter(blocked_words=["test"])
        context = GuardrailContext(text="")

        result = await guardrail.evaluate(context)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_very_long_text(self):
        """Test guardrails with very long text."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext

        guardrail = ContentFilter(blocked_words=["badword"])
        context = GuardrailContext(text="a" * 1000000)  # 1MB text

        result = await guardrail.evaluate(context)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_unicode_text(self):
        """Test guardrails with unicode text."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext

        guardrail = ContentFilter(blocked_words=["emoji"])
        context = GuardrailContext(text="Hello 👋 World 🌍 你好世界")

        result = await guardrail.evaluate(context)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_special_characters(self):
        """Test guardrails with special regex characters."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext

        guardrail = ContentFilter(blocked_words=["test.test"])
        context = GuardrailContext(text="This has test.test in it")

        result = await guardrail.evaluate(context)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_concurrent_evaluations(self):
        """Test multiple concurrent guardrail evaluations."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext

        guardrail = ContentFilter(blocked_words=["bad"])

        # Run 100 evaluations concurrently
        contexts = [GuardrailContext(text=f"Text {i}") for i in range(100)]
        tasks = [guardrail.evaluate(ctx) for ctx in contexts]
        results = await asyncio.gather(*tasks)

        assert all(r.passed for r in results)
        assert len(results) == 100


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for the complete guardrails system."""

    @pytest.mark.asyncio
    async def test_full_guardrail_pipeline(self):
        """Test complete pipeline from input to output."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.built_in.pii import PIIScanner
        from syrin.guardrails.context import GuardrailContext
        from syrin.guardrails.engine import ParallelEvaluationEngine

        engine = ParallelEvaluationEngine()

        # Input guardrails
        input_guardrails = [
            ContentFilter(blocked_words=["blocked"]),
            PIIScanner(),
        ]

        context = GuardrailContext(text="Hello world")
        result = await engine.evaluate(context, input_guardrails)

        assert result.passed is True
        assert len(result.decisions) == 2

    @pytest.mark.asyncio
    async def test_blocked_input_stops_pipeline(self):
        """Test that blocked input stops further processing."""
        from syrin.guardrails.built_in.content import ContentFilter
        from syrin.guardrails.context import GuardrailContext
        from syrin.guardrails.engine import ParallelEvaluationEngine

        engine = ParallelEvaluationEngine()
        guardrails = [ContentFilter(blocked_words=["blocked"])]

        context = GuardrailContext(text="This is blocked content")
        result = await engine.evaluate(context, guardrails)

        assert result.passed is False
        assert "blocked" in result.reason.lower()


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
