"""Protocol for per-class remote config: schema and apply ownership."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from syrin.remote._types import ConfigSchema


@runtime_checkable
class RemoteConfigurable(Protocol):
    """Protocol for config objects that own their remote config schema and apply logic.

    Implement this on Budget, Memory, Context, CheckpointConfig, APIRateLimit,
    Output, CircuitBreaker, and on Agent for the \"agent\" section. The aggregator
    (extract_agent_schema / ConfigResolver) discovers sections via
    REMOTE_CONFIG_SECTIONS and delegates to each configurable.
    """

    def get_remote_config_schema(self, section_key: str) -> tuple[ConfigSchema, dict[str, object]]:
        """Return (schema for this section, current_values for this section)."""
        ...

    def apply_remote_overrides(
        self,
        agent: object,
        pairs: list[tuple[str, object]],
        section_schema: ConfigSchema,
    ) -> None:
        """Apply override (path, value) pairs for this section to the agent."""
        ...
