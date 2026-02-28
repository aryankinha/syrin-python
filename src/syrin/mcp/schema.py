"""MCP schema conversion — ToolSpec ↔ MCP Tool."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


def tool_spec_to_mcp(t: Any) -> dict[str, Any]:
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


def mcp_tool_to_tool_spec(mcp_tool: dict[str, Any], call_fn: Any) -> Any:
    """Convert MCP tool dict to Syrin ToolSpec (requires call_fn to invoke remote)."""
    from syrin.tool import ToolSpec

    schema = mcp_tool.get("inputSchema") or {}
    props = schema.get("properties") or {}
    req = schema.get("required") or []
    params = {"type": "object", "properties": props, "required": req}
    return ToolSpec(
        name=mcp_tool.get("name", "unknown"),
        description=mcp_tool.get("description", "") or "",
        parameters_schema=params,
        func=call_fn,
    )
