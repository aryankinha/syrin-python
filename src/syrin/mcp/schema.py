"""MCP schema conversion — ToolSpec ↔ MCP Tool."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def validate_tool_arguments(spec: object, arguments: dict[str, object]) -> None:
    """Validate arguments against tool's parameters_schema. Raises jsonschema.ValidationError."""
    schema = getattr(spec, "parameters_schema", None) or {}
    if not schema or not schema.get("properties"):
        return
    import jsonschema

    full_schema = {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
        "additionalProperties": schema.get("additionalProperties", True),
    }
    jsonschema.validate(arguments, full_schema)


def tool_spec_to_mcp(t: object) -> dict[str, object]:
    """Convert Syrin ToolSpec to MCP tool schema (name, description, inputSchema)."""
    return {
        "name": getattr(t, "name", "unknown"),
        "description": getattr(t, "description", "") or "",
        "inputSchema": {
            "type": "object",
            "properties": (getattr(t, "parameters_schema", None) or {}).get("properties", {}),
            "required": (getattr(t, "parameters_schema", None) or {}).get("required", []),
        },
    }


def mcp_tool_to_tool_spec(mcp_tool: dict[str, object], call_fn: object) -> object:
    """Convert MCP tool dict to Syrin ToolSpec (requires call_fn to invoke remote)."""
    from syrin.tool import ToolSpec

    schema = mcp_tool.get("inputSchema") or {}
    props = schema.get("properties") or {}  # type: ignore[attr-defined]
    req = schema.get("required") or []  # type: ignore[attr-defined]
    params = {"type": "object", "properties": props, "required": req}
    return ToolSpec(
        name=mcp_tool.get("name", "unknown"),  # type: ignore[arg-type]
        description=mcp_tool.get("description", "") or "",  # type: ignore[arg-type]
        parameters_schema=params,
        func=call_fn,  # type: ignore[arg-type]
    )
