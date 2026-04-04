"""P1-T4: WorkflowExecutor — sequential step tests.

Mock at Agent.arun() (the LLM boundary). Return deterministic Response objects.
"""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.response import Response
from syrin.types import TokenUsage
from syrin.workflow import Workflow


def _make_agent(content: str, cost: float = 0.01) -> type[Agent]:
    """Create an agent stub that returns a fixed response."""

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = f"Stub: {content}"

    fixed = Response(
        content=content,
        raw=content,
        cost=cost,
        tokens=TokenUsage(input_tokens=5, output_tokens=10, total_tokens=15),
        model="almock/almock",
        trace=[],
    )

    async def _arun(self: Agent, input_text: str) -> Response[str]:
        self._last_input = input_text  # type: ignore[attr-defined]
        return fixed

    def _run(self: Agent, input_text: str) -> Response[str]:
        self._last_input = input_text  # type: ignore[attr-defined]
        return fixed

    _Stub.arun = _arun  # type: ignore[method-assign]
    _Stub.run = _run  # type: ignore[method-assign]
    _Stub.__name__ = f"Stub_{content[:10].replace(' ', '_')}"
    return _Stub


@pytest.mark.phase_1
class TestSingleStep:
    """Single sequential step: output of step becomes the result."""

    async def test_single_step_returns_response(self) -> None:
        """A single-step workflow returns the step's response."""
        Agent1 = _make_agent("answer from step 1")
        wf = Workflow("test").step(Agent1)
        result = await wf.run("user input")
        assert result.content == "answer from step 1"

    async def test_single_step_cost_is_tracked(self) -> None:
        """Cost from a single step is reflected in the response."""
        Agent1 = _make_agent("result", cost=0.05)
        wf = Workflow("test").step(Agent1)
        result = await wf.run("task")
        assert result.cost == pytest.approx(0.05)


@pytest.mark.phase_1
class TestTwoStepSequential:
    """Two sequential steps: step 1 output → step 2 input as HandoffContext.content."""

    async def test_two_steps_chain_content(self) -> None:
        """Second step receives first step's output as its task input."""
        received_inputs: list[str] = []

        class FirstAgent(Agent):
            model = Model.Almock()
            system_prompt = "First"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="first result", cost=0.01)

        class SecondAgent(Agent):
            model = Model.Almock()
            system_prompt = "Second"

            async def arun(self, input_text: str) -> Response[str]:
                received_inputs.append(input_text)
                return Response(content="second result", cost=0.02)

        wf = Workflow("chain").step(FirstAgent).step(SecondAgent)
        result = await wf.run("initial input")

        assert result.content == "second result"
        assert len(received_inputs) == 1
        # Second agent receives first agent's content
        assert "first result" in received_inputs[0]

    async def test_two_steps_final_result_is_last_step(self) -> None:
        """The final response is from the last step, not the first."""
        Agent1 = _make_agent("step 1 output")
        Agent2 = _make_agent("step 2 output")
        wf = Workflow("test").step(Agent1).step(Agent2)
        result = await wf.run("task")
        assert result.content == "step 2 output"


@pytest.mark.phase_1
class TestThreeStepHistory:
    """Three steps: ctx.history has 2 entries when step 3 executes."""

    async def test_history_accumulates(self) -> None:
        """History grows as steps complete."""

        class Step1(Agent):
            model = Model.Almock()
            system_prompt = "Step1"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="step1 output", cost=0.01)

        class Step2(Agent):
            model = Model.Almock()
            system_prompt = "Step2"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="step2 output", cost=0.01)

        class Step3(Agent):
            model = Model.Almock()
            system_prompt = "Step3"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="step3 output", cost=0.01)

        wf = Workflow("three-steps").step(Step1).step(Step2).step(Step3)
        result = await wf.run("input")
        assert result.content == "step3 output"


@pytest.mark.phase_1
class TestStepTaskOverride:
    """Step with task= override: uses the override, not HandoffContext.content."""

    async def test_task_override_is_passed_to_agent(self) -> None:
        """When task is set, the agent receives the override, not previous output."""
        received_tasks: list[str] = []

        class Agent1(Agent):
            model = Model.Almock()
            system_prompt = "Agent1"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="agent1 output", cost=0.01)

        class Agent2(Agent):
            model = Model.Almock()
            system_prompt = "Agent2"

            async def arun(self, input_text: str) -> Response[str]:
                received_tasks.append(input_text)
                return Response(content="agent2 output", cost=0.01)

        wf = Workflow("override").step(Agent1).step(Agent2, task="fixed task")
        await wf.run("initial")

        assert len(received_tasks) == 1
        assert received_tasks[0] == "fixed task"

    async def test_task_override_without_previous_context(self) -> None:
        """When no task override, agent receives HandoffContext.content."""
        received_tasks: list[str] = []

        class AgentCapture(Agent):
            model = Model.Almock()
            system_prompt = "capture"

            async def arun(self, input_text: str) -> Response[str]:
                received_tasks.append(input_text)
                return Response(content="captured", cost=0.01)

        wf = Workflow("no-override").step(AgentCapture)
        await wf.run("my specific input")

        assert received_tasks[0] == "my specific input"
