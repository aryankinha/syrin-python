"""Unit tests for Template class (TDD, edge cases, valid and invalid)."""

import tempfile
from pathlib import Path

import pytest

from syrin.template import SlotConfig, Template

# -----------------------------------------------------------------------------
# render() - valid cases
# -----------------------------------------------------------------------------


class TestTemplateRenderValid:
    """Valid render scenarios."""

    def test_render_simple_variable(self) -> None:
        t = Template("x", "Hello {{name}}", slots={"name": SlotConfig("str")})
        assert t.render(name="World") == "Hello World"

    def test_render_multiple_variables(self) -> None:
        t = Template(
            "x",
            "{{a}} + {{b}} = {{c}}",
            slots={
                "a": SlotConfig("str"),
                "b": SlotConfig("str"),
                "c": SlotConfig("str"),
            },
        )
        assert t.render(a="1", b="2", c="3") == "1 + 2 = 3"

    def test_render_with_default(self) -> None:
        t = Template(
            "x",
            "Hi {{name}}",
            slots={
                "name": SlotConfig("str", required=False, default="Guest"),
            },
        )
        assert t.render() == "Hi Guest"
        assert t.render(name="Alice") == "Hi Alice"

    def test_render_section_true(self) -> None:
        # Mustache {{#x}}...{{/x}} renders when x is truthy
        t = Template(
            "x",
            "{{#show}}Visible{{/show}}",
            slots={
                "show": SlotConfig("bool"),
            },
        )
        assert t.render(show=True) == "Visible"

    def test_render_section_false(self) -> None:
        t = Template("x", "{{#show}}Visible{{/show}}", slots={"show": SlotConfig("bool")})
        assert t.render(show=False) == ""

    def test_render_list_iteration(self) -> None:
        # Mustache: {{#list}}{{.}}{{/list}} - . is current element
        t = Template(
            "x",
            "{{#items}}{{.}}, {{/items}}",
            slots={
                "items": SlotConfig("list[str]"),
            },
        )
        assert t.render(items=["a", "b", "c"]) == "a, b, c, "

    def test_render_empty_list(self) -> None:
        t = Template("x", "{{#items}}{{.}}{{/items}}", slots={"items": SlotConfig("list[str]")})
        assert t.render(items=[]) == ""

    def test_render_int_coercion(self) -> None:
        t = Template("x", "{{n}}", slots={"n": SlotConfig("int")})
        assert t.render(n=42) == "42"
        assert t.render(n="99") == "99"

    def test_render_str_coercion(self) -> None:
        t = Template("x", "{{x}}", slots={"x": SlotConfig("str")})
        assert t.render(x=123) == "123"

    def test_render_bool_coercion(self) -> None:
        t = Template("x", "{{#flag}}on{{/flag}}", slots={"flag": SlotConfig("bool")})
        assert t.render(flag="true") == "on"
        assert t.render(flag="yes") == "on"

    def test_render_no_slots(self) -> None:
        t = Template("x", "Static content", slots=None)
        assert t.render() == "Static content"

    def test_render_extra_kwargs_ignored(self) -> None:
        t = Template("x", "{{a}}", slots={"a": SlotConfig("str")})
        assert t.render(a="ok", extra="ignored") == "ok"

    def test_render_with_dict_slot_config(self) -> None:
        t = Template("x", "{{v}}", slots={"v": {"type": "str", "required": True}})
        assert t.render(v="x") == "x"


# -----------------------------------------------------------------------------
# render() - strict mode
# -----------------------------------------------------------------------------


class TestTemplateRenderStrict:
    """Strict mode behavior."""

    def test_strict_missing_required_raises(self) -> None:
        t = Template("x", "{{a}}", slots={"a": SlotConfig("str", required=True)}, strict=True)
        with pytest.raises(ValueError, match="Required slot .a. is missing"):
            t.render()

    def test_strict_with_default_no_raise(self) -> None:
        t = Template(
            "x", "{{a}}", slots={"a": SlotConfig("str", required=True, default="x")}, strict=True
        )
        assert t.render() == "x"

    def test_strict_not_required_no_raise(self) -> None:
        t = Template("x", "{{a}}", slots={"a": SlotConfig("str", required=False)}, strict=True)
        assert t.render() == ""

    def test_non_strict_missing_required_renders_empty(self) -> None:
        t = Template("x", "x{{a}}y", slots={"a": SlotConfig("str", required=True)}, strict=False)
        assert t.render() == "xy"


