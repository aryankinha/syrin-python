"""Tests for SwarmHandoffContext skip_next (Feature 4)."""

from __future__ import annotations

import json

import pytest

from syrin import Agent, Model
from syrin.enums import Hook, SwarmTopology
from syrin.events import EventContext
from syrin.response import Response
from syrin.swarm import Swarm, SwarmConfig, SwarmHandoffContext
from syrin.swarm._handoff import SwarmHandoffContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_orchestrator(task_list: list[dict[str, str]]) -> Agent:
    """Orchestrator that outputs a JSON task list."""
    _tasks = task_list

    class _Orch(Agent):
        model = Model.Almock()
        system_prompt = "orchestrator"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=json.dumps(_tasks), cost=0.01)

    _Orch.__name__ = "Orchestrator"
    return _Orch()


# ---------------------------------------------------------------------------
# Unit tests for SwarmHandoffContext dataclass
# ---------------------------------------------------------------------------


class TestSwarmHandoffContextDataclass:
    """SwarmHandoffContext field defaults and mutation."""

    def test_default_skip_next_is_false(self) -> None:
        """skip_next defaults to False."""
        from syrin.response import Response as _Resp

        ctx = SwarmHandoffContext(
            next_input="input",
            result=_Resp(content="result", cost=0.0),
            current_agent="AgentA",
            next_agent="AgentB",
        )
        assert ctx.skip_next is False

    def test_skip_next_can_be_set_to_true(self) -> None:
        """skip_next can be mutated to True."""
        from syrin.response import Response as _Resp

        ctx = SwarmHandoffContext(
            next_input="input",
            result=_Resp(content="result", cost=0.0),
            current_agent="AgentA",
            next_agent="AgentB",
        )
        ctx.skip_next = True
        assert ctx.skip_next is True

    def test_next_input_can_be_rewritten(self) -> None:
        """next_input can be modified by hook handlers."""
        from syrin.response import Response as _Resp

        ctx = SwarmHandoffContext(
            next_input="original input",
            result=_Resp(content="result", cost=0.0),
            current_agent="AgentA",
            next_agent="AgentB",
        )
        ctx.next_input = "modified input"
        assert ctx.next_input == "modified input"

    def test_next_agent_defaults_to_none(self) -> None:
        """next_agent defaults to None when not provided."""
        from syrin.response import Response as _Resp

        ctx = SwarmHandoffContext(
            next_input="input",
            result=_Resp(content="result", cost=0.0),
            current_agent="AgentA",
        )
        assert ctx.next_agent is None


# ---------------------------------------------------------------------------
# Integration: skip_next in ORCHESTRATOR topology
# ---------------------------------------------------------------------------


@pytest.mark.phase_5
class TestHandoffSkipInOrchestrator:
    """Hook handler setting skip_next=True skips the next agent."""

    async def test_skip_next_true_skips_next_agent(self) -> None:
        """Setting ctx.skip_next=True on SWARM_AGENT_HANDOFF skips the worker."""
        ran: list[str] = []

        class _WorkerAgent(Agent):
            model = Model.Almock()
            system_prompt = "worker"

            async def arun(self, input_text: str) -> Response[str]:
                ran.append("worker")
                return Response(content="worker output", cost=0.01)

        orch = _make_orchestrator([{"agent": "_WorkerAgent", "task": "do work"}])
        worker = _WorkerAgent()

        swarm = Swarm(
            agents=[orch, worker],
            goal="skip test",
            config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
        )

        def skip_handler(ctx: EventContext) -> None:
            handoff: SwarmHandoffContext | None = ctx.get("handoff")  # type: ignore[assignment]
            if handoff is not None:
                handoff.skip_next = True

        swarm.events.on(Hook.SWARM_AGENT_HANDOFF, skip_handler)

        result = await swarm.run()
        # Worker should NOT have run
        assert "worker" not in ran
        assert "worker output" not in result.content

    async def test_skip_next_false_normal_execution(self) -> None:
        """Default skip_next=False allows normal execution to continue."""
        ran: list[str] = []

        class _NormalWorker(Agent):
            model = Model.Almock()
            system_prompt = "worker"

            async def arun(self, input_text: str) -> Response[str]:
                ran.append("worker")
                return Response(content="normal output", cost=0.01)

        orch = _make_orchestrator([{"agent": "_NormalWorker", "task": "do work"}])
        worker = _NormalWorker()

        swarm = Swarm(
            agents=[orch, worker],
            goal="normal test",
            config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
        )

        def no_skip_handler(ctx: EventContext) -> None:
            # Don't set skip_next — default is False
            pass

        swarm.events.on(Hook.SWARM_AGENT_HANDOFF, no_skip_handler)

        result = await swarm.run()
        assert "worker" in ran
        assert "normal output" in result.content

    async def test_next_input_rewrite_is_received_by_worker(self) -> None:
        """Hook handler can rewrite next_input and the worker receives the new input."""
        received_input: list[str] = []

        class _EchoWorker(Agent):
            model = Model.Almock()
            system_prompt = "echo worker"

            async def arun(self, input_text: str) -> Response[str]:
                received_input.append(input_text)
                return Response(content=f"echoed: {input_text}", cost=0.01)

        orch = _make_orchestrator([{"agent": "_EchoWorker", "task": "original task"}])
        worker = _EchoWorker()

        swarm = Swarm(
            agents=[orch, worker],
            goal="input rewrite test",
            config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
        )

        def rewrite_input(ctx: EventContext) -> None:
            handoff: SwarmHandoffContext | None = ctx.get("handoff")  # type: ignore[assignment]
            if handoff is not None:
                handoff.next_input = "REWRITTEN TASK"

        swarm.events.on(Hook.SWARM_AGENT_HANDOFF, rewrite_input)

        await swarm.run()
        assert received_input == ["REWRITTEN TASK"]

    async def test_parallel_topology_handoff_context_not_emitted(self) -> None:
        """PARALLEL topology does not emit SWARM_AGENT_HANDOFF events."""
        handoff_events: list[EventContext] = []

        class _ParallelWorker(Agent):
            model = Model.Almock()
            system_prompt = "parallel worker"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="parallel result", cost=0.01)

        _ParallelWorker()
        b = _ParallelWorker()
        b.__class__.__name__ = "_ParallelWorker2"

        class _PW2(_ParallelWorker):
            pass

        swarm = Swarm(
            agents=[_ParallelWorker(), _PW2()],
            goal="parallel goal",
            config=SwarmConfig(topology=SwarmTopology.PARALLEL),
        )

        def capture_handoff(ctx: EventContext) -> None:
            handoff_events.append(ctx)

        swarm.events.on(Hook.SWARM_AGENT_HANDOFF, capture_handoff)
        await swarm.run()

        assert handoff_events == [], "PARALLEL topology should not emit SWARM_AGENT_HANDOFF events"
