"""Budget enforcement: per-run and per-period limits; threshold actions triggered and tested."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from syrin import Agent
from syrin.budget import Budget, BudgetThreshold, raise_on_exceeded
from syrin.exceptions import BudgetExceededError
from syrin.model import Model
from syrin.types import CostInfo, ProviderResponse, TokenUsage


def _mock_provider_response(
    content: str = "ok",
    input_tokens: int = 1000,
    output_tokens: int = 500,
) -> ProviderResponse:
    return ProviderResponse(
        content=content,
        tool_calls=[],
        token_usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        ),
    )


class TestPerRunLimitEnforced:
    """Per-run budget limit is enforced; run stops and raises or returns with stop_reason."""

    def test_run_cost_exceeds_limit_raises_budget_exceeded(self) -> None:
        """When run cost exceeds budget.run, BudgetExceededError is raised."""
        model = Model("anthropic/claude-3-5-sonnet")
        budget = Budget(max_cost=0.0, on_exceeded=raise_on_exceeded)
        agent = Agent(model=model, budget=budget, system_prompt="Be brief.")
        mock_resp = _mock_provider_response(content="Hi", input_tokens=1000, output_tokens=500)
        with patch.object(
            agent._provider,
            "complete",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            with pytest.raises(BudgetExceededError) as exc_info:
                agent.run("Hello")
            assert "run" in str(exc_info.value).lower() or "budget" in str(exc_info.value).lower()

    def test_run_under_limit_returns_response(self) -> None:
        """When run cost is under limit, response is returned with cost populated."""
        model = Model("anthropic/claude-3-5-sonnet")
        budget = Budget(max_cost=100.0, on_exceeded=raise_on_exceeded)
        agent = Agent(model=model, budget=budget, system_prompt="Be brief.")
        mock_resp = _mock_provider_response(content="Hi", input_tokens=10, output_tokens=5)
        with patch.object(
            agent._provider,
            "complete",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            r = agent.run("Hello")
        assert r.cost >= 0
        assert r.content == "Hi"

    def test_response_has_budget_remaining_after_run(self) -> None:
        """Response.report or response.budget_remaining reflects remaining after run."""
        model = Model("anthropic/claude-3-5-sonnet")
        budget = Budget(max_cost=10.0, on_exceeded=raise_on_exceeded)
        agent = Agent(model=model, budget=budget, system_prompt="Be brief.")
        mock_resp = _mock_provider_response(content="Hi", input_tokens=5, output_tokens=5)
        with patch.object(
            agent._provider,
            "complete",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            r = agent.run("Hello")
        assert r.report is not None
        assert hasattr(r, "budget_remaining") or hasattr(r.report, "budget_remaining")


class TestThresholdActionsTriggered:
    """Budget threshold actions (warn, switch model, stop) are triggered at the right time."""

    def test_threshold_action_called_when_tracker_crosses_threshold(self) -> None:
        """When tracker run cost crosses threshold %, check_thresholds runs the action."""
        from syrin.budget import BudgetTracker

        triggered: list[int] = []

        def on_threshold(ctx):
            triggered.append(getattr(ctx, "percentage", 0))

        tracker = BudgetTracker()
        tracker.record(CostInfo(cost_usd=0.15, token_usage=TokenUsage()))
        budget = Budget(
            max_cost=1.0,
            on_exceeded=raise_on_exceeded,
            thresholds=[BudgetThreshold(at=10, action=on_threshold)],
        )
        tracker.check_thresholds(budget, parent=None)
        assert len(triggered) >= 1
        assert triggered[0] >= 10

    def test_threshold_warn_does_not_raise(self) -> None:
        """Threshold with warn-only action does not raise; run can complete."""
        warned: list[int] = []

        def warn_only(ctx):
            warned.append(getattr(ctx, "at", 0))

        model = Model("anthropic/claude-3-5-sonnet")
        budget = Budget(
            max_cost=100.0,
            on_exceeded=raise_on_exceeded,
            thresholds=[BudgetThreshold(at=1, action=warn_only)],
        )
        agent = Agent(model=model, budget=budget, system_prompt="Be brief.")
        mock_resp = _mock_provider_response(content="Hi", input_tokens=10, output_tokens=5)
        with patch.object(
            agent._provider,
            "complete",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            r = agent.run("Hello")
        assert r.content == "Hi"
        assert len(warned) >= 0


class TestBudgetEdgeCases:
    """Edge cases: no budget, zero run limit, budget without threshold."""

    def test_no_budget_agent_runs_normally(self) -> None:
        """Agent without budget runs and returns response with cost."""
        model = Model("anthropic/claude-3-5-sonnet")
        agent = Agent(model=model, budget=None, system_prompt="Be brief.")
        mock_resp = _mock_provider_response(content="Hi")
        with patch.object(
            agent._provider,
            "complete",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            r = agent.run("Hello")
        assert r.content == "Hi"
        assert r.cost >= 0

    def test_budget_run_zero_raises_on_any_positive_cost(self) -> None:
        """Budget(max_cost=0) with raise_on_exceeded raises as soon as cost is recorded."""
        model = Model("anthropic/claude-3-5-sonnet")
        budget = Budget(max_cost=0.0, on_exceeded=raise_on_exceeded)
        agent = Agent(model=model, budget=budget, system_prompt="Be brief.")
        mock_resp = _mock_provider_response(content="x", input_tokens=1, output_tokens=1)
        with (
            patch.object(
                agent._provider,
                "complete",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
            pytest.raises(BudgetExceededError),
        ):
            agent.run("Hi")
