"""Tool decorator and schema generation for agent tools."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Union, get_type_hints

from pydantic import BaseModel, Field, PrivateAttr

from syrin.enums import DocFormat
from syrin.tool._schema import schema_to_toon as _schema_to_toon
from syrin.tool._schema import tool_schema_to_format_dict

_TYPE_TO_JSON: dict[type[object], str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


class ToolSpec(BaseModel):  # type: ignore[explicit-any]
    """Spec for a tool the model can call. Usually built via @tool decorator or syrin.tool().

    Attributes:
        name: Tool name. Model uses this in tool_calls.name.
        description: Description for the model. Be specific about when and why to call.
        parameters_schema: JSON schema for parameters. Model uses this to generate args.
        func: Python function to run. Receives parsed arguments from the model.
        requires_approval: If True, block execution until human approval via ApprovalGate.
        inject_run_context: If True, first param is ctx: RunContext; agent injects at runtime.
    """

    name: str = Field(..., description="Tool name (used in tool_calls.name)")
    description: str = Field(
        default="",
        description=(
            "Description for the model. The LLM uses this to decide when to call this tool—"
            "be specific about when and why. Example: 'Search web for current facts. "
            "Use when the user asks about news, events, or recent information.'"
        ),
    )
    parameters_schema: dict[str, object] = Field(
        default_factory=dict,
        description="JSON schema for parameters. Model uses this to generate args.",
    )
    func: Callable[..., object] = Field(  # type: ignore[explicit-any]
        ...,
        description="Python function to run. Receives parsed arguments from model.",
    )
    requires_approval: bool = Field(
        default=False,
        description="If True, block execution until human approval via ApprovalGate.",
    )
    inject_run_context: bool = Field(
        default=False,
        description="If True, first param is ctx: RunContext[Deps]; agent injects it at runtime.",
    )

    model_config = {"arbitrary_types_allowed": True}

    _format_cache: dict[DocFormat, dict[str, object]] = PrivateAttr(default_factory=dict)

    def schema_to_toon(self, indent: int = 0) -> str:
        """Return this tool's parameters schema as TOON (token-efficient) string."""
        return _schema_to_toon(self.parameters_schema or {}, indent)

    def to_format(self, format: DocFormat = DocFormat.TOON) -> dict[str, object]:
        """Return this tool as a provider-ready schema dict (TOON, JSON, or YAML).

        P6: Result is cached per DocFormat so repeated LLM context builds don't
        re-serialize the same static schema on every call.
        """
        if format not in self._format_cache:
            self._format_cache[format] = tool_schema_to_format_dict(
                self.name,
                self.description or "",
                self.parameters_schema or {},
                format,
            )
        return self._format_cache[format]


def _annotation_to_json_schema(annotation: type[object] | object) -> dict[str, object]:
    """Convert a type annotation to a JSON schema fragment."""
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())

    if annotation is type(None):
        return {"type": "null"}
    if origin is Union or (hasattr(annotation, "__args__") and type(None) in (args or ())):
        non_none = [a for a in (args or ()) if a is not type(None)]
        if len(non_none) == 1:
            return {"oneOf": [_annotation_to_json_schema(non_none[0]), {"type": "null"}]}
        if non_none:
            return {"oneOf": [_annotation_to_json_schema(a) for a in non_none]}
    if origin is list and args:
        return {"type": "array", "items": _annotation_to_json_schema(args[0])}
    if origin is dict and len(args) >= 2:
        value_ann = args[1]  # type: ignore[misc]  # safe after len check; mypy tuple narrow
        if value_ann is not type(None):
            return {
                "type": "object",
                "additionalProperties": _annotation_to_json_schema(value_ann),
            }
    if isinstance(annotation, type) and annotation in _TYPE_TO_JSON:
        return {"type": _TYPE_TO_JSON[annotation]}
    return {"type": "string"}


def _parameters_schema_from_function(func: Callable[..., object]) -> tuple[dict[str, object], bool]:  # type: ignore[explicit-any]
    """Build a JSON schema for the function's parameters from type hints.

    Excludes param named 'ctx' (RunContext for DI). Returns (schema, inject_run_context).
    """
    hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}
    sig = inspect.signature(func)
    properties: dict[str, object] = {}
    required: list[str] = []
    inject_run_context = False
    for name, param in sig.parameters.items():
        if name == "self" or name == "cls":
            continue
        if name == "ctx":
            inject_run_context = True
            continue
        ann = hints.get(name, param.annotation)
        if ann is inspect.Parameter.empty:
            ann = object
        properties[name] = _annotation_to_json_schema(ann)
        if param.default is inspect.Parameter.empty:
            required.append(name)
    schema: dict[str, object] = {"type": "object", "properties": properties, "required": required}
    return (schema, inject_run_context)


def tool(  # type: ignore[explicit-any]
    func: Callable[..., object] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    requires_approval: bool = False,
) -> Callable[..., object] | ToolSpec:
    """Decorator to register a function as a Syrin tool.

    Extracts name from function name (or override), description from first line of
    docstring (or override), and builds JSON schema from type hints.

    Args:
        func: Function to decorate. If None, returns a decorator.
        name: Override tool name. Default: function name.
        description: Override description. Default: first line of docstring.
        requires_approval: If True, block execution until human approval.

    Returns:
        ToolSpec when used as @tool or @tool(); callable decorator when used as @tool(name="...").

    Example:
        >>> @tool
        ... def get_weather(city: str) -> str:
        ...     \"\"\"Get current weather for a city.\"\"\"
        ...     return f"Weather in {city}"
    """

    def decorator(f: Callable[..., object]) -> ToolSpec:  # type: ignore[explicit-any]
        tool_name = name or f.__name__
        desc = description or (inspect.getdoc(f) or "").strip().split("\n")[0] or ""
        params_schema, inject_run_context = _parameters_schema_from_function(f)
        return ToolSpec(
            name=tool_name,
            description=desc,
            parameters_schema=params_schema,
            func=f,
            requires_approval=requires_approval,
            inject_run_context=inject_run_context,
        )

    if func is not None:
        return decorator(func)
    return decorator


__all__ = ["tool", "ToolSpec"]
