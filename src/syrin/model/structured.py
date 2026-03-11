"""Structured output system - Simple decorator-based API.

Usage:
    from syrin.model import structured, output, OutputType

    @structured
    class Sentiment:
        sentiment: str
        confidence: float

    model = Model.OpenAI("gpt-4o", output=Sentiment)
"""

from __future__ import annotations

from typing import Annotated, Any, TypeVar, Union, cast, get_args, get_origin, get_type_hints

T = TypeVar("T")

_PRIMITIVE_JSON_TYPES: dict[type, dict[str, str]] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    list: {"type": "array"},
    dict: {"type": "object"},
}


def _is_optional(hint: type) -> bool:
    """True if type is Optional[T] or T | None."""
    origin = get_origin(hint)
    if origin is Union:
        args = get_args(hint)
        return type(None) in args
    return False


def _unwrap_optional(hint: type) -> type:
    """Return non-None part of Optional[T] or T | None."""
    origin = get_origin(hint)
    if origin is Union:
        args = get_args(hint)
        non_none = [a for a in args if a is not type(None)]
        return non_none[0] if len(non_none) == 1 else hint
    return hint


def _extract_description(metadata: tuple[object, ...]) -> str | None:
    """Extract description from Annotated metadata (string or Field)."""
    if not metadata:
        return None
    first = metadata[0]
    if isinstance(first, str):
        return first
    desc = getattr(first, "description", None)
    if isinstance(desc, str):
        return desc
    return None


def _has_default(cls: type, name: str) -> bool:
    """True if field has a default (class attribute or dataclass default)."""
    if hasattr(cls, "__dataclass_fields__"):
        fields = getattr(cls, "__dataclass_fields__", {})
        if name in fields:
            return (
                getattr(fields[name], "default", None) is not type(None)
                or getattr(fields[name], "default_factory", None) is not None
            )
    # Plain class: attribute exists and is not a type
    try:
        val = getattr(cls, name)
        return not (callable(val) or isinstance(val, type))
    except AttributeError:
        return False


