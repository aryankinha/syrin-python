"""Remote config schema and override helpers for Agent. Used by serve/playground."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from syrin.agent import Agent


def agent_guardrails_schema_and_values(agent: Agent) -> tuple[Any, dict[str, object]]:  # type: ignore[explicit-any]
    """Build (ConfigSchema, current_values) for guardrails section (enable/disable by name)."""
    from syrin.remote._types import ConfigSchema, FieldSchema

    guardrail_list = getattr(agent._guardrails, "_guardrails", [])
    fields: list[object] = []
    current_values: dict[str, object] = {}
    disabled: set[str] = getattr(agent, "_guardrails_disabled", set()) or set()
    for g in guardrail_list:
        name = getattr(g, "name", getattr(g, "__class__", type(g)).__name__)
        path = f"guardrails.{name}.enabled"
        fields.append(
            FieldSchema(
                name=f"{name}.enabled",
                path=path,
                type="bool",
                default=True,
                description=None,
                constraints={},
                enum_values=None,
                children=None,
                remote_excluded=False,
            )
        )
        current_values[path] = name not in disabled
    return (ConfigSchema(section="guardrails", class_name="Agent", fields=fields), current_values)  # type: ignore[arg-type]


def agent_template_vars_schema_and_values(agent: Agent) -> tuple[Any, dict[str, object]]:  # type: ignore[explicit-any]
    """Build (ConfigSchema, current_values) for template_variables section."""
    from syrin.remote._types import ConfigSchema, FieldSchema

    pv = getattr(agent, "_template_vars", {}) or {}
    fields: list[object] = []
    current_values: dict[str, object] = {}
    for key, val in pv.items():
        path = f"template_variables.{key}"
        fields.append(
            FieldSchema(
                name=key,
                path=path,
                type="str",
                default=None,
                description=None,
                constraints={},
                enum_values=None,
                children=None,
                remote_excluded=False,
            )
        )
        current_values[path] = val
    return (
        ConfigSchema(section="template_variables", class_name="Agent", fields=fields),  # type: ignore[arg-type]
        current_values,
    )


def agent_tools_schema_and_values(agent: Agent) -> tuple[Any, dict[str, object]]:  # type: ignore[explicit-any]
    """Build (ConfigSchema, current_values) for tools section (enable/disable by name)."""
    from syrin.remote._types import ConfigSchema, FieldSchema

    tools_list = getattr(agent, "_tools", []) or []
    disabled: set[str] = getattr(agent, "_tools_disabled", set()) or set()
    fields: list[object] = []
    current_values: dict[str, object] = {}
    for t in tools_list:
        name = getattr(t, "name", "")
        if not name:
            continue
        path = f"tools.{name}.enabled"
        fields.append(
            FieldSchema(
                name=f"{name}.enabled",
                path=path,
                type="bool",
                default=True,
                description=None,
                constraints={},
                enum_values=None,
                children=None,
                remote_excluded=False,
            )
        )
        current_values[path] = name not in disabled
    return (ConfigSchema(section="tools", class_name="Agent", fields=fields), current_values)  # type: ignore[arg-type]


def agent_mcp_schema_and_values(agent: Agent) -> tuple[Any, dict[str, object]]:  # type: ignore[explicit-any]
    """Build (ConfigSchema, current_values) for mcp section (enable/disable by index)."""
    from syrin.remote._types import ConfigSchema, FieldSchema

    mcp_list = getattr(agent, "_mcp_instances", []) or []
    disabled: set[int] = getattr(agent, "_mcp_disabled", set()) or set()
    fields: list[object] = []
    current_values: dict[str, object] = {}
    for i in range(len(mcp_list)):
        path = f"mcp.{i}.enabled"
        fields.append(
            FieldSchema(
                name=f"{i}.enabled",
                path=path,
                type="bool",
                default=True,
                description=None,
                constraints={},
                enum_values=None,
                children=None,
                remote_excluded=False,
            )
        )
        current_values[path] = i not in disabled
    return (ConfigSchema(section="mcp", class_name="Agent", fields=fields), current_values)  # type: ignore[arg-type]


def apply_guardrails_overrides(agent: Agent, pairs: list[tuple[str, object]]) -> None:
    """Apply guardrails.*.enabled overrides to agent._guardrails_disabled."""
    disabled: set[str] | None = getattr(agent, "_guardrails_disabled", None)
    if disabled is None:
        object.__setattr__(agent, "_guardrails_disabled", set())
        disabled = agent._guardrails_disabled
    for path, value in pairs:
        if not path.startswith("guardrails.") or not path.endswith(".enabled"):
            continue
        name = path[: -len(".enabled")].split(".", 1)[1]
        if name and (value is True or value is False):
            if value:
                disabled.discard(name)
            else:
                disabled.add(name)


def apply_template_vars_overrides(agent: Agent, pairs: list[tuple[str, object]]) -> None:
    """Apply template_variables.* overrides to agent._template_vars."""
    pv = getattr(agent, "_template_vars", None)
    if pv is None:
        object.__setattr__(agent, "_template_vars", {})
        pv = agent._template_vars
    for path, value in pairs:
        if not path.startswith("template_variables."):
            continue
        key = path.split(".", 1)[1]
        if key:
            pv[key] = value if value is not None else ""


def apply_tools_overrides(agent: Agent, pairs: list[tuple[str, object]]) -> None:
    """Apply tools.*.enabled overrides to agent._tools_disabled."""
    disabled: set[str] | None = getattr(agent, "_tools_disabled", None)
    if disabled is None:
        object.__setattr__(agent, "_tools_disabled", set())
        disabled = agent._tools_disabled
    for path, value in pairs:
        if not path.startswith("tools.") or not path.endswith(".enabled"):
            continue
        name = path[: -len(".enabled")].split(".", 1)[1]
        if name and (value is True or value is False):
            if value:
                disabled.discard(name)
            else:
                disabled.add(name)


def apply_mcp_overrides(agent: Agent, pairs: list[tuple[str, object]]) -> None:
    """Apply mcp.*.enabled overrides to agent._mcp_disabled."""
    disabled: set[int] | None = getattr(agent, "_mcp_disabled", None)
    if disabled is None:
        object.__setattr__(agent, "_mcp_disabled", set())
        disabled = agent._mcp_disabled
    for path, value in pairs:
        if not path.startswith("mcp.") or not path.endswith(".enabled"):
            continue
        try:
            i = int(path.split(".")[1])
        except (IndexError, ValueError):
            continue
        if value is True or value is False:
            if value:
                disabled.discard(i)
            else:
                disabled.add(i)
