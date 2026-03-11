"""Template engine for slot-based structured generation.

Uses Mustache-style syntax ({{variable}}, {{#section}}...{{/section}}, {{#list}}{{.}}{{/list}})
to reduce hallucination by constraining LLM output to filling predefined slots.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import chevron

__all__ = ["Template", "SlotConfig"]


@dataclass(frozen=True)
class SlotConfig:
    """Configuration for a single template slot.

    Attributes:
        slot_type: Python type name: "str", "int", "float", "bool", "list[str]".
        required: If True, render() raises when slot is missing (strict mode).
        default: Default value when slot is not provided.
    """

    slot_type: str
    required: bool = False
    default: Any = None

    def to_json_schema_type(self) -> str:
        """Map slot_type to JSON schema type string."""
        if self.slot_type.startswith("list["):
            return "array"
        mapping: dict[str, str] = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
        }
        return mapping.get(self.slot_type, "string")


def _coerce_value(value: Any, slot_type: str) -> Any:
    """Coerce value to slot type for template rendering."""
    if value is None:
        return None
    if slot_type == "str":
        return str(value) if not isinstance(value, str) else value
    if slot_type == "int":
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        try:
            return int(float(str(value).replace(",", "")))
        except (ValueError, TypeError):
            return value
    if slot_type == "float":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        try:
            return float(str(value).replace(",", ""))
        except (ValueError, TypeError):
            return value
    if slot_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", "on")
        return bool(value)
    if slot_type.startswith("list["):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else [value]
            except json.JSONDecodeError:
                return [value] if value else []
        return [value] if value is not None else []
    return value


def _prepare_context(
    slots: dict[str, SlotConfig],
    data: dict[str, Any],
    strict: bool,
) -> dict[str, Any]:
    """Prepare Mustache context from slot config and provided data."""
    ctx: dict[str, Any] = {}
    for name, config in slots.items():
        if name in data:
            ctx[name] = _coerce_value(data[name], config.slot_type)
        elif config.default is not None:
            ctx[name] = config.default
        elif config.required and strict:
            raise ValueError(f"Required slot {name!r} is missing")
        else:
            ctx[name] = None
    return ctx


class Template:
    """Structured template with typed slots for constrained generation.

    Templates reduce hallucination by constraining LLM output to filling
    predefined slots rather than generating freeform text. Supports
    Mustache-style syntax: {{var}}, {{#section}}...{{/section}},
    {{#list}}{{.}}{{/list}} for iteration (use {{.}} for current element).

    Example:
        >>> t = Template(
        ...     name="cap",
        ...     content="Capital: {{amount}}",
        ...     slots={"amount": SlotConfig("str", required=True)},
        ... )
        >>> t.render(amount="₹50L")
        'Capital: ₹50L'
    """

    def __init__(
        self,
        name: str,
        content: str,
        *,
        slots: dict[str, SlotConfig | dict[str, Any]] | None = None,
        strict: bool = False,
    ) -> None:
        """Create a template.

        Args:
            name: Template identifier.
            content: Mustache template string.
            slots: Slot definitions. Values can be SlotConfig or dict with
                type, required, default keys.
            strict: If True, render() raises when a required slot is missing.
        """
        self._name = name
        self._content = content
        self._strict = strict
        self._slots: dict[str, SlotConfig] = {}
        if slots:
            for k, v in slots.items():
                if isinstance(v, SlotConfig):
                    self._slots[k] = v
                elif isinstance(v, dict):
                    self._slots[k] = SlotConfig(
                        slot_type=str(v.get("type", "str")),
                        required=bool(v.get("required", False)),
                        default=v.get("default"),
                    )
                else:
                    self._slots[k] = SlotConfig(slot_type="str", required=False)

    @property
    def name(self) -> str:
        """Template identifier."""
        return self._name

    @property
    def content(self) -> str:
        """Raw template string."""
        return self._content

    @property
    def slots(self) -> dict[str, SlotConfig]:
        """Slot configuration by name."""
        return dict(self._slots)

    def render(self, **kwargs: Any) -> str:
        """Render template with provided slot values.

        Args:
            **kwargs: Slot values by name. Extras are ignored.

        Returns:
            Rendered string.

        Raises:
            ValueError: If strict=True and a required slot is missing.
        """
        ctx = _prepare_context(self._slots, kwargs, self._strict)
        return cast(str, chevron.render(self._content, ctx))

    def slot_schema(self) -> dict[str, Any]:
        """Return JSON schema for slots (for LLM extraction)."""
        props: dict[str, Any] = {}
        required: list[str] = []
        for name, config in self._slots.items():
            t = config.to_json_schema_type()
            prop: dict[str, Any] = {"type": t, "description": f"Slot: {name}"}
            if t == "array":
                prop["items"] = {"type": "string"}
            props[name] = prop
            if config.required:
                required.append(name)
        schema: dict[str, Any] = {
            "type": "object",
            "properties": props,
        }
        if required:
            schema["required"] = required
        return schema

    @classmethod
    def from_file(cls, path: str | Path, **kwargs: Any) -> Template:
        """Load template from file.

        Args:
            path: Path to template file.
            **kwargs: Passed to Template constructor (slots, strict).

        Returns:
            Template instance. Name defaults to stem of path.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Template file not found: {path}")
        content = p.read_text(encoding="utf-8")
        name = kwargs.pop("name", p.stem)
        return cls(name=name, content=content, **kwargs)

    @classmethod
    def from_string(cls, content: str, name: str = "unnamed", **kwargs: Any) -> Template:
        """Create template from string.

        Args:
            content: Template content.
            name: Template identifier. Default "unnamed".
            **kwargs: Passed to Template constructor (slots, strict).

        Returns:
            Template instance.
        """
        return cls(name=name, content=content, **kwargs)
