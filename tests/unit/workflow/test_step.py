"""P1-T2: WorkflowStep type tests.

Tests cover all four step types: SequentialStep, ParallelStep, BranchStep, DynamicStep.
All steps must be immutable after construction.
"""

from __future__ import annotations

import pytest

from syrin import Agent, Budget, Model
from syrin.workflow._step import BranchStep, DynamicStep, ParallelStep, SequentialStep

# ──────────────────────────────────────────────────────────────────────────────
# Stub agents
# ──────────────────────────────────────────────────────────────────────────────


class AgentA(Agent):
    """Stub agent A."""

    model = Model.Almock()
    system_prompt = "Agent A"


class AgentB(Agent):
    """Stub agent B."""

    model = Model.Almock()
    system_prompt = "Agent B"


class AgentC(Agent):
    """Stub agent C."""

    model = Model.Almock()
    system_prompt = "Agent C"


# ──────────────────────────────────────────────────────────────────────────────
# SequentialStep
# ──────────────────────────────────────────────────────────────────────────────


class TestSequentialStep:
    """SequentialStep holds exactly one agent class + optional task + optional budget."""

    def test_holds_one_agent_class(self) -> None:
        """SequentialStep stores the agent class."""
        step = SequentialStep(agent_class=AgentA)
        assert step.agent_class is AgentA

    def test_task_defaults_to_none(self) -> None:
        """task defaults to None when not provided."""
        step = SequentialStep(agent_class=AgentA)
        assert step.task is None

    def test_task_can_be_set(self) -> None:
        """task stores the provided override string."""
        step = SequentialStep(agent_class=AgentA, task="do something")
        assert step.task == "do something"

    def test_budget_defaults_to_none(self) -> None:
        """budget defaults to None when not provided."""
        step = SequentialStep(agent_class=AgentA)
        assert step.budget is None

    def test_budget_can_be_set(self) -> None:
        """budget stores the provided Budget instance."""
        bgt = Budget(max_cost=0.50)
        step = SequentialStep(agent_class=AgentA, budget=bgt)
        assert step.budget is bgt

    def test_is_immutable(self) -> None:
        """SequentialStep is frozen — mutation raises an error."""
        step = SequentialStep(agent_class=AgentA)
        with pytest.raises((AttributeError, TypeError)):
            step.agent_class = AgentB  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# ParallelStep
# ──────────────────────────────────────────────────────────────────────────────


class TestParallelStep:
    """ParallelStep holds a list of agent classes; minimum 2."""

    def test_holds_multiple_agent_classes(self) -> None:
        """ParallelStep stores agent classes as a tuple."""
        step = ParallelStep(agent_classes=(AgentA, AgentB))
        assert AgentA in step.agent_classes
        assert AgentB in step.agent_classes

    def test_minimum_two_agents(self) -> None:
        """ParallelStep requires at least 2 agent classes."""
        with pytest.raises(ValueError, match="at least 2"):
            ParallelStep(agent_classes=(AgentA,))

    def test_empty_raises(self) -> None:
        """Empty agent_classes raises ValueError."""
        with pytest.raises(ValueError):
            ParallelStep(agent_classes=())

    def test_three_agents_allowed(self) -> None:
        """Three or more agents are valid."""
        step = ParallelStep(agent_classes=(AgentA, AgentB, AgentC))
        assert len(step.agent_classes) == 3

    def test_budget_defaults_to_none(self) -> None:
        """budget defaults to None."""
        step = ParallelStep(agent_classes=(AgentA, AgentB))
        assert step.budget is None

    def test_budget_can_be_set(self) -> None:
        """budget stores the provided Budget."""
        bgt = Budget(max_cost=1.00)
        step = ParallelStep(agent_classes=(AgentA, AgentB), budget=bgt)
        assert step.budget is bgt

    def test_is_immutable(self) -> None:
        """ParallelStep is frozen — mutation raises an error."""
        step = ParallelStep(agent_classes=(AgentA, AgentB))
        with pytest.raises((AttributeError, TypeError)):
            step.agent_classes = (AgentC,)  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# BranchStep
# ──────────────────────────────────────────────────────────────────────────────


