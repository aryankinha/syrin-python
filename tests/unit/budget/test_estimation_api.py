"""TDD tests for the simplified Budget Estimation API (v0.11.0).

Tests cover:
- CostEstimate dataclass
- EstimationPolicy StrEnum on Budget
- CostEstimator base class with estimate_agent() / estimate_many()
- Agent.estimated_cost property
- Swarm.estimated_cost property
- Hook.ESTIMATION_COMPLETE enum value
"""

from __future__ import annotations

import pytest

from syrin.model import Model

# Shared mock model to avoid real API calls
_MOCK_MODEL = Model.Almock()

# ---------------------------------------------------------------------------
# CostEstimate
# ---------------------------------------------------------------------------


def test_cost_estimate_fields() -> None:
    """CostEstimate has p50, p95, sufficient, and low_confidence fields."""
    from syrin.budget._estimate import CostEstimate

    est = CostEstimate(p50=0.01, p95=0.02, sufficient=True, low_confidence=False)
    assert est.p50 == 0.01
    assert est.p95 == 0.02
    assert est.sufficient is True
    assert est.low_confidence is False


def test_cost_estimate_is_frozen() -> None:
    """CostEstimate is immutable (frozen dataclass)."""
    from syrin.budget._estimate import CostEstimate

    est = CostEstimate(p50=0.01, p95=0.02, sufficient=True, low_confidence=False)
    with pytest.raises((AttributeError, TypeError)):
        est.p50 = 0.99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# EstimationPolicy StrEnum
# ---------------------------------------------------------------------------


def test_estimation_policy_values() -> None:
    """EstimationPolicy has DISABLED, WARN_ONLY, and RAISE values."""
    from syrin.enums import EstimationPolicy

    assert EstimationPolicy.DISABLED == "disabled"
    assert EstimationPolicy.WARN_ONLY == "warn_only"
    assert EstimationPolicy.RAISE == "raise"


def test_estimation_policy_is_str_enum() -> None:
    """EstimationPolicy is a StrEnum."""
    from enum import StrEnum

    from syrin.enums import EstimationPolicy

    assert issubclass(EstimationPolicy, StrEnum)


# ---------------------------------------------------------------------------
# Hook.ESTIMATION_COMPLETE
# ---------------------------------------------------------------------------


def test_hook_estimation_complete_exists() -> None:
    """Hook.ESTIMATION_COMPLETE is present with the expected value."""
    from syrin.enums import Hook

    assert Hook.ESTIMATION_COMPLETE == "estimation.complete"


# ---------------------------------------------------------------------------
# Budget new fields
# ---------------------------------------------------------------------------


def test_budget_estimation_false_by_default() -> None:
    """Budget.estimation defaults to False."""
    from syrin.budget import Budget

    b = Budget(max_cost=1.0)
    assert b.estimation is False


def test_budget_estimation_true_accepted() -> None:
    """Budget.estimation=True is accepted."""
    from syrin.budget import Budget

    b = Budget(max_cost=1.0, estimation=True)
    assert b.estimation is True


def test_budget_estimation_policy_default_warn_only() -> None:
    """Budget.estimation_policy defaults to EstimationPolicy.WARN_ONLY."""
    from syrin.budget import Budget
    from syrin.enums import EstimationPolicy

    b = Budget(max_cost=1.0)
    assert b.estimation_policy == EstimationPolicy.WARN_ONLY


def test_budget_custom_estimator_accepted() -> None:
    """Budget.estimator accepts a CostEstimator subclass instance."""
    from syrin.budget import Budget, CostEstimator
    from syrin.budget._estimate import CostEstimate

    class MyEstimator(CostEstimator):
        def estimate_agent(self, agent_class: type) -> CostEstimate:
            return CostEstimate(p50=0.05, p95=0.10, sufficient=True, low_confidence=False)

    estimator = MyEstimator()
    b = Budget(max_cost=1.0, estimation=True, estimator=estimator)
    assert b.estimator is estimator


# ---------------------------------------------------------------------------
# CostEstimator base class
# ---------------------------------------------------------------------------


