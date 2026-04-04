"""Tests for ORCHESTRATOR topology (Feature 2)."""

from __future__ import annotations

import json

import pytest

from syrin import Agent, Model
from syrin.enums import Hook, SwarmTopology
from syrin.events import EventContext
from syrin.response import Response
from syrin.swarm import Swarm, SwarmConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_orchestrator(task_list: list[dict[str, str]]) -> Agent:
    """Orchestrator that emits a JSON task list."""
    _tasks = task_list

    class _Orch(Agent):
        model = Model.Almock()
        system_prompt = "orchestrator"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=json.dumps(_tasks), cost=0.01)

    _Orch.__name__ = "Orchestrator"
    return _Orch()


def _make_worker(name: str, content: str) -> Agent:
    """Simple worker agent."""

    class _Worker(Agent):
        model = Model.Almock()
        system_prompt = "worker"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=0.005)

    _Worker.__name__ = name
    return _Worker()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.phase_5
class TestOrchestratorTopology:
    """ORCHESTRATOR topology — first agent decomposes, rest execute."""

    async def test_first_agent_runs_and_output_parsed_as_task_list(self) -> None:
        """The orchestrator runs first and its JSON output is parsed."""
        orch = _make_orchestrator([{"agent": "Worker", "task": "do something"}])
        worker = _make_worker("Worker", "worker output")

        swarm = Swarm(
            agents=[orch, worker],
            goal="test orchestration",
            config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
        )
        result = await swarm.run()
        assert "worker output" in result.content

    async def test_tasks_dispatched_to_named_agents(self) -> None:
        """Each task assignment is dispatched to the correct named agent."""
        received: dict[str, str] = {}

        class _WriterAgent(Agent):
            model = Model.Almock()
            system_prompt = "writer"

            async def arun(self, input_text: str) -> Response[str]:
                received["writer"] = input_text
                return Response(content="written text", cost=0.01)

        class _ReviewerAgent(Agent):
            model = Model.Almock()
            system_prompt = "reviewer"

            async def arun(self, input_text: str) -> Response[str]:
                received["reviewer"] = input_text
                return Response(content="review notes", cost=0.01)

        orch = _make_orchestrator(
            [
                {"agent": "_WriterAgent", "task": "write a draft"},
                {"agent": "_ReviewerAgent", "task": "review the draft"},
            ]
        )
        writer = _WriterAgent()
        reviewer = _ReviewerAgent()

        swarm = Swarm(
            agents=[orch, writer, reviewer],
            goal="write and review",
            config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
        )
        await swarm.run()
        assert received["writer"] == "write a draft"
        assert received["reviewer"] == "review the draft"

    async def test_results_aggregated_into_swarm_result(self) -> None:
        """All worker results are present in SwarmResult."""
        orch = _make_orchestrator(
            [
                {"agent": "Alpha", "task": "task alpha"},
                {"agent": "Beta", "task": "task beta"},
            ]
        )
        alpha = _make_worker("Alpha", "alpha done")
        beta = _make_worker("Beta", "beta done")

        swarm = Swarm(
            agents=[orch, alpha, beta],
            goal="do both tasks",
            config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
        )
        result = await swarm.run()
        assert "alpha done" in result.content
        assert "beta done" in result.content

    async def test_unknown_agent_name_skipped_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Unknown agent name in orchestrator output → skipped, warning emitted."""
        import logging

        orch = _make_orchestrator(
            [
                {"agent": "NonExistentAgent", "task": "impossible task"},
                {"agent": "Worker", "task": "real task"},
            ]
        )
        worker = _make_worker("Worker", "worker done")

        swarm = Swarm(
            agents=[orch, worker],
            goal="handle unknown agent",
            config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
        )
        with caplog.at_level(logging.WARNING):
            result = await swarm.run()

        assert "worker done" in result.content
        assert any("NonExistentAgent" in r.message for r in caplog.records)

    async def test_no_task_assignments_returns_orchestrator_output(self) -> None:
        """When orchestrator emits no tasks, its own output is returned."""

        class _FreeFormOrchestrator(Agent):
            model = Model.Almock()
            system_prompt = "free form orchestrator"

            async def arun(self, input_text: str) -> Response[str]:
                return Response(content="This is a free-form answer.", cost=0.01)

        orch = _FreeFormOrchestrator()
        worker = _make_worker("Worker", "worker output")

        swarm = Swarm(
            agents=[orch, worker],
            goal="answer freely",
            config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
        )
        result = await swarm.run()
        assert "This is a free-form answer." in result.content
        # Worker should NOT have run
        assert "worker output" not in result.content

    async def test_cost_breakdown_contains_all_agents(self) -> None:
        """cost_breakdown includes the orchestrator and all workers."""
        orch = _make_orchestrator([{"agent": "Worker", "task": "task"}])
        worker = _make_worker("Worker", "done")

        swarm = Swarm(
            agents=[orch, worker],
            goal="cost test",
            config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
        )
        result = await swarm.run()
        assert "Orchestrator" in result.cost_breakdown
        assert "Worker" in result.cost_breakdown

    async def test_swarm_started_and_ended_events_fired(self) -> None:
        """SWARM_STARTED and SWARM_ENDED events are fired."""
        fired: list[str] = []

        orch = _make_orchestrator([])
        swarm = Swarm(
            agents=[orch],
            goal="event test",
            config=SwarmConfig(topology=SwarmTopology.ORCHESTRATOR),
        )

        def on_started(ctx: EventContext) -> None:
            fired.append("started")

        def on_ended(ctx: EventContext) -> None:
            fired.append("ended")

        swarm.events.on(Hook.SWARM_STARTED, on_started)
        swarm.events.on(Hook.SWARM_ENDED, on_ended)

        await swarm.run()
        assert "started" in fired
        assert "ended" in fired
