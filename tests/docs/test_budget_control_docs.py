"""Validate code examples from docs/budget-control.md.

Runs the main budget examples with mocked provider so no real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from syrin import Agent, Budget, RateLimit, warn_on_exceeded
from syrin.enums import ThresholdWindow
from syrin.model import Model
from syrin.threshold import BudgetThreshold
from syrin.types import ProviderResponse, TokenUsage


def _mock_provider_response(
    content: str = "test",
    token_usage: TokenUsage | None = None,
) -> ProviderResponse:
    return ProviderResponse(
        content=content,
        tool_calls=[],
        token_usage=token_usage or TokenUsage(input_tokens=10, output_tokens=20),
    )


def _create_mock_provider():
    mock = MagicMock()
    mock.complete = AsyncMock(return_value=_mock_provider_response())
    mock.stream_sync = MagicMock(
        return_value=iter(
            [_mock_provider_response(content="a"), _mock_provider_response(content="b")]
        )
    )

    async def _stream(*_args, **_kwargs):
        yield _mock_provider_response(content="c")

    mock.stream = _stream
    return mock


class TestBudgetControlCompleteExample:
    """Complete Example from budget-control.md (BudgetAwareAgent with ThresholdWindow)."""

    @patch("syrin.agent._get_provider")
    def test_budget_aware_agent_with_thresholds(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()

        class BudgetAwareAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            system_prompt = "You are a helpful assistant."

            def __init__(self):
                super().__init__()
                self.budget = Budget(
                    run=1.00,
                    on_exceeded=warn_on_exceeded,
                    thresholds=[
                        BudgetThreshold(at=80, action=lambda _: None),
                        BudgetThreshold(at=95, action=lambda _: None),
                    ],
                )

        agent = BudgetAwareAgent()
        response = agent.response("What is Python?")
        assert response.content
        assert hasattr(response, "cost")
        assert response.budget_remaining is not None or response.budget_used is not None


class TestBudgetControlSpendThresholdExample:
    """Spend-only thresholds (run + daily) from budget-control.md."""

    @patch("syrin.agent._get_provider")
    def test_spend_threshold_agent_construction(self, mock_get_provider):
        mock_get_provider.return_value = _create_mock_provider()

        class SpendThresholdAgent(Agent):
            model = Model("openai/gpt-4o-mini")
            system_prompt = "Be concise."

            def __init__(self):
                super().__init__()
                self.budget = Budget(
                    run=1.00,
                    per=RateLimit(hour=5.00, day=20.00),
                    on_exceeded=warn_on_exceeded,
                    thresholds=[
                        BudgetThreshold(at=80, action=lambda _: None),
                        BudgetThreshold(at=90, action=lambda _: None, window=ThresholdWindow.DAY),
                    ],
                )

        agent = SpendThresholdAgent()
        response = agent.response("Say hello in one line")
        assert response.content
        summary = agent.budget_summary
        assert "current_run_cost" in summary
        assert "daily_cost" in summary


class TestBudgetControlRateLimitExamples:
    """Rate limit and calendar_month from budget-control.md."""

    def test_rate_limit_calendar_month_construction(self):
        r = RateLimit(month=500.00, calendar_month=True)
        assert r.calendar_month is True
        assert r.month == 500.0

    def test_rate_limit_month_days(self):
        r = RateLimit(month=100.0, month_days=7)
        assert r.month_days == 7
