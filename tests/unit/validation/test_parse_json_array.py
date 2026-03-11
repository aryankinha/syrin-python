"""Tests for _parse_json object/array extraction from text."""

from __future__ import annotations

from pydantic import BaseModel

from syrin.validation import ValidationPipeline


class SimpleItem(BaseModel):
    name: str
    value: int


class ItemList(BaseModel):
    items: list[dict]


class TestParseJsonArray:
    """ValidationPipeline._parse_json extracts JSON from surrounding text."""

    def test_json_object_with_prefix(self) -> None:
        """Object with prefix extracts correctly."""
        pipeline = ValidationPipeline(SimpleItem, max_retries=1)
        raw = 'Result: {"name": "test", "value": 42}'
        parsed, _, err = pipeline.validate(raw)
        assert parsed is not None
        assert parsed.name == "test"
        assert parsed.value == 42
        assert err is None

    def test_json_object_in_text_with_array_field(self) -> None:
        """Nested structure with array parses correctly."""
        pipeline = ValidationPipeline(ItemList, max_retries=1)
        raw = 'Items: {"items": [{"name": "a", "value": 1}]}'
        parsed, _, err = pipeline.validate(raw)
        assert parsed is not None
        assert len(parsed.items) == 1
        assert parsed.items[0]["name"] == "a"
        assert err is None
