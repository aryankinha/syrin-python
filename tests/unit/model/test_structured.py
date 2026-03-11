"""Tests for StructuredOutput, @structured decorator — nested types, Annotated, required."""

from __future__ import annotations

from typing import Annotated, cast

import pytest
from pydantic import BaseModel

from syrin.model.structured import StructuredOutput, structured

# =============================================================================
# TEST CLASSES — @structured with various type patterns
# =============================================================================


@structured
class Shareholder:
    """Nested type for list[Shareholder] tests."""

    name: str
    category: str
    shares: int
    percentage: float


@structured
class CapitalStructure:
    """Capital structure with nested shareholders."""

    authorized_capital: str
    shareholders: list[Shareholder]


@structured
class WithAnnotated:
    """Class with Annotated descriptions."""

    authorized_capital: Annotated[str, "Total authorized capital in ₹"]
    face_value: Annotated[str, "Face value per equity share in ₹"]
    missing: Annotated[list[str], "List of data fields not found in source documents"]


@structured
class WithOptionalField:
    """Class with Optional field."""

    name: str
    email: str | None = None


@structured
class WithDefaultValue:
    """Class with default value makes field optional."""

    name: str
    count: int = 0


@structured
class SimpleTypes:
    """Simple scalar types."""

    a: str
    b: int
    c: float
    d: bool


@structured
class WithListStr:
    """Class with list[str]."""

    tags: list[str]


@structured
class WithDictStrAny:
    """Class with dict[str, ...]."""

    metadata: dict[str, str]


# =============================================================================
# NESTED TYPE SUPPORT
# =============================================================================


class TestNestedTypes:
    """list[Shareholder] produces proper JSON schema with $defs and items."""

    def test_nested_list_schema_has_defs(self) -> None:
        """Schema includes $defs for Shareholder."""
        so = StructuredOutput(CapitalStructure)
        schema = so.schema
        assert "$defs" in schema
        assert "Shareholder" in schema["$defs"]

    def test_nested_list_items_ref_shareholder(self) -> None:
        """shareholders.items references Shareholder schema."""
        so = StructuredOutput(CapitalStructure)
        schema = so.schema
        props = schema["properties"]
        shareholders_prop = props.get("shareholders")
        assert shareholders_prop is not None
        assert shareholders_prop["type"] == "array"
        items = shareholders_prop.get("items")
        assert items is not None
        assert items.get("$ref") == "#/$defs/Shareholder" or items == schema["$defs"]["Shareholder"]

    def test_nested_pydantic_model_validates(self) -> None:
        """Pydantic model validates nested structure."""
        so = StructuredOutput(CapitalStructure)
        model = cast(type[BaseModel], so.pydantic_model)
        assert model is not None
        raw = {
            "authorized_capital": "5,00,00,000",
            "shareholders": [
                {
                    "name": "Promoter",
                    "category": "Promoter",
                    "shares": 1250000,
                    "percentage": 62.50,
                },
                {"name": "Public", "category": "Public", "shares": 750000, "percentage": 37.50},
            ],
        }
        validated = model.model_validate(raw)
        assert validated.authorized_capital == "5,00,00,000"  # type: ignore[attr-defined]
        assert len(validated.shareholders) == 2  # type: ignore[attr-defined]
        assert validated.shareholders[0].name == "Promoter"  # type: ignore[attr-defined]
        assert validated.shareholders[0].percentage == 62.50  # type: ignore[attr-defined]


# =============================================================================
# ANNOTATED DESCRIPTION SUPPORT
# =============================================================================


class TestAnnotatedDescriptions:
    """Annotated[T, "description"] adds description to schema."""

    def test_annotated_string_adds_description(self) -> None:
        """String metadata becomes description in schema."""
        so = StructuredOutput(WithAnnotated)
        props = so.schema["properties"]
        ac = props.get("authorized_capital")
        assert ac is not None
        assert ac.get("description") == "Total authorized capital in ₹"
        assert ac.get("type") == "string"

    def test_annotated_face_value_description(self) -> None:
        """Face value field has description."""
        so = StructuredOutput(WithAnnotated)
        fv = so.schema["properties"].get("face_value")
        assert fv is not None
        assert fv.get("description") == "Face value per equity share in ₹"

    def test_annotated_list_description(self) -> None:
        """Annotated list has description."""
        so = StructuredOutput(WithAnnotated)
        missing = so.schema["properties"].get("missing")
        assert missing is not None
        assert "List of data fields not found" in str(missing.get("description", ""))


# =============================================================================
# REQUIRED FIELD LOGIC
# =============================================================================


class TestRequiredFieldLogic:
    """Required vs optional derived from Optional and defaults."""

    def test_optional_field_not_required(self) -> None:
        """Optional[str] = None makes email not required."""
        so = StructuredOutput(WithOptionalField)
        required = so.schema.get("required", [])
        assert "name" in required
        assert "email" not in required

    def test_default_value_not_required(self) -> None:
        """Field with default is not required."""
        so = StructuredOutput(WithDefaultValue)
        required = so.schema.get("required", [])
        assert "name" in required
        assert "count" not in required

    def test_simple_all_required(self) -> None:
        """Simple types without defaults are all required."""
        so = StructuredOutput(SimpleTypes)
        required = so.schema.get("required", [])
        assert set(required) == {"a", "b", "c", "d"}


# =============================================================================
# SIMPLE TYPES AND SCHEMA SHAPE
# =============================================================================


class TestSimpleTypes:
    """Basic schema generation."""

    def test_simple_schema_types(self) -> None:
        """Schema has correct types for primitives."""
        so = StructuredOutput(SimpleTypes)
        p = so.schema["properties"]
        assert p["a"]["type"] == "string"
        assert p["b"]["type"] == "integer"
        assert p["c"]["type"] == "number"
        assert p["d"]["type"] == "boolean"

    def test_list_str_schema(self) -> None:
        """list[str] produces array of strings."""
        so = StructuredOutput(WithListStr)
        tags = so.schema["properties"]["tags"]
        assert tags["type"] == "array"
        assert tags["items"]["type"] == "string"

    def test_decorator_sets_attributes(self) -> None:
        """@structured sets _is_structured and schema attrs."""
        assert getattr(SimpleTypes, "_is_structured", False) is True
        assert hasattr(SimpleTypes, "_structured_schema")
        assert hasattr(SimpleTypes, "_structured_pydantic")


# =============================================================================
# EDGE CASES AND INVALID
# =============================================================================


class TestEdgeCases:
    """Edge cases and robustness."""

    def test_empty_class_handled(self) -> None:
        """Empty class doesn't crash."""

        @structured
        class Empty:
            pass

        so = StructuredOutput(Empty)
        assert so.schema["type"] == "object"
        assert "properties" in so.schema

    def test_pydantic_validates_simple(self) -> None:
        """Pydantic model validates simple structure."""
        so = StructuredOutput(SimpleTypes)
        model = cast(type[BaseModel], so.pydantic_model)
        assert model is not None
        v = model.model_validate({"a": "x", "b": 1, "c": 1.0, "d": True})
        assert v.a == "x"  # type: ignore[attr-defined]
        assert v.b == 1  # type: ignore[attr-defined]

    def test_invalid_data_raises(self) -> None:
        """Invalid data raises Pydantic ValidationError."""
        from pydantic import ValidationError

        so = StructuredOutput(SimpleTypes)
        model = cast(type[BaseModel], so.pydantic_model)
        assert model is not None
        with pytest.raises(ValidationError):
            model.model_validate({"a": 123})  # b should be int
