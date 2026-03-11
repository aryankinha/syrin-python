"""Tests for FactVerificationGuardrail."""

from __future__ import annotations

import pytest

from syrin.enums import VerificationStatus
from syrin.guardrails.built_in.fact_verification import FactVerificationGuardrail
from syrin.guardrails.context import GuardrailContext
from syrin.knowledge._grounding import GroundedFact


class _FakeFact:
    content: str
    confidence: float
    verification: object

    def __init__(self, content: str, confidence: float, verification: VerificationStatus) -> None:
        self.content = content
        self.confidence = confidence
        self.verification = verification


@pytest.mark.asyncio
async def test_passes_when_no_grounded_facts() -> None:
    """When metadata has no grounded_facts, passes (no-op)."""
    guard = FactVerificationGuardrail()
    ctx = GuardrailContext(text="The capital is ₹50,00,000.", metadata={})
    result = await guard.evaluate(ctx)
    assert result.passed is True
    assert "skipping" in result.reason.lower() or "skipping" in str(result.metadata).lower()


@pytest.mark.asyncio
async def test_passes_when_claims_match_verified_facts() -> None:
    """When output matches verified fact content, passes."""
    guard = FactVerificationGuardrail()
    facts = [
        GroundedFact(
            "The authorized capital is ₹50,00,000.",
            "moa.pdf",
            confidence=0.9,
            verification=VerificationStatus.VERIFIED,
        ),
    ]
    ctx = GuardrailContext(
        text="The authorized capital is ₹50,00,000. [Source: moa.pdf]",
        metadata={"grounded_facts": facts},
    )
    result = await guard.evaluate(ctx)
    assert result.passed is True


@pytest.mark.asyncio
async def test_passes_with_empty_facts() -> None:
    """When grounded_facts is empty list, passes."""
    guard = FactVerificationGuardrail()
    ctx = GuardrailContext(text="Some text.", metadata={"grounded_facts": []})
    result = await guard.evaluate(ctx)
    assert result.passed is True