class TestBranchStep:
    """BranchStep requires a callable condition, if_true agent, if_false agent."""

    def test_holds_condition_and_branches(self) -> None:
        """BranchStep stores condition callable and both branch classes."""
        cond = lambda _ctx: True  # noqa: E731
        step = BranchStep(condition=cond, if_true_class=AgentA, if_false_class=AgentB)
        assert step.condition is cond
        assert step.if_true_class is AgentA
        assert step.if_false_class is AgentB

    def test_condition_can_return_bool(self) -> None:
        """condition callable returns bool."""
        step = BranchStep(
            condition=lambda ctx: bool(ctx),
            if_true_class=AgentA,
            if_false_class=AgentB,
        )
        assert step.condition is not None

    def test_budget_defaults_to_none(self) -> None:
        """budget defaults to None."""
        step = BranchStep(
            condition=lambda _ctx: True,
            if_true_class=AgentA,
            if_false_class=AgentB,
        )
        assert step.budget is None

    def test_budget_can_be_set(self) -> None:
        """budget stores the provided Budget."""
        bgt = Budget(max_cost=0.25)
        step = BranchStep(
            condition=lambda _ctx: True,
            if_true_class=AgentA,
            if_false_class=AgentB,
            budget=bgt,
        )
        assert step.budget is bgt

    def test_is_immutable(self) -> None:
        """BranchStep is frozen — mutation raises an error."""
        step = BranchStep(
            condition=lambda _ctx: True,
            if_true_class=AgentA,
            if_false_class=AgentB,
        )
        with pytest.raises((AttributeError, TypeError)):
            step.if_true_class = AgentC  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# DynamicStep
# ──────────────────────────────────────────────────────────────────────────────


class TestDynamicStep:
    """DynamicStep requires a callable fn; optional max_agents cap."""

    def test_holds_factory_fn(self) -> None:
        """DynamicStep stores the factory callable."""
        fn = lambda _ctx: [(AgentA, "task", 0.50)]  # noqa: E731
        step = DynamicStep(fn=fn)
        assert step.fn is fn

    def test_max_agents_defaults_to_none(self) -> None:
        """max_agents is None when not set (unlimited)."""
        step = DynamicStep(fn=lambda _ctx: [])
        assert step.max_agents is None

    def test_max_agents_can_be_set(self) -> None:
        """max_agents stores the cap value."""
        step = DynamicStep(fn=lambda _ctx: [], max_agents=5)
        assert step.max_agents == 5

    def test_label_defaults_to_dynamic(self) -> None:
        """label defaults to 'dynamic' for visualisation."""
        step = DynamicStep(fn=lambda _ctx: [])
        assert step.label == "dynamic"

    def test_label_can_be_set(self) -> None:
        """label can be customised."""
        step = DynamicStep(fn=lambda _ctx: [], label="spawn-workers")
        assert step.label == "spawn-workers"

    def test_is_immutable(self) -> None:
        """DynamicStep is frozen — mutation raises an error."""
        step = DynamicStep(fn=lambda _ctx: [])
        with pytest.raises((AttributeError, TypeError)):
            step.max_agents = 10  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# WorkflowStep union type
# ──────────────────────────────────────────────────────────────────────────────


class TestWorkflowStepUnion:
    """WorkflowStep union enables exhaustive match dispatch."""

    def test_match_sequential(self) -> None:
        """match identifies SequentialStep correctly."""
        step: SequentialStep | ParallelStep | BranchStep | DynamicStep = SequentialStep(
            agent_class=AgentA
        )
        matched = False
        match step:
            case SequentialStep():
                matched = True
            case _:
                pass
        assert matched

    def test_match_parallel(self) -> None:
        """match identifies ParallelStep correctly."""
        step: SequentialStep | ParallelStep | BranchStep | DynamicStep = ParallelStep(
            agent_classes=(AgentA, AgentB)
        )
        matched = False
        match step:
            case ParallelStep():
                matched = True
            case _:
                pass
        assert matched

    def test_match_branch(self) -> None:
        """match identifies BranchStep correctly."""
        step: SequentialStep | ParallelStep | BranchStep | DynamicStep = BranchStep(
            condition=lambda _ctx: True,
            if_true_class=AgentA,
            if_false_class=AgentB,
        )
        matched = False
        match step:
            case BranchStep():
                matched = True
            case _:
                pass
        assert matched

    def test_match_dynamic(self) -> None:
        """match identifies DynamicStep correctly."""
        step: SequentialStep | ParallelStep | BranchStep | DynamicStep = DynamicStep(
            fn=lambda _ctx: []
        )
        matched = False
        match step:
            case DynamicStep():
                matched = True
            case _:
                pass
        assert matched
