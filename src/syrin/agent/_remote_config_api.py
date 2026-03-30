"""Remote-config use-case helpers for Agent public methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from syrin.agent._remote_config import (
    agent_guardrails_schema_and_values as _agent_guardrails_schema_and_values,
)
from syrin.agent._remote_config import (
    agent_mcp_schema_and_values as _agent_mcp_schema_and_values,
)
from syrin.agent._remote_config import (
    agent_template_vars_schema_and_values as _agent_template_vars_schema_and_values,
)
from syrin.agent._remote_config import (
    agent_tools_schema_and_values as _agent_tools_schema_and_values,
)
from syrin.agent._remote_config import (
    apply_guardrails_overrides as _apply_guardrails_overrides,
)
from syrin.agent._remote_config import apply_mcp_overrides as _apply_mcp_overrides
from syrin.agent._remote_config import (
    apply_template_vars_overrides as _apply_template_vars_overrides,
)
from syrin.agent._remote_config import apply_tools_overrides as _apply_tools_overrides

if TYPE_CHECKING:
    from syrin.agent import Agent


def get_remote_config_schema(agent: Agent, section_key: str) -> tuple[object, dict[str, object]]:
    """Return the schema and current values for an agent-owned remote config section."""
    from syrin.remote._schema import get_agent_section_schema_and_values
    from syrin.remote._types import ConfigSchema

    if section_key == "agent":
        return get_agent_section_schema_and_values(agent)
    if section_key == "guardrails":
        return _agent_guardrails_schema_and_values(agent)
    if section_key == "template_variables":
        return _agent_template_vars_schema_and_values(agent)
    if section_key == "tools":
        return _agent_tools_schema_and_values(agent)
    if section_key == "mcp":
        return _agent_mcp_schema_and_values(agent)
    return (ConfigSchema(section=section_key, class_name="Agent", fields=[]), {})


def apply_remote_overrides(
    agent: Agent,
    pairs: list[tuple[str, object]],
    section_schema: object,
) -> None:
    """Apply remote configuration overrides for an agent-owned section."""
    from syrin.remote._resolver_helpers import apply_agent_section_overrides
    from syrin.remote._types import ConfigSchema

    section = getattr(section_schema, "section", None)
    if section == "agent":
        apply_agent_section_overrides(agent, pairs, cast(ConfigSchema, section_schema))
        return
    if section == "guardrails":
        _apply_guardrails_overrides(agent, pairs)
        return
    if section == "template_variables":
        _apply_template_vars_overrides(agent, pairs)
        return
    if section == "tools":
        _apply_tools_overrides(agent, pairs)
        return
    if section == "mcp":
        _apply_mcp_overrides(agent, pairs)
        return
