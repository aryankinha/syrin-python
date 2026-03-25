"""Output configuration for structured output validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic import BaseModel

import builtins

from syrin.types.validation import OutputValidator


@dataclass
class Output:
    """Configuration for structured output validation.

    Pass to Agent(output=Output(MyPydanticModel)). Groups all structured
    output options in one place. Use Output(MyModel) shorthand for defaults.

    Attributes:
        type: Pydantic model to validate output against.
        validation_retries: Number of retries (default 3).
        context: Dict passed to validators for dynamic validation.
        validator: Custom OutputValidator for business logic.
        strict: Use strict validation mode.

    Example:
        agent = Agent(
            model=Model.OpenAI("gpt-4o"),
            output=Output(
                type=UserInfo,
                validation_retries=3,
                context={"allowed_domains": ["company.com"]},
            ),
        )

    Or use shorthand:
        agent = Agent(
            model=Model.OpenAI("gpt-4o"),
            output=Output(UserInfo),  # Just the type
        )
    """

    type: builtins.type[BaseModel] | None = None
    """Pydantic model to validate output against."""

    validation_retries: int = 3
    """Number of validation retry attempts (default: 3)."""

    context: dict[str, object] = field(default_factory=dict)
    """Context passed to validators for dynamic validation."""

    validator: OutputValidator | None = None
    """Custom output validator for business logic."""

    strict: bool = False
    """Use strict validation mode."""

    def __init__(
        self,
        output_type: builtins.type[BaseModel] | None = None,
        *,
        validation_retries: int = 3,
        context: dict[str, object] | None = None,
        validator: OutputValidator | None = None,
        strict: bool = False,
    ):
        self.type = output_type
        self.validation_retries = validation_retries
        self.context = context or {}
        self.validator = validator
        self.strict = strict

    def get_remote_config_schema(self, section_key: str) -> tuple[Any, dict[str, object]]:  # type: ignore[explicit-any]
        """RemoteConfigurable: return (schema, current_values) for the output section."""
        from syrin.remote._schema import build_section_schema_from_obj
        from syrin.remote._types import ConfigSchema

        if section_key != "output":
            return (ConfigSchema(section="output", class_name="Output", fields=[]), {})
        return build_section_schema_from_obj(self, "output", "Output")

    def apply_remote_overrides(
        self,
        agent: object,
        pairs: list[tuple[str, object]],
        section_schema: object,
    ) -> None:
        """RemoteConfigurable: apply output overrides (self is agent._output)."""
        from syrin.remote._resolver_helpers import build_nested_update

        update = build_nested_update(section_schema, pairs, "output")  # type: ignore[arg-type]
        if not update:
            return
        for key, value in update.items():
            if hasattr(self, key):
                setattr(self, key, value)
