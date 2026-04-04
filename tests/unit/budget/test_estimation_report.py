"""Tests for EstimationReport and Workflow.estimate()."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from syrin.budget._estimate import CostEstimate, EstimationReport
from syrin.workflow import Workflow

# ---------------------------------------------------------------------------
# EstimationReport dataclass fields
# ---------------------------------------------------------------------------


def test_estimation_report_fields() -> None:
    per_step = [
        CostEstimate(p50=0.05, p95=0.10, sufficient=True, low_confidence=False),
        CostEstimate(p50=0.03, p95=0.08, sufficient=True, low_confidence=False),
    ]
    report = EstimationReport(
        total_p50=0.08,
        total_p95=0.18,
        budget_sufficient=True,
        per_step=per_step,
        low_confidence=False,
    )
    assert report.total_p50 == 0.08
    assert report.total_p95 == 0.18
    assert report.budget_sufficient is True
    assert len(report.per_step) == 2
    assert report.low_confidence is False


def test_estimation_report_low_confidence_flag() -> None:
    per_step = [
        CostEstimate(p50=0.01, p95=0.02, sufficient=True, low_confidence=True),
    ]
    report = EstimationReport(
        total_p50=0.01,
        total_p95=0.02,
        budget_sufficient=True,
        per_step=per_step,
        low_confidence=True,
    )
    assert report.low_confidence is True


def test_estimation_report_is_frozen() -> None:
    """EstimationReport should be immutable (frozen=True)."""
    per_step: list[CostEstimate] = []
    report = EstimationReport(
        total_p50=0.0,
        total_p95=0.0,
        budget_sufficient=True,
        per_step=per_step,
        low_confidence=False,
    )
    with pytest.raises((AttributeError, TypeError)):
        report.total_p50 = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Workflow.estimate() — zero LLM calls
# ---------------------------------------------------------------------------


class FakeAgent:
    """Minimal fake agent with a class name."""

    output_tokens_estimate = 500


class FakeAgent2:
    output_tokens_estimate = (300, 700)


def test_workflow_estimate_returns_estimation_report() -> None:
    wf = Workflow("test-wf").step(FakeAgent)  # type: ignore[arg-type]
    report = wf.estimate("some input")
    assert isinstance(report, EstimationReport)


def test_workflow_estimate_aggregates_steps() -> None:
    wf = (
        Workflow("test-wf")
        .step(FakeAgent)  # type: ignore[arg-type]
        .step(FakeAgent2)  # type: ignore[arg-type]
    )
    report = wf.estimate("some input")
    assert len(report.per_step) == 2
    # Both steps should be present
    assert report.total_p50 > 0
    assert report.total_p95 > 0


def test_workflow_estimate_budget_sufficient_false_when_budget_too_small() -> None:
    from syrin.budget import Budget

    wf = (
        Workflow("test-wf", budget=Budget(max_cost=0.0001)).step(FakeAgent)  # type: ignore[arg-type]
    )
    report = wf.estimate("some input")
    # p95 for FakeAgent with 500 tokens = 500 * 0.000003 = 0.0015
    # Budget max_cost=0.0001 < 0.0015 → insufficient
    assert report.budget_sufficient is False


def test_workflow_estimate_budget_sufficient_true_when_budget_large() -> None:
    from syrin.budget import Budget

    wf = (
        Workflow("test-wf", budget=Budget(max_cost=100.0)).step(FakeAgent)  # type: ignore[arg-type]
    )
    report = wf.estimate("some input")
    assert report.budget_sufficient is True


def test_workflow_estimate_zero_llm_calls() -> None:
    """estimate() must not invoke any LLM model.complete() calls."""
    wf = Workflow("test-wf").step(FakeAgent)  # type: ignore[arg-type]

    call_count = [0]

    def fake_complete(*args: object, **kwargs: object) -> object:
        call_count[0] += 1
        raise AssertionError("LLM was called during estimate()!")

    # Patch at a high level to detect any accidental LLM call
    with patch("syrin.budget._estimate.CostEstimator.estimate_agent") as mock_est:
        mock_est.return_value = CostEstimate(
            p50=0.05, p95=0.10, sufficient=True, low_confidence=False
        )
        report = wf.estimate("some input")

    assert call_count[0] == 0
    assert isinstance(report, EstimationReport)


def test_workflow_estimate_parallel_step() -> None:
    """Parallel steps should produce per-agent estimates."""
    wf = Workflow("test-wf").parallel([FakeAgent, FakeAgent2])  # type: ignore[arg-type]
    report = wf.estimate("some input")
    # Parallel step has 2 agents
    assert len(report.per_step) == 2


def test_workflow_estimate_no_steps_raises() -> None:
    """Workflow.estimate() on empty workflow should raise WorkflowNotRunnable."""
    from syrin.workflow.exceptions import WorkflowNotRunnable

    wf = Workflow("empty-wf")
    with pytest.raises(WorkflowNotRunnable):
        wf.estimate("input")