def test_budget_estimator_default_uses_class_hint() -> None:
    """CostEstimator.estimate_agent uses output_tokens_estimate when present."""
    from syrin.budget import CostEstimator

    class HeavyAgent:
        output_tokens_estimate = (1000, 2000)

    estimator = CostEstimator()
    result = estimator.estimate_agent(HeavyAgent)

    # p50 from 1000 tokens, p95 from 2000 tokens
    assert result.p50 > 0.0
    assert result.p95 >= result.p50
    assert result.low_confidence is False
    assert result.sufficient is True  # no budget context → always True


def test_budget_estimator_low_confidence_when_no_hint() -> None:
    """CostEstimator.estimate_agent marks low_confidence=True when no hint."""
    from syrin.budget import CostEstimator

    class SimpleAgent:
        pass

    estimator = CostEstimator()
    result = estimator.estimate_agent(SimpleAgent)
    assert result.low_confidence is True
    assert result.sufficient is True


def test_budget_estimator_estimate_many_aggregates() -> None:
    """estimate_many sums p50/p95 across agents."""
    from syrin.budget import CostEstimator

    class AgentA:
        output_tokens_estimate = (100, 200)

    class AgentB:
        output_tokens_estimate = (300, 600)

    estimator = CostEstimator()
    a_est = estimator.estimate_agent(AgentA)
    b_est = estimator.estimate_agent(AgentB)

    combined = estimator.estimate_many([AgentA, AgentB], budget=None)
    assert abs(combined.p50 - (a_est.p50 + b_est.p50)) < 1e-9
    assert abs(combined.p95 - (a_est.p95 + b_est.p95)) < 1e-9


def test_budget_estimator_estimate_many_sets_sufficient_true() -> None:
    """estimate_many sets sufficient=True when budget covers p95."""
    from syrin.budget import Budget, CostEstimator

    class TinyAgent:
        output_tokens_estimate = 10  # very cheap

    estimator = CostEstimator()
    result = estimator.estimate_many([TinyAgent], budget=Budget(max_cost=100.0))
    assert result.sufficient is True


def test_budget_estimator_estimate_many_sets_sufficient_false() -> None:
    """estimate_many sets sufficient=False when budget is too small."""
    from syrin.budget import Budget, CostEstimator

    class HeavyAgent:
        output_tokens_estimate = (10_000_000, 20_000_000)  # extremely expensive

    estimator = CostEstimator()
    result = estimator.estimate_many([HeavyAgent], budget=Budget(max_cost=0.0001))
    assert result.sufficient is False


def test_budget_estimator_override_estimate_agent() -> None:
    """CostEstimator subclasses can override estimate_agent."""
    from syrin.budget import CostEstimator
    from syrin.budget._estimate import CostEstimate

    class FixedEstimator(CostEstimator):
        def estimate_agent(self, agent_class: type) -> CostEstimate:
            return CostEstimate(p50=1.0, p95=2.0, sufficient=True, low_confidence=False)

    estimator = FixedEstimator()

    class AnyAgent:
        pass

    result = estimator.estimate_agent(AnyAgent)
    assert result.p50 == 1.0
    assert result.p95 == 2.0


# ---------------------------------------------------------------------------
# Agent.estimated_cost property
# ---------------------------------------------------------------------------


def test_agent_estimated_cost_returns_none_when_no_budget() -> None:
    """Agent.estimated_cost returns None when no budget is configured."""
    from syrin.agent._core import Agent

    class MyAgent(Agent):
        model = _MOCK_MODEL
        system_prompt = "test"

    agent = MyAgent()
    assert agent.estimated_cost is None


def test_agent_estimated_cost_returns_none_when_estimation_false() -> None:
    """Agent.estimated_cost returns None when budget.estimation=False."""
    from syrin.agent._core import Agent
    from syrin.budget import Budget

    class MyAgent(Agent):
        model = _MOCK_MODEL
        system_prompt = "test"

    agent = MyAgent(budget=Budget(max_cost=1.0, estimation=False))
    assert agent.estimated_cost is None


def test_agent_estimated_cost_returns_cost_estimate_when_true() -> None:
    """Agent.estimated_cost returns a CostEstimate when estimation=True."""
    from syrin.agent._core import Agent
    from syrin.budget import Budget
    from syrin.budget._estimate import CostEstimate

    class MyAgent(Agent):
        model = _MOCK_MODEL
        system_prompt = "test"

    agent = MyAgent(budget=Budget(max_cost=5.0, estimation=True))
    result = agent.estimated_cost
    assert result is not None
    assert isinstance(result, CostEstimate)
    assert result.p50 >= 0.0
    assert result.p95 >= result.p50


