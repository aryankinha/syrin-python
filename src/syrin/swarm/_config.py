"""SwarmConfig — swarm-level configuration and validation."""

from __future__ import annotations

from syrin.enums import FallbackStrategy, SwarmTopology


class SwarmConfig:
    """Configuration for a :class:`~syrin.swarm.Swarm`.

    Attributes:
        on_agent_failure: How to handle a failing agent.  Defaults to
            :attr:`~syrin.enums.FallbackStrategy.SKIP_AND_CONTINUE`.
        max_parallel_agents: Maximum agents allowed to run concurrently.
            Must be > 0.  Defaults to ``10``.
        timeout: Total swarm timeout in seconds, or ``None`` for no limit.
        topology: Execution topology for this swarm.  Defaults to
            :attr:`~syrin.enums.SwarmTopology.ORCHESTRATOR`.
        agent_timeout: Per-agent execution timeout in seconds.  Must be > 0
            when set.  ``None`` means no per-agent limit.
        max_agent_retries: Number of automatic retries per failing agent.
            Must be ≥ 0.  Defaults to ``0`` (no retries).
        debug: Enable verbose debug logging.  Defaults to ``False``.

    Example::

        config = SwarmConfig(
            topology=SwarmTopology.ORCHESTRATOR,
            on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE,
            max_parallel_agents=5,
            agent_timeout=30.0,
        )
    """

    def __init__(
        self,
        on_agent_failure: FallbackStrategy = FallbackStrategy.SKIP_AND_CONTINUE,
        max_parallel_agents: int = 10,
        timeout: float | None = None,
        topology: SwarmTopology = SwarmTopology.ORCHESTRATOR,
        agent_timeout: float | None = None,
        max_agent_retries: int = 0,
        debug: bool = False,
    ) -> None:
        """Initialise SwarmConfig.

        Args:
            on_agent_failure: Fallback strategy when an agent raises.
            max_parallel_agents: Maximum concurrent agents.  Must be > 0.
            timeout: Swarm-level wall-clock timeout in seconds.
            topology: Execution topology.
            agent_timeout: Per-agent wall-clock timeout in seconds.
                Must be > 0 when provided.
            max_agent_retries: Automatic retries per failing agent (≥ 0).
            debug: Enable verbose debug output.

        Raises:
            ValueError: If ``max_parallel_agents`` ≤ 0, ``agent_timeout`` ≤ 0,
                or ``max_agent_retries`` < 0.
        """
        if max_parallel_agents <= 0:
            raise ValueError(f"max_parallel_agents must be > 0, got {max_parallel_agents}")
        if agent_timeout is not None and agent_timeout <= 0:
            raise ValueError(f"agent_timeout must be > 0 when set, got {agent_timeout}")
        if max_agent_retries < 0:
            raise ValueError(f"max_agent_retries must be >= 0, got {max_agent_retries}")

        self.on_agent_failure: FallbackStrategy = on_agent_failure
        self.max_parallel_agents: int = max_parallel_agents
        self.timeout: float | None = timeout
        self.topology: SwarmTopology = topology
        self.agent_timeout: float | None = agent_timeout
        self.max_agent_retries: int = max_agent_retries
        self.debug: bool = debug


__all__ = ["SwarmConfig", "FallbackStrategy"]
