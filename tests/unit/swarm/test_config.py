"""P2-T3: SwarmConfig — swarm-level configuration and validation."""

from __future__ import annotations

import pytest

from syrin.enums import FallbackStrategy, SwarmTopology
from syrin.swarm._config import SwarmConfig


@pytest.mark.phase_2
class TestSwarmConfigDefaults:
    """SwarmConfig() has sensible defaults (no required fields)."""

    def test_no_required_fields(self) -> None:
        """SwarmConfig() constructs without any arguments."""
        config = SwarmConfig()
        assert config is not None

    def test_default_on_agent_failure(self) -> None:
        """Default on_agent_failure is SKIP_AND_CONTINUE."""
        config = SwarmConfig()
        assert config.on_agent_failure == FallbackStrategy.SKIP_AND_CONTINUE

    def test_default_max_parallel_agents_positive(self) -> None:
        """Default max_parallel_agents is a positive integer."""
        config = SwarmConfig()
        assert config.max_parallel_agents > 0

    def test_default_timeout_is_none(self) -> None:
        """Default timeout is None (no limit)."""
        config = SwarmConfig()
        assert config.timeout is None

    def test_default_topology(self) -> None:
        """Default topology is ORCHESTRATOR."""
        config = SwarmConfig()
        assert config.topology == SwarmTopology.ORCHESTRATOR

    def test_default_agent_timeout_none(self) -> None:
        """Default agent_timeout is None (no per-agent limit)."""
        config = SwarmConfig()
        assert config.agent_timeout is None

    def test_default_max_retries_zero(self) -> None:
        """Default max_agent_retries is 0 (no automatic retry)."""
        config = SwarmConfig()
        assert config.max_agent_retries == 0


@pytest.mark.phase_2
class TestSwarmConfigValidation:
    """SwarmConfig validates its fields."""

    def test_valid_fallback_strategy(self) -> None:
        """on_agent_failure accepts any FallbackStrategy value."""
        config = SwarmConfig(on_agent_failure=FallbackStrategy.SKIP_AND_CONTINUE)
        assert config.on_agent_failure == FallbackStrategy.SKIP_AND_CONTINUE

    def test_max_parallel_agents_zero_raises(self) -> None:
        """max_parallel_agents=0 raises ValueError."""
        with pytest.raises(ValueError):
            SwarmConfig(max_parallel_agents=0)

    def test_max_parallel_agents_negative_raises(self) -> None:
        """Negative max_parallel_agents raises ValueError."""
        with pytest.raises(ValueError):
            SwarmConfig(max_parallel_agents=-1)

    def test_agent_timeout_negative_raises(self) -> None:
        """Negative agent_timeout raises ValueError."""
        with pytest.raises(ValueError):
            SwarmConfig(agent_timeout=-1)

    def test_agent_timeout_zero_raises(self) -> None:
        """agent_timeout=0 raises ValueError (must be positive or None)."""
        with pytest.raises(ValueError):
            SwarmConfig(agent_timeout=0)

    def test_valid_agent_timeout(self) -> None:
        """Positive agent_timeout is valid."""
        config = SwarmConfig(agent_timeout=60.0)
        assert config.agent_timeout == pytest.approx(60.0)

    def test_valid_topology(self) -> None:
        """topology accepts any SwarmTopology value."""
        config = SwarmConfig(topology=SwarmTopology.ORCHESTRATOR)
        assert config.topology == SwarmTopology.ORCHESTRATOR

    def test_max_agent_retries_negative_raises(self) -> None:
        """Negative max_agent_retries raises ValueError."""
        with pytest.raises(ValueError):
            SwarmConfig(max_agent_retries=-1)


@pytest.mark.phase_2
class TestSwarmConfigFields:
    """All SwarmConfig fields are documented."""

    def test_has_on_agent_failure_field(self) -> None:
        """on_agent_failure field exists and stores correctly."""
        config = SwarmConfig(on_agent_failure=FallbackStrategy.ABORT_SWARM)
        assert config.on_agent_failure == FallbackStrategy.ABORT_SWARM

    def test_has_topology_field(self) -> None:
        """topology field exists and stores SwarmTopology."""
        config = SwarmConfig(topology=SwarmTopology.WORKFLOW)
        assert config.topology == SwarmTopology.WORKFLOW

    def test_has_max_parallel_agents_field(self) -> None:
        """max_parallel_agents field exists."""
        config = SwarmConfig(max_parallel_agents=5)
        assert config.max_parallel_agents == 5

    def test_has_timeout_field(self) -> None:
        """timeout field exists."""
        config = SwarmConfig(timeout=300.0)
        assert config.timeout == pytest.approx(300.0)

    def test_has_debug_field(self) -> None:
        """debug field exists and defaults to False."""
        config = SwarmConfig()
        assert config.debug is False

    def test_debug_can_be_enabled(self) -> None:
        """debug=True is valid."""
        config = SwarmConfig(debug=True)
        assert config.debug is True
