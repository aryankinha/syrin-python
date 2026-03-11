"""Tests for CitationGuardrail."""

from __future__ import annotations

import pytest

from syrin.guardrails.built_in.citation import CitationGuardrail
from syrin.guardrails.context import GuardrailContext


@pytest.mark.asyncio
async def test_passes_when_require_source_false() -> None:
    """When require_source=False, always passes."""
    guard = CitationGuardrail(require_source=False)
    ctx = GuardrailContext(text="The capital is ₹50,00,000. No citation.")
    result = await guard.evaluate(ctx)
    assert result.passed is True


@pytest.mark.asyncio
async def test_passes_with_citation() -> None:
    """When output has [Source: ...], passes."""
    guard = CitationGuardrail(require_source=True)
    ctx = GuardrailContext(text="The authorized capital is ₹50,00,000. [Source: moa.pdf, Page 3]")
    result = await guard.evaluate(ctx)
    assert result.passed is True


@pytest.mark.asyncio
async def test_fails_without_citation_on_factual_paragraph() -> None:
    """When factual paragraph has no citation, fails."""
    guard = CitationGuardrail(require_source=True)
    ctx = GuardrailContext(
        text="The authorized capital is ₹50,00,000. The face value is ₹10 per share."
    )
    result = await guard.evaluate(ctx)
    assert result.passed is False
    assert "citation" in result.reason.lower() or "citation" in result.rule.lower()
