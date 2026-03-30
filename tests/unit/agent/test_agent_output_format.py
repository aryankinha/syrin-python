"""Tests for Agent output_config and template integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from syrin import (
    Agent,
    CitationStyle,
    Output,
    OutputConfig,
    OutputFormat,
    SlotConfig,
    Template,
)
from syrin.model import Model
from syrin.types import ProviderResponse, TokenUsage


class SimpleOut(BaseModel):
    """Minimal Pydantic model for template tests."""

    name: str
    value: int


def _mock_provider_response(content: str) -> ProviderResponse:
    return ProviderResponse(
        content=content,
        tool_calls=[],
        token_usage=TokenUsage(input_tokens=1, output_tokens=1, total_tokens=2),
    )


class TestAgentOutputConfig:
    """Agent accepts output_config (OutputFormat or OutputConfig)."""

    def test_agent_output_config_enum(self) -> None:
        """Agent accepts OutputFormat enum."""
        agent = Agent(
            model=Model.Almock(latency_min=0, latency_max=0),
            system_prompt="Hi",
            output_config=OutputFormat.TEXT,
        )
        assert agent._output_config is not None
        assert agent._output_config.format == OutputFormat.TEXT
        assert agent._output_config.template is None

    def test_agent_output_config_config(self) -> None:
        """Agent accepts OutputConfig."""
        agent = Agent(
            model=Model.Almock(latency_min=0, latency_max=0),
            system_prompt="Hi",
            output_config=OutputConfig(format=OutputFormat.MARKDOWN),
        )
        assert agent._output_config is not None
        assert agent._output_config.format == OutputFormat.MARKDOWN


class TestAgentOutputConfigTemplate:
    """Agent with output_config.template renders template from structured output."""

    def test_template_renders_content(self) -> None:
        """When output_config has template and output has model, response.content is rendered."""
        tpl = Template(
            "simple",
            "Name: {{name}}, Value: {{value}}",
            slots={"name": SlotConfig("str"), "value": SlotConfig("int")},
        )
        model = Model("anthropic/claude-3-5-sonnet")
        agent = Agent(
            model=model,
            system_prompt="Return JSON.",
            output=Output(SimpleOut),
            output_config=OutputConfig(format=OutputFormat.TEXT, template=tpl),
        )
        mock_resp = _mock_provider_response(content='{"name": "Alice", "value": 42}')
        with patch.object(
            agent._provider,
            "complete",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            r = agent.run("Return name and value.")
        assert r.content == "Name: Alice, Value: 42"
        assert r.template_data == {"name": "Alice", "value": 42}
        assert r.structured is not None
        assert r.structured.parsed.name == "Alice"

    def test_template_without_output_raises(self) -> None:
        """output_config with template requires output=Output(SomeModel)."""
        tpl = Template("x", "{{a}}", slots={"a": SlotConfig("str")})
        with pytest.raises(ValueError, match="output_config with template requires"):
            Agent(
                model=Model.Almock(),
                system_prompt="Hi",
                output_config=OutputConfig(format=OutputFormat.TEXT, template=tpl),
            )


class TestAgentOutputConfigFileGeneration:
    """Agent with output_config generates response.file and response.file_bytes."""

    def test_output_config_text_produces_file(self) -> None:
        """When output_config is TEXT, response.file and response.file_bytes are set."""
        agent = Agent(
            model=Model.Almock(latency_min=0, latency_max=0),
            system_prompt="Return 'Hello world'.",
            output_config=OutputFormat.TEXT,
        )
        with patch.object(
            agent._provider,
            "complete",
            new_callable=AsyncMock,
            return_value=_mock_provider_response(content="Hello world"),
        ):
            r = agent.run("Say hello")
        assert r.content == "Hello world"
        assert r.file is not None
        assert r.file.exists()
        assert r.file.suffix == ".txt"
        assert r.file_bytes is not None
        assert r.file_bytes == b"Hello world"

    def test_output_config_none_no_file(self) -> None:
        """When output_config is None, response.file and response.file_bytes are None."""
        agent = Agent(
            model=Model.Almock(latency_min=0, latency_max=0),
            system_prompt="Hi",
        )
        with patch.object(
            agent._provider,
            "complete",
            new_callable=AsyncMock,
            return_value=_mock_provider_response(content="Hi"),
        ):
            r = agent.run("Hi")
        assert r.file is None
        assert r.file_bytes is None

    def test_output_config_pdf_missing_deps_graceful(self) -> None:
        """PDF format without WeasyPrint: no crash, response.file is None."""
        agent = Agent(
            model=Model.Almock(latency_min=0, latency_max=0),
            system_prompt="Return content.",
            output_config=OutputFormat.PDF,
        )
        with (
            patch(
                "syrin.output_format.format_to_file",
                side_effect=ImportError("No module named 'weasyprint'"),
            ),
            patch.object(
                agent._provider,
                "complete",
                new_callable=AsyncMock,
                return_value=_mock_provider_response(content="PDF content here"),
            ),
        ):
            r = agent.run("Generate PDF")
        assert r.content == "PDF content here"
        assert r.file is None
        assert r.file_bytes is None

    def test_output_config_docx_missing_deps_graceful(self) -> None:
        """DOCX format without python-docx: no crash, response.file is None."""
        agent = Agent(
            model=Model.Almock(latency_min=0, latency_max=0),
            system_prompt="Return content.",
            output_config=OutputFormat.DOCX,
        )
        with (
            patch(
                "syrin.output_format.format_to_file",
                side_effect=ImportError("No module named 'docx'"),
            ),
            patch.object(
                agent._provider,
                "complete",
                new_callable=AsyncMock,
                return_value=_mock_provider_response(content="DOCX content here"),
            ),
        ):
            r = agent.run("Generate DOCX")
        assert r.content == "DOCX content here"
        assert r.file is None
        assert r.file_bytes is None


class TestAgentOutputConfigCitation:
    """Agent with output_config.citation parses and styles citations."""

    def test_citation_populates_response_citations(self) -> None:
        """When output_config has citation, response.citations is populated."""
        agent = Agent(
            model=Model.Almock(latency_min=0, latency_max=0),
            system_prompt="Return text with citations.",
            output_config=OutputConfig(
                format=OutputFormat.TEXT,
                citation_style=CitationStyle.FOOTNOTE,
            ),
        )
        content_with_citation = "The authorized capital is ₹50,00,000 [Source: moa.pdf, Page 3]."
        with patch.object(
            agent._provider,
            "complete",
            new_callable=AsyncMock,
            return_value=_mock_provider_response(content=content_with_citation),
        ):
            r = agent.run("What is the capital?")
        assert r.citations is not None
        assert len(r.citations) == 1
        assert r.citations[0].source == "moa.pdf"
        assert r.citations[0].page == 3
        assert "[1]" in r.content
        assert "moa.pdf" in r.content

    def test_no_citation_config_empty_citations(self) -> None:
        """When output_config has no citation, response.citations is empty."""
        agent = Agent(
            model=Model.Almock(latency_min=0, latency_max=0),
            system_prompt="Hi",
            output_config=OutputFormat.TEXT,
        )
        with patch.object(
            agent._provider,
            "complete",
            new_callable=AsyncMock,
            return_value=_mock_provider_response(content="Text [Source: doc.pdf, Page 1]"),
        ):
            r = agent.run("Hi")
        assert r.citations == []
        assert "[Source:" in r.content