class StructuredOutput:
    """Container for structured output schema.

    Used internally by Model when output type is set. Converts a Python class
    or JSON schema to a format the provider can use for structured output.
    Rarely constructed directly; use @structured or model.with_output().
    """

    _schema: dict[str, Any]
    _pydantic_model: type | None = None

    def __init__(self, schema: dict[str, Any] | type) -> None:
        if isinstance(schema, type):
            self._schema = self._class_to_schema(schema)
            self._pydantic_model = self._create_pydantic_model(schema)
        else:
            self._schema = schema
            self._pydantic_model = self._create_pydantic_model_from_schema(schema)

    def _class_to_schema(self, cls: type) -> dict[str, Any]:
        """Convert a Python class to JSON schema with $defs for nested types."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
        defs: dict[str, dict[str, Any]] = {}

        for name, hint in get_type_hints(cls, include_extras=True).items():
            prop_schema, nested_defs = self._hint_to_schema(hint, defs)
            schema["properties"][name] = prop_schema
            defs.update(nested_defs)

            if not self._is_field_optional(cls, name, hint):
                schema["required"].append(name)

        if defs:
            schema["$defs"] = defs

        return schema

    def _hint_to_schema(
        self,
        hint: type,
        defs: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        """Convert type hint to JSON schema property. Returns (prop, additional_defs)."""
        description: str | None = None
        effective_hint = hint

        origin = get_origin(hint)
        if origin is Annotated:
            args = get_args(hint)
            effective_hint = args[0] if args else str
            meta = args[1:] if len(args) > 1 else ()
            if meta:
                description = _extract_description(meta)

        inner_defs: dict[str, dict[str, Any]] = {}

        origin = get_origin(effective_hint)
        args = get_args(effective_hint)

        if origin is list:
            item_type = args[0] if args else str
            item_schema, item_defs = self._inner_type_to_schema(item_type, defs)
            inner_defs.update(item_defs)
            prop: dict[str, Any] = {"type": "array", "items": item_schema}
        elif origin is dict:
            prop = {"type": "object"}
        else:
            prop, inner_defs = self._inner_type_to_schema(effective_hint, defs)

        if description is not None:
            prop["description"] = description

        return prop, inner_defs

    def _inner_type_to_schema(
        self,
        py_type: type,
        defs: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        """Convert inner type to schema. Handles primitives and @structured classes."""
        if py_type in _PRIMITIVE_JSON_TYPES:
            return _PRIMITIVE_JSON_TYPES[py_type].copy(), {}

        if getattr(py_type, "_is_structured", False):
            name = getattr(py_type, "__name__", "Unknown")
            nested = StructuredOutput(py_type)
            nested_schema = nested._schema
            nested_defs = nested_schema.pop("$defs", {})
            ref_schema: dict[str, Any] = {"$ref": f"#/$defs/{name}"}
            all_defs: dict[str, dict[str, Any]] = {name: nested_schema, **nested_defs}
            return ref_schema, all_defs

        return {"type": "string"}, {}

    def _is_field_optional(self, cls: type, name: str, hint: type) -> bool:
        """True if field is optional (Optional, default value)."""
        return _is_optional(hint) or _has_default(cls, name)

    def _create_pydantic_model(self, cls: type) -> type:
        """Create a Pydantic model from a Python class, including nested @structured."""
        try:
            from pydantic import BaseModel, create_model

            hints = (
                get_type_hints(cls, include_extras=True) if hasattr(cls, "__annotations__") else {}
            )
            if not hints:
                hints = self._fallback_hints(cls)

            resolved: dict[str, Any] = {}
            for name, hint in hints.items():
                python_type = self._resolve_hint_to_python_type(hint)
                if self._is_field_optional(cls, name, hint):
                    resolved[name] = (python_type | None, None)
                else:
                    resolved[name] = (python_type, ...)

            if resolved:
                return create_model(cls.__name__, **resolved, __base__=BaseModel)
            return cls
        except Exception:
            return cls

    def _resolve_hint_to_python_type(self, hint: type) -> type:
        """Resolve hint to a Python type Pydantic accepts (handles list[Shareholder])."""
        if get_origin(hint) is Annotated:
            args = get_args(hint)
            hint = args[0] if args else hint
        effective = _unwrap_optional(hint) if _is_optional(hint) else hint
        origin = get_origin(effective)
        args = get_args(effective)

        if origin is list:
            item_type = args[0] if args else str
            if getattr(item_type, "_is_structured", False):
                nested_pydantic = getattr(item_type, "_structured_pydantic", None)
                if nested_pydantic is not None:
                    return list[nested_pydantic]  # type: ignore[valid-type]
            return list[item_type]  # type: ignore[valid-type]
        if origin is dict:
            return dict[str, str]
        if origin is Annotated:
            return self._resolve_hint_to_python_type(args[0] if args else str)

        if getattr(effective, "_is_structured", False):
            nested_pydantic = getattr(effective, "_structured_pydantic", None)
            if nested_pydantic is not None:
                return cast(type, nested_pydantic)

        return effective

    def _fallback_hints(self, cls: type) -> dict[str, type]:
        """Fallback when no annotations: infer from class attributes."""
        hints: dict[str, type] = {}
        for name in dir(cls):
            if name.startswith("_"):
                continue
            val = getattr(cls, name, None)
            if val is not None and not callable(val):
                hints[name] = type(val)
        return hints

    def _create_pydantic_model_from_schema(self, schema: dict[str, Any]) -> type:
        """Create a Pydantic model from JSON schema."""
        try:
            from pydantic import create_model

            properties = schema.get("properties", {})
            required = schema.get("required", [])

            field_definitions: dict[str, Any] = {}
            for name, prop in properties.items():
                prop_type = self._json_type_to_python_type(prop)
                if name in required:
                    field_definitions[name] = (prop_type, ...)
                else:
                    field_definitions[name] = (prop_type | None, None)

            return create_model("StructuredOutput", **field_definitions)  # type: ignore[no-any-return]
        except Exception:
            return type  # Fallback on schema parse failure; callers must handle

    def _json_type_to_python_type(self, prop: dict[str, Any]) -> type:
        """Convert JSON Schema type to Python type."""
        json_type = prop.get("type", "string")
        type_map: dict[str, type] = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        return type_map.get(json_type, str)

    @property
    def schema(self) -> dict[str, Any]:
        """Get the JSON schema."""
        return self._schema

    @property
    def pydantic_model(self) -> type | None:
        """Get the Pydantic model (if available)."""
        return self._pydantic_model


def structured(cls: type[T]) -> type[T]:
    """Decorator to define structured output schema.

    Supports nested types (list[Shareholder]), Annotated descriptions, and
    proper required/optional based on Optional and defaults.

    Usage:
        @structured
        class Sentiment:
            sentiment: str  # "positive", "negative", "neutral"
            confidence: float  # 0.0 to 1.0
            explanation: str = ""  # Optional field

        model = Model.OpenAI("gpt-4o", output=Sentiment)
    """
    obj = cast(Any, cls)
    obj._is_structured = True
    so = StructuredOutput(cls)
    obj._structured_schema = so.schema
    obj._structured_pydantic = so.pydantic_model
    return cls


class OutputType:
    """Wrapper for output type. Use with Agent(output=...) or Model(output=...).

    Wraps a Pydantic model or StructuredOutput. Provides schema and pydantic_model
    for provider integration.
    """

    def __init__(self, output_cls: type | StructuredOutput) -> None:
        if isinstance(output_cls, StructuredOutput):
            self._output_cls = output_cls.pydantic_model or output_cls._schema
        else:
            self._output_cls = output_cls
        self._structured = (
            StructuredOutput(output_cls)
            if not isinstance(output_cls, StructuredOutput)
            else output_cls
        )

    @property
    def schema(self) -> dict[str, Any]:
        return self._structured.schema

    @property
    def pydantic_model(self) -> type | None:
        return self._structured.pydantic_model

    @property
    def model_class(self) -> type:
        if isinstance(self._output_cls, type):
            return self._output_cls
        return self._structured.pydantic_model or type(self._structured)

    def __repr__(self) -> str:
        name = getattr(self._output_cls, "__name__", "Schema")
        return f"OutputType({name})"


def output(output_cls: type[T]) -> OutputType:
    """Shorthand to create OutputType from a Pydantic model or class."""
    return OutputType(output_cls)


__all__ = [
    "StructuredOutput",
    "structured",
    "OutputType",
    "output",
]