def test_agent_estimated_cost_uses_custom_estimator() -> None:
    """Agent.estimated_cost uses Budget.estimator when provided."""
    from syrin.agent._core import Agent
    from syrin.budget import Budget, CostEstimator
    from syrin.budget._estimate import CostEstimate

    class FixedEstimator(CostEstimator):
        def estimate_agent(self, agent_class: type) -> CostEstimate:
            return CostEstimate(p50=0.42, p95=0.84, sufficient=True, low_confidence=False)

    class MyAgent(Agent):
        model = _MOCK_MODEL
        system_prompt = "test"

    agent = MyAgent(budget=Budget(max_cost=5.0, estimation=True, estimator=FixedEstimator()))
    result = agent.estimated_cost
    assert result is not None
    assert result.p50 == pytest.approx(0.42)
    assert result.p95 == pytest.approx(0.84)


# ---------------------------------------------------------------------------
# Swarm.estimated_cost property
# ---------------------------------------------------------------------------


def test_swarm_estimated_cost_returns_none_when_no_budget() -> None:
    """Swarm.estimated_cost returns None when no budget is set."""
    from unittest.mock import MagicMock

    from syrin.swarm._core import Swarm

    agent = MagicMock()
    swarm = Swarm(agents=[agent], goal="test")
    assert swarm.estimated_cost is None


def test_swarm_estimated_cost_aggregates_agents() -> None:
    """Swarm.estimated_cost returns a CostEstimate covering all agents."""
    from unittest.mock import MagicMock

    from syrin.budget import Budget
    from syrin.budget._estimate import CostEstimate
    from syrin.swarm._core import Swarm

    agent1 = MagicMock()
    agent2 = MagicMock()
    swarm = Swarm(
        agents=[agent1, agent2],
        goal="test",
        budget=Budget(max_cost=10.0, estimation=True),
    )
    result = swarm.estimated_cost
    assert result is not None
    assert isinstance(result, CostEstimate)


# ---------------------------------------------------------------------------
# EstimationPolicy enforcement
# ---------------------------------------------------------------------------


def test_estimation_policy_raise_raises_on_insufficient() -> None:
    """When policy=RAISE and p95 > budget, estimated_cost raises InsufficientBudgetError."""
    from syrin.agent._core import Agent
    from syrin.budget import Budget, CostEstimator, InsufficientBudgetError
    from syrin.budget._estimate import CostEstimate
    from syrin.enums import EstimationPolicy

    class ExpensiveEstimator(CostEstimator):
        def estimate_agent(self, agent_class: type) -> CostEstimate:
            return CostEstimate(p50=10.0, p95=20.0, sufficient=False, low_confidence=False)

    class MyAgent(Agent):
        model = _MOCK_MODEL
        system_prompt = "test"

    agent = MyAgent(
        budget=Budget(
            max_cost=0.001,
            estimation=True,
            estimation_policy=EstimationPolicy.RAISE,
            estimator=ExpensiveEstimator(),
        )
    )
    with pytest.raises(InsufficientBudgetError):
        _ = agent.estimated_cost


def test_estimation_policy_warn_only_does_not_raise() -> None:
    """When policy=WARN_ONLY and p95 > budget, estimated_cost does not raise."""
    from syrin.agent._core import Agent
    from syrin.budget import Budget, CostEstimator
    from syrin.budget._estimate import CostEstimate
    from syrin.enums import EstimationPolicy

    class ExpensiveEstimator(CostEstimator):
        def estimate_agent(self, agent_class: type) -> CostEstimate:
            return CostEstimate(p50=10.0, p95=20.0, sufficient=False, low_confidence=False)

    class MyAgent(Agent):
        model = _MOCK_MODEL
        system_prompt = "test"

    agent = MyAgent(
        budget=Budget(
            max_cost=0.001,
            estimation=True,
            estimation_policy=EstimationPolicy.WARN_ONLY,
            estimator=ExpensiveEstimator(),
        )
    )
    # Should not raise; returns the estimate with sufficient=False
    result = agent.estimated_cost
    assert result is not None
    assert result.sufficient is False
