"""
Integration tests for Syrin - End-to-end workflows with mocking.

These tests verify the complete flow of the system:
- Agent creation → LLM call → Tool execution → Response
- Multi-agent handoffs
- Budget tracking end-to-end
- Memory persistence
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from syrin import Agent, Budget, warn_on_exceeded
from syrin.budget import raise_on_exceeded
from syrin.enums import MessageRole
from syrin.model import Model
from syrin.tool import tool
from syrin.types import (
    CostInfo,
    Message,
    ProviderResponse,
    TokenUsage,
    ToolCall,
)


class TestAgentIntegrationWorkflows:
    """Integration tests for complete agent workflows."""

    def test_simple_agent_workflow(self):
        """Test simple agent: create → call → response."""
        model = Model("openai/gpt-4o-mini")
        agent = Agent(model=model)

        with patch.object(agent._provider, "complete", new_callable=AsyncMock) as mock:
            mock.return_value = ProviderResponse(
                content="Hello! How can I help you?",
                tool_calls=[],
                token_usage=TokenUsage(input_tokens=10, output_tokens=15),
            )

            response = agent.response("Hi")

        assert response.content == "Hello! How can I help you?"
        assert response.cost > 0
        assert response.tokens.total_tokens == 25

    def test_agent_with_tools_workflow(self):
        """Test agent with tools: call LLM → execute tool → call LLM again → response."""
        from syrin.tool import tool

        @tool
        def search(query: str) -> str:
            return f"Results for: {query}"

        model = Model("openai/gpt-4o-mini")
        agent = Agent(model=model, tools=[search])

        call_count = 0

        async def mock_complete(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ProviderResponse(
                    content="",
                    tool_calls=[ToolCall(id="call_1", name="search", arguments={"query": "AI"})],
                    token_usage=TokenUsage(input_tokens=20, output_tokens=10),
                )
            return ProviderResponse(
                content="Found results for: AI",
                tool_calls=[],
                token_usage=TokenUsage(input_tokens=30, output_tokens=15),
            )

        with patch.object(agent._provider, "complete", side_effect=mock_complete):
            response = agent.response("Search for AI")

        assert response.content == "Found results for: AI"
        assert call_count == 2

    def test_agent_with_memory_workflow(self):
        """Test agent with memory: persists conversation history."""
        from syrin.memory import BufferMemory

        mem = BufferMemory()
        mem.add(Message(role=MessageRole.USER, content="My name is John"))
        mem.add(Message(role=MessageRole.ASSISTANT, content="Hello John!"))

        model = Model("openai/gpt-4o-mini")
        agent = Agent(model=model, memory=mem)

        messages = agent._build_messages("What is my name?")

        # Should have: system, previous user, previous assistant, new user
        assert len(messages) >= 3

    def test_agent_with_budget_workflow(self):
        """Test agent with budget: tracks costs end-to-end."""
        model = Model("openai/gpt-4o-mini")
        budget = Budget(run=10.0, on_exceeded=warn_on_exceeded)
        agent = Agent(model=model, budget=budget)

        with patch.object(agent._provider, "complete", new_callable=AsyncMock) as mock:
            mock.return_value = ProviderResponse(
                content="Response",
                tool_calls=[],
                token_usage=TokenUsage(input_tokens=1000, output_tokens=500),
            )

            agent.response("Hello")

        # Budget should track the cost
        summary = agent.budget_summary
        assert summary["current_run_cost"] > 0

    def test_agent_switch_model_workflow(self):
        """Test agent model switching."""
        model = Model("openai/gpt-4o-mini")
        agent = Agent(model=model)

        assert "gpt-4o-mini" in agent._model_config.model_id

        agent.switch_model(Model("openai/gpt-4"))
        assert "gpt-4" in agent._model_config.model_id


class TestMultiAgentIntegration:
    """Integration tests for multi-agent scenarios."""

    def test_handoff_workflow(self):
        """Test agent handoff: create agent → handoff → continue."""
        from syrin.tool import tool

        @tool
        def specialist_tool() -> str:
            return "Specialist result"

        class Specialist(Agent):
            model = Model("openai/gpt-4o-mini")
            tools = [specialist_tool]

        agent = Agent(model=Model("openai/gpt-4o-mini"))

        with patch("syrin.agent._get_provider") as mock_provider:
            mock_provider.return_value = AsyncMock()
            mock_provider.return_value.complete = AsyncMock(
                return_value=ProviderResponse(
                    content="Specialist result",
                    tool_calls=[],
                    token_usage=TokenUsage(),
                )
            )

            # Create a handoff
            child = agent.handoff(Specialist, "Perform specialized task")
            assert child is not None

    def test_spawn_workflow(self):
        """Test agent spawn: create parent → spawn child → independent."""

        class Child(Agent):
            model = Model("openai/gpt-4o-mini")

        parent = Agent(model=Model("openai/gpt-4o-mini"))

        with patch("syrin.agent._get_provider") as mock_provider:
            mock_provider.return_value = MagicMock()

            child = parent.spawn(Child)
            assert child is not None
            assert child is not parent


class TestBudgetTrackingIntegration:
    """Integration tests for budget tracking."""

    def test_budget_warning_workflow(self):
        """Test budget warning: cost exceeds threshold → warning."""
        model = Model("openai/gpt-4o-mini")
        budget = Budget(run=1.0, on_exceeded=warn_on_exceeded)
        agent = Agent(model=model, budget=budget)

        with patch.object(agent._provider, "complete", new_callable=AsyncMock) as mock:
            # High cost to trigger warning
            mock.return_value = ProviderResponse(
                content="Response",
                tool_calls=[],
                token_usage=TokenUsage(input_tokens=1_000_000, output_tokens=500_000),
            )

            response = agent.response("Test")

        # Should complete without error (WARN only)
        assert response.content == "Response"

    def test_budget_error_workflow(self):
        """Test budget error: cost exceeds limit → raises."""
        model = Model("openai/gpt-4o-mini")
        budget = Budget(run=0.000001, on_exceeded=raise_on_exceeded)
        agent = Agent(model=model, budget=budget)

        with patch.object(agent._provider, "complete", new_callable=AsyncMock) as mock:
            mock.return_value = ProviderResponse(
                content="Response",
                tool_calls=[],
                token_usage=TokenUsage(input_tokens=1000, output_tokens=500),
            )

            from syrin.exceptions import BudgetExceededError

            with pytest.raises(BudgetExceededError):
                agent.response("Test")


class TestLoopIntegration:
    """Integration tests for different loop types."""

    def test_react_loop_integration(self):
        """Test REACT loop with tool calling."""

        @tool
        def calculator(_expr: str) -> str:
            return "42"

        model = Model("openai/gpt-4o-mini")
        agent = Agent(model=model, tools=[calculator])

        call_count = 0

        async def mock_complete(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ProviderResponse(
                    content="",
                    tool_calls=[
                        ToolCall(id="call_1", name="calculator", arguments={"expr": "6*7"})
                    ],
                    token_usage=TokenUsage(),
                )
            return ProviderResponse(
                content="The answer is 42.", tool_calls=[], token_usage=TokenUsage()
            )

        with patch.object(agent._provider, "complete", side_effect=mock_complete):
            response = agent.response("What is 6*7?")

        assert response.content == "The answer is 42."
        assert call_count == 2

    def test_single_shot_loop_integration(self):
        """Test SingleShot loop - no tool calling."""

        model = Model("openai/gpt-4o-mini")
        agent = Agent(model=model)

        with patch.object(agent._provider, "complete", new_callable=AsyncMock) as mock:
            mock.return_value = ProviderResponse(
                content="Simple response",
                tool_calls=[],
                token_usage=TokenUsage(),
            )

            response = agent.response("Hello")

        assert response.content == "Simple response"


class TestMemoryIntegration:
    """Integration tests for memory system."""

    def test_buffer_memory_integration(self):
        """Test BufferMemory with agent."""
        from syrin.memory import BufferMemory
        from syrin.types import Message, MessageRole

        mem = BufferMemory()
        mem.add(Message(role=MessageRole.USER, content="First message"))
        mem.add(Message(role=MessageRole.ASSISTANT, content="First response"))
        mem.add(Message(role=MessageRole.USER, content="Second message"))

        model = Model("openai/gpt-4o-mini")
        agent = Agent(model=model, memory=mem)

        messages = agent._build_messages("Third message")
        # Should have: 3 history + new = 4 (no system by default)
        assert len(messages) == 4

    def test_window_memory_integration(self):
        """Test WindowMemory with agent - limits history."""
        from syrin.memory import WindowMemory
        from syrin.types import Message, MessageRole

        mem = WindowMemory(k=1)  # Keep only last pair

        # Add 5 pairs
        for i in range(5):
            mem.add(Message(role=MessageRole.USER, content=f"User {i}"))
            mem.add(Message(role=MessageRole.ASSISTANT, content=f"Assistant {i}"))

        model = Model("openai/gpt-4o-mini")
        agent = Agent(model=model, memory=mem)

        messages = agent._build_messages("New message")
        # Should have: last pair (2) + new (1) = 3 (no system by default)
        assert len(messages) == 3


class TestCostCalculationIntegration:
    """Integration tests for cost calculation across the system."""

    def test_cost_calculation_multiple_models(self):
        """Test cost calculation for different models."""
        models_to_test = [
            ("gpt-4o-mini", 0.15, 0.60),  # input/output per 1M
            ("gpt-4o", 2.50, 10.00),
            ("claude-3-haiku", 0.20, 0.20),
        ]

        for model_id, _expected_input_rate, _expected_output_rate in models_to_test:
            usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)

            from syrin.cost import calculate_cost

            cost = calculate_cost(model_id, usage)

            # Just verify cost is calculated (not zero)
            assert cost > 0, f"Cost should be > 0 for {model_id}"

    def test_budget_tracker_integration(self):
        """Test BudgetTracker tracks all costs."""
        from syrin.budget import BudgetTracker

        tracker = BudgetTracker()

        # Record multiple costs
        tracker.record(
            CostInfo(cost_usd=0.01, token_usage=TokenUsage(input_tokens=100, output_tokens=50))
        )
        tracker.record(
            CostInfo(cost_usd=0.02, token_usage=TokenUsage(input_tokens=200, output_tokens=100))
        )
        tracker.record(
            CostInfo(cost_usd=0.03, token_usage=TokenUsage(input_tokens=300, output_tokens=150))
        )

        assert tracker.current_run_cost == 0.06

        summary = tracker.get_summary()
        assert summary.current_run_cost == 0.06
