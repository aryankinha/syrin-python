"""Swarm topologies — orchestrator, parallel, consensus, reflection."""

from syrin.swarm.topologies._consensus import (
    ConsensusConfig,
    ConsensusResult,
    ConsensusVote,
    run_consensus,
)
from syrin.swarm.topologies._parallel import run_parallel
from syrin.swarm.topologies._reflection import (
    ReflectionConfig,
    ReflectionResult,
    RoundOutput,
    run_reflection,
)

__all__ = [
    "ConsensusConfig",
    "ConsensusResult",
    "ConsensusVote",
    "ReflectionConfig",
    "ReflectionResult",
    "RoundOutput",
    "run_consensus",
    "run_parallel",
    "run_reflection",
]
