"""Internal: TOON and tool schema format conversion. Not part of public API."""

from __future__ import annotations

import json

from syrin.enums import DocFormat


def schema_to_toon(schema: dict[str, object], indent: int = 0) -> str:
    """Convert a JSON schema to TOON format (token-efficient).

    Args:
        schema: JSON schema dict (type, properties, required, etc.).
        indent: Indentation level for nesting.

    Returns:
        TOON-format string (~40% fewer tokens than JSON).
    """
    lines: list[str] = []
    prefix = "  " * indent

    if not isinstance(schema, dict):
        return f"{prefix}{json.dumps(schema)}"

    for key, value in schema.items():
        if key == "type" and isinstance(value, str):
            lines.append(f"{prefix}{key}: {value}")
        elif key == "properties" and isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            for prop_name, prop_schema in value.items():
                lines.append(f"{prefix}  {prop_name}:")
                prop_lines = schema_to_toon(prop_schema, indent + 2).split("\n")
                for line in prop_lines:
                    if line.strip():
                        lines.append(line)
        elif key == "required" and isinstance(value, list):
            if value:
                lines.append(f"{prefix}{key}[{len(value)}]: {','.join(value)}")
            else:
                lines.append(f"{prefix}{key}: []")
        elif key == "items" and isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            item_lines = schema_to_toon(value, indent + 1).split("\n")
            for line in item_lines:
                if line.strip():
                    lines.append(line)
        elif isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            sub_lines = schema_to_toon(value, indent + 1).split("\n")
            for line in sub_lines:
                if line.strip():
                    lines.append(line)
        elif isinstance(value, list):
            if value:
                lines.append(f"{prefix}{key}: {json.dumps(value)}")
            else:
                lines.append(f"{prefix}{key}: []")
        elif isinstance(value, str):
            if value:
                lines.append(f"{prefix}{key}: {value}")
            else:
                lines.append(f"{prefix}{key}:")
        elif value is None:
            lines.append(f"{prefix}{key}:")
        else:
            lines.append(f"{prefix}{key}: {json.dumps(value)}")

    return "\n".join(lines)


def tool_schema_to_format_dict(
    name: str,
    description: str,
    parameters_schema: dict[str, object],
    format: DocFormat = DocFormat.TOON,
) -> dict[str, object]:
    """Build provider-style tool schema dict from components (no ToolSpec dependency).

    Args:
        name: Tool name.
        description: Tool description.
        parameters_schema: JSON schema for parameters.
        format: DocFormat.TOON (default) or DocFormat.JSON.

    Returns:
        Provider-ready schema dict (type/function/name/description/parameters).
    """
    if format == DocFormat.TOON:
        toon_params = schema_to_toon(parameters_schema or {})
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description or "",
                "parameters": toon_params,
            },
        }
    if format == DocFormat.YAML:
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError:
            return {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description or "",
                    "parameters": json.dumps(parameters_schema or {}),
                },
            }
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description or "",
                "parameters": yaml.dump(parameters_schema or {}),
            },
        }
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description or "",
            "parameters": parameters_schema or {"type": "object", "properties": {}},
        },
    }
