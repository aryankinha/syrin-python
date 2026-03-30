"""Template render depth limit enforcement for deeply-nested Mustache templates.

Tests that:
- Templates with nesting depth <= 10 render fine
- Templates with nesting depth > 10 raise TemplateParseError (or similar)
- The default max_depth is 10
- max_depth can be overridden
"""

from __future__ import annotations

import pytest

from syrin.template import Template


def _make_nested(depth: int) -> str:
    """Create a Mustache template with `depth` levels of nesting."""
    open_tags = "".join(f"{{{{#section{i}}}}}" for i in range(depth))
    close_tags = "".join(f"{{{{/section{i}}}}}" for i in reversed(range(depth)))
    return f"{open_tags}deep_content{close_tags}"


class TestTemplateDepthLimit:
    def test_shallow_template_renders(self) -> None:
        """A template with no sections renders fine."""
        t = Template(
            name="flat",
            content="Hello {{name}}",
            slots={"name": {"type": "str"}},
        )
        result = t.render(name="world")
        assert "world" in result

    def test_shallow_nesting_allowed(self) -> None:
        """Nesting depth 5 — below default limit — should not raise."""
        content = _make_nested(5)
        t = Template(name="test", content=content)
        # render() should not raise for depth 5 (limit is 10)
        t.render()  # Empty context is fine; check doesn't require render to produce output

    def test_exactly_at_limit_allowed(self) -> None:
        """Nesting depth of exactly 10 should not raise."""
        content = _make_nested(10)
        t = Template(name="test", content=content)
        t.render()  # Should not raise

    def test_over_limit_raises(self) -> None:
        """Nesting depth of 11 exceeds default max_depth=10 — must raise."""
        content = _make_nested(11)
        t = Template(name="test", content=content)
        with pytest.raises(Exception) as exc_info:
            t.render()
        assert exc_info.type.__name__ in (
            "TemplateParseError",
            "ValueError",
            "RecursionError",
            "TemplateTooDeepError",
        ), f"Expected a depth-limit error, got {exc_info.type.__name__}"

    def test_custom_max_depth_rejects_over_limit(self) -> None:
        """Custom max_depth=5 rejects depth 6."""
        content = _make_nested(6)
        t = Template(name="test", content=content)
        with pytest.raises((RecursionError, RuntimeError, ValueError)):
            t.render(max_depth=5)

    def test_custom_max_depth_allows_at_limit(self) -> None:
        """Custom max_depth=5 allows depth 5."""
        content = _make_nested(5)
        t = Template(name="test", content=content)
        t.render(max_depth=5)  # Should not raise
