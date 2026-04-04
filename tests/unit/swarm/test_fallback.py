"""P2-T8: Graceful degradation and blast radius containment."""

from __future__ import annotations

import pytest

from syrin import Agent, Model
from syrin.enums import FallbackStrategy, Hook, SwarmTopology
from syrin.events import EventContext
from syrin.response import Response
from syrin.swarm import Swarm, SwarmConfig


def _make_agent(content: str, cost: float = 0.01) -> Agent:
    """Stub agent returning *content*."""

    class _Stub(Agent):
        model = Model.Almock()
        system_prompt = "stub"

        async def arun(self, input_text: str) -> Response[str]:
            return Response(content=content, cost=cost)

    _Stub.__name__ = f"Stub_{content[:8]}"
    return _Stub()


def _make_failing_agent(name: str = "Fail") -> Agent:
    """Agent that always raises."""

    class _Fail(Agent):
        model = Model.Almock()
        system_prompt = "fail"

        async def arun(self, input_text: str) -> Response[str]:
            raise RuntimeError(f"{name} blew up")

    _Fail.__name__ = name
    return _Fail()


@pytest.mark.phase_2
class TestSkipAndContinue:
    """FallbackStrategy.SKIP_AND_CONTINUE — failed agent skipped, swarm continues."""

    async def test_skip_and_continue_returns_partial(self) -> None:
        """Swarm completes with partial result when one agent fails."""
        good = _make_agent("good output")
        bad = _make_failing_agent("BomberAgent")
        swarm = Swarm(
            agents=[good, bad],
            goal="partial test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE
            ),
        )
        result = await swarm.run()
        assert "good output" in result.content

    async def test_partial_results_not_empty(self) -> None:
        """SwarmResult.partial_results contains the successful agent's output."""
        good = _make_agent("survivor")
        bad = _make_failing_agent()
        swarm = Swarm(
            agents=[good, bad],
            goal="survivor test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE
            ),
        )
        result = await swarm.run()
        assert len(result.partial_results) >= 1

    async def test_all_fail_skip_returns_empty_content(self) -> None:
        """If all agents fail with SKIP_AND_CONTINUE, SwarmResult has empty/minimal content."""
        bad1 = _make_failing_agent("Bad1")
        bad2 = _make_failing_agent("Bad2")
        swarm = Swarm(
            agents=[bad1, bad2],
            goal="all-fail test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE
            ),
        )
        result = await swarm.run()
        # Should not raise; content may be empty
        assert isinstance(result.content, str)


@pytest.mark.phase_2
class TestAbortSwarm:
    """FallbackStrategy.ABORT_SWARM — one failure stops all agents."""

    async def test_abort_raises_on_failure(self) -> None:
        """With ABORT_SWARM, any agent failure raises an exception."""
        good = _make_agent("good")
        bad = _make_failing_agent("AbortBomb")
        swarm = Swarm(
            agents=[good, bad],
            goal="abort test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.ABORT_SWARM
            ),
        )
        with pytest.raises((RuntimeError, ValueError)):
            await swarm.run()

    async def test_abort_does_not_swallow_exception(self) -> None:
        """ABORT_SWARM propagates a recognisable error."""
        bad = _make_failing_agent("CriticalFail")
        swarm = Swarm(
            agents=[bad],
            goal="abort propagate",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.ABORT_SWARM
            ),
        )
        with pytest.raises(Exception) as exc_info:
            await swarm.run()
        # Should mention the failure somehow
        assert exc_info.value is not None


@pytest.mark.phase_2
class TestIsolateAndContinue:
    """FallbackStrategy.ISOLATE_AND_CONTINUE — failed agent isolated, swarm continues."""

    async def test_isolate_continues_with_good_agents(self) -> None:
        """With ISOLATE_AND_CONTINUE, good agents still produce output."""
        good = _make_agent("isolated output")
        bad = _make_failing_agent("Isolated")
        swarm = Swarm(
            agents=[good, bad],
            goal="isolate test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL,
                on_agent_failure=FallbackStrategy.ISOLATE_AND_CONTINUE,
            ),
        )
        result = await swarm.run()
        assert "isolated output" in result.content


@pytest.mark.phase_2
class TestFailureHooks:
    """Failure hooks fire correctly."""

    async def test_agent_failed_hook_fires(self) -> None:
        """Hook.AGENT_FAILED fires with context when an agent fails."""
        failed_events: list[EventContext] = []
        bad = _make_failing_agent("FailHook")
        swarm = Swarm(
            agents=[bad],
            goal="hook test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE
            ),
        )
        swarm.events.on(Hook.AGENT_FAILED, lambda ctx: failed_events.append(ctx))
        await swarm.run()
        assert len(failed_events) >= 1

    async def test_agent_failed_hook_has_agent_name(self) -> None:
        """AGENT_FAILED context includes the failing agent's name."""
        failed_events: list[EventContext] = []
        bad = _make_failing_agent("NamedFail")
        swarm = Swarm(
            agents=[bad],
            goal="name test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE
            ),
        )
        swarm.events.on(Hook.AGENT_FAILED, lambda ctx: failed_events.append(ctx))
        await swarm.run()
        assert len(failed_events) >= 1
        ctx = failed_events[0]
        assert getattr(ctx, "agent_name", None) is not None

    async def test_blast_radius_hook_fires_on_failure(self) -> None:
        """Hook.BLAST_RADIUS_COMPUTED fires after an agent failure."""
        blast_events: list[EventContext] = []
        bad = _make_failing_agent("BlastAgent")
        swarm = Swarm(
            agents=[bad, _make_agent("ok")],
            goal="blast test",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE
            ),
        )
        swarm.events.on(Hook.BLAST_RADIUS_COMPUTED, lambda ctx: blast_events.append(ctx))
        await swarm.run()
        assert len(blast_events) >= 1

    async def test_swarm_partial_result_hook_fires(self) -> None:
        """Hook.SWARM_PARTIAL_RESULT fires when swarm completes with skipped agents."""
        partial_events: list[EventContext] = []
        bad = _make_failing_agent()
        good = _make_agent("kept")
        swarm = Swarm(
            agents=[good, bad],
            goal="partial hook",
            config=SwarmConfig(
                topology=SwarmTopology.PARALLEL, on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE
            ),
        )
        swarm.events.on(Hook.SWARM_PARTIAL_RESULT, lambda ctx: partial_events.append(ctx))
        await swarm.run()
        assert len(partial_events) >= 1
