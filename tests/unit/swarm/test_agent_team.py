"""Tests for Agent.team — hierarchical swarm composition (Feature 1)."""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.enums import SwarmTopology
from syrin.response import Response
from syrin.swarm import Swarm, SwarmConfig

# ---------------------------------------------------------------------------
# Stub agents
# ---------------------------------------------------------------------------


class _Alpha(Agent):
    model = Model.Almock()
    system_prompt = "alpha"

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="alpha result", cost=0.01)


class _Beta(Agent):
    model = Model.Almock()
    system_prompt = "beta"

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="beta result", cost=0.01)


class _Gamma(Agent):
    model = Model.Almock()
    system_prompt = "gamma"

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="gamma result", cost=0.01)


class _ParentWithTeam(Agent):
    model = Model.Almock()
    system_prompt = "parent"
    team = [_Alpha, _Beta]

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="parent result", cost=0.01)


class _LeafAgent(Agent):
    """Agent with no team — default None."""

    model = Model.Almock()
    system_prompt = "leaf"

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="leaf result", cost=0.01)


# CEO → CTO → Engineer hierarchy
class _Engineer(Agent):
    model = Model.Almock()
    system_prompt = "engineer"

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="code", cost=0.01)


class _CTO(Agent):
    model = Model.Almock()
    system_prompt = "cto"
    team = [_Engineer]

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="tech decisions", cost=0.01)


class _CEO(Agent):
    model = Model.Almock()
    system_prompt = "ceo"
    team = [_CTO]

    async def arun(self, input_text: str) -> Response[str]:
        return Response(content="strategy", cost=0.01)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.phase_5
class TestAgentTeamExpansion:
    """Agent.team ClassVar causes auto-spawning of sub-agents in Swarm."""

    def test_team_members_are_added_to_swarm(self) -> None:
        """Agents listed in team= are instantiated and added to the swarm pool."""
        parent = _ParentWithTeam()
        swarm = Swarm(agents=[parent], goal="test goal")
        agent_names = {type(a).__name__ for a in swarm._agents}
        assert "_Alpha" in agent_names
        assert "_Beta" in agent_names

    def test_team_member_count(self) -> None:
        """Swarm agent count includes original agent + all team members."""
        parent = _ParentWithTeam()
        swarm = Swarm(agents=[parent], goal="test goal")
        # 1 parent + 2 team members
        assert swarm.agent_count == 3

    def test_no_team_default_no_expansion(self) -> None:
        """Agent with no team (default None) — no extra agents spawned."""
        leaf = _LeafAgent()
        swarm = Swarm(agents=[leaf], goal="test goal")
        assert swarm.agent_count == 1

    def test_team_members_are_fresh_instances(self) -> None:
        """Team member classes are instantiated fresh for each Swarm."""
        parent1 = _ParentWithTeam()
        parent2 = _ParentWithTeam()
        swarm1 = Swarm(agents=[parent1], goal="goal 1")
        swarm2 = Swarm(agents=[parent2], goal="goal 2")

        swarm1_alpha = next(a for a in swarm1._agents if type(a).__name__ == "_Alpha")
        swarm2_alpha = next(a for a in swarm2._agents if type(a).__name__ == "_Alpha")
        assert swarm1_alpha is not swarm2_alpha

    def test_nested_team_hierarchy_ceo_cto_engineer(self) -> None:
        """CEO.team=[CTO], CTO.team=[Engineer] — all three levels are present."""
        ceo = _CEO()
        swarm = Swarm(agents=[ceo], goal="run company")
        agent_names = {type(a).__name__ for a in swarm._agents}
        assert "_CEO" in agent_names
        assert "_CTO" in agent_names
        assert "_Engineer" in agent_names

    def test_supervisor_id_set_on_team_member(self) -> None:
        """Team member _supervisor_id is set to the parent's agent_id."""
        parent = _ParentWithTeam()
        parent_id = getattr(parent, "agent_id", type(parent).__name__)
        swarm = Swarm(agents=[parent], goal="test goal")

        for member in swarm._agents:
            if type(member).__name__ in ("_Alpha", "_Beta"):
                supervisor = getattr(member, "_supervisor_id", None)
                assert supervisor == parent_id, (
                    f"Expected _supervisor_id={parent_id!r}, got {supervisor!r}"
                )

    def test_team_map_records_parent_to_children(self) -> None:
        """swarm._team_map maps parent agent_id → list of child agent_ids."""
        parent = _ParentWithTeam()
        parent_id = getattr(parent, "agent_id", type(parent).__name__)
        swarm = Swarm(agents=[parent], goal="test goal")

        assert parent_id in swarm._team_map
        assert len(swarm._team_map[parent_id]) == 2

    async def test_parallel_swarm_with_team_runs_all_agents(self) -> None:
        """Swarm.run() with team expansion runs all expanded agents."""
        parent = _ParentWithTeam()
        swarm = Swarm(
            agents=[parent],
            goal="complete the task",
            config=SwarmConfig(topology=SwarmTopology.PARALLEL),
        )
        result = await swarm.run()
        # Parent + 2 team members all return content
        assert "parent result" in result.content
        assert "alpha result" in result.content
        assert "beta result" in result.content
