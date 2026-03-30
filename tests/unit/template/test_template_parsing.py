"""Template parsing error handling for malformed YAML frontmatter.

Tests that:
- Valid YAML frontmatter loads correctly
- Malformed YAML frontmatter raises TemplateParseError (not silently ignored)
- TemplateParseError includes line number
- TemplateParseError includes the file path
"""

from __future__ import annotations

from pathlib import Path

import pytest

from syrin.exceptions import TemplateParseError
from syrin.template import Template


def _write_template(dir: str, content: str, filename: str = "t.md") -> Path:
    p = Path(dir) / filename
    p.write_text(content, encoding="utf-8")
    return p


class TestTemplateFromFileYamlErrors:
    def test_valid_frontmatter_loads(self, tmp_path: Path) -> None:
        """Valid YAML frontmatter parses and creates slots."""
        p = tmp_path / "valid.md"
        p.write_text(
            "---\nname:\n  type: str\n  required: true\n---\nHello {{name}}\n",
            encoding="utf-8",
        )
        t = Template.from_file(p)
        assert "name" in t.slots

    def test_malformed_yaml_raises_template_parse_error(self, tmp_path: Path) -> None:
        """Malformed YAML in frontmatter must raise TemplateParseError."""
        p = tmp_path / "bad.md"
        # Invalid YAML: tab characters in indentation are forbidden in YAML
        p.write_text(
            "---\nname:\n\t  type: str\n---\nHello {{name}}\n",
            encoding="utf-8",
        )
        with pytest.raises(TemplateParseError) as exc_info:
            Template.from_file(p)
        assert "bad.md" in str(exc_info.value) or "bad" in str(exc_info.value).lower()

    def test_parse_error_includes_line_number(self, tmp_path: Path) -> None:
        """TemplateParseError must have a line attribute."""
        p = tmp_path / "bad.md"
        p.write_text(
            "---\nname:\n\t  type: str\n---\nHello\n",
            encoding="utf-8",
        )
        with pytest.raises(TemplateParseError) as exc_info:
            Template.from_file(p)
        err = exc_info.value
        assert hasattr(err, "line"), "TemplateParseError must have a 'line' attribute"
        assert err.line is not None

    def test_no_frontmatter_no_error(self, tmp_path: Path) -> None:
        """Files without frontmatter should parse fine."""
        p = tmp_path / "plain.md"
        p.write_text("Hello {{name}}\n", encoding="utf-8")
        t = Template.from_file(p)
        assert t.name == "plain"

    def test_parse_error_has_path(self, tmp_path: Path) -> None:
        """TemplateParseError must have a path attribute pointing to the file."""
        p = tmp_path / "bad2.md"
        p.write_text(
            "---\nname:\n\t bad: value\n---\nHello\n",
            encoding="utf-8",
        )
        with pytest.raises(TemplateParseError) as exc_info:
            Template.from_file(p)
        err = exc_info.value
        assert hasattr(err, "path"), "TemplateParseError must have a 'path' attribute"