# -----------------------------------------------------------------------------
# slot_schema()
# -----------------------------------------------------------------------------


class TestTemplateSlotSchema:
    """slot_schema() returns valid JSON schema."""

    def test_slot_schema_empty(self) -> None:
        t = Template("x", "static", slots={})
        s = t.slot_schema()
        assert s["type"] == "object"
        assert s["properties"] == {}
        assert "required" not in s

    def test_slot_schema_with_required(self) -> None:
        t = Template(
            "x",
            "{{a}}",
            slots={
                "a": SlotConfig("str", required=True),
                "b": SlotConfig("int", required=False),
            },
        )
        s = t.slot_schema()
        assert "a" in s["properties"]
        assert "b" in s["properties"]
        assert s["required"] == ["a"]

    def test_slot_schema_types(self) -> None:
        t = Template(
            "x",
            "",
            slots={
                "s": SlotConfig("str"),
                "i": SlotConfig("int"),
                "f": SlotConfig("float"),
                "b": SlotConfig("bool"),
                "l": SlotConfig("list[str]"),
            },
        )
        s = t.slot_schema()
        assert s["properties"]["s"]["type"] == "string"
        assert s["properties"]["i"]["type"] == "integer"
        assert s["properties"]["f"]["type"] == "number"
        assert s["properties"]["b"]["type"] == "boolean"
        assert s["properties"]["l"]["type"] == "array"


# -----------------------------------------------------------------------------
# from_file, from_string
# -----------------------------------------------------------------------------


class TestTemplateFactories:
    """from_file and from_string."""

    def test_from_string(self) -> None:
        t = Template.from_string("Hi {{x}}", name="greet", slots={"x": SlotConfig("str")})
        assert t.name == "greet"
        assert t.render(x="you") == "Hi you"

    def test_from_string_default_name(self) -> None:
        t = Template.from_string("x")
        assert t.name == "unnamed"

    def test_from_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Title: {{title}}\nBody: {{body}}")
            path = f.name
        try:
            t = Template.from_file(
                path,
                slots={
                    "title": SlotConfig("str"),
                    "body": SlotConfig("str"),
                },
            )
            assert t.name == Path(path).stem
            assert t.render(title="A", body="B") == "Title: A\nBody: B"
        finally:
            Path(path).unlink()

    def test_from_file_not_found_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            Template.from_file("/nonexistent/path/template.mustache")

    def test_from_file_custom_name(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("{{x}}")
            path = f.name
        try:
            t = Template.from_file(path, name="custom", slots={"x": SlotConfig("str")})
            assert t.name == "custom"
        finally:
            Path(path).unlink()


# -----------------------------------------------------------------------------
# Edge cases
# -----------------------------------------------------------------------------


class TestTemplateEdgeCases:
    """Edge cases and special values."""

    def test_empty_content(self) -> None:
        t = Template("x", "", slots={})
        assert t.render() == ""

    def test_null_in_context(self) -> None:
        t = Template("x", "{{a}}", slots={"a": SlotConfig("str")})
        assert t.render(a=None) == ""

    def test_nested_structure_in_list(self) -> None:
        t = Template("x", "{{#items}}{{.}} {{/items}}", slots={"items": SlotConfig("list[str]")})
        assert t.render(items=["x", "y"]) == "x y "

    def test_slot_with_comma_in_int_string(self) -> None:
        t = Template("x", "{{n}}", slots={"n": SlotConfig("int")})
        assert t.render(n="1,234") == "1234"

    def test_properties(self) -> None:
        t = Template("n", "c", slots={"a": SlotConfig("str")})
        assert t.name == "n"
        assert t.content == "c"
        assert "a" in t.slots
