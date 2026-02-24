"""Comprehensive test suite for Syrin Guardrails Authority Layer (Phase 2).

Test Driven Development approach - all tests written before implementation.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest


class TestAuthorityCheck:
    """Tests for AuthorityCheck guardrail."""

    @pytest.fixture
    def mock_context_with_user(self):
        """Create context with user."""
        from syrin.enums import GuardrailStage
        from syrin.guardrails.context import GuardrailContext

        user = Mock()
        user.id = "user123"
        user.has_permission = Mock(return_value=True)

        return GuardrailContext(text="Test action", stage=GuardrailStage.ACTION, user=user)

    @pytest.mark.asyncio
    async def test_authority_check_user_has_permission(self, mock_context_with_user):
        """Test that check passes when user has permission."""
        from syrin.guardrails.built_in.authority import AuthorityCheck

        guardrail = AuthorityCheck(requires="write")
        result = await guardrail.evaluate(mock_context_with_user)

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_authority_check_no_user(self):
        """Test that check fails when no user in context."""
        from syrin.guardrails.built_in.authority import AuthorityCheck
        from syrin.guardrails.context import GuardrailContext

        context = GuardrailContext(text="Test", user=None)
        guardrail = AuthorityCheck(requires="write")

        result = await guardrail.evaluate(context)

        assert result.passed is False


class TestBudgetEnforcer:
    """Tests for BudgetEnforcer guardrail."""

    @pytest.mark.asyncio
    async def test_budget_enforcer_sufficient_funds(self):
        """Test that check passes with sufficient budget."""
        from syrin.guardrails.built_in.budget import BudgetEnforcer
        from syrin.guardrails.context import GuardrailContext

        budget = Mock()
        budget.remaining = 100.0

        context = GuardrailContext(text="Transfer", budget=budget)
        guardrail = BudgetEnforcer(max_amount=50)
        result = await guardrail.evaluate(context)

        assert result.passed is True


class TestThresholdApproval:
    """Tests for ThresholdApproval (K-of-N) guardrail."""

    @pytest.mark.asyncio
    async def test_threshold_approval_collects_approvals(self):
        """Test that threshold approval collects K of N approvals."""
        from syrin.guardrails.built_in.threshold import ThresholdApproval
        from syrin.guardrails.context import GuardrailContext

        guardrail = ThresholdApproval(k=2, n=3)
        context = GuardrailContext(text="Transfer $10000")

        result = await guardrail.evaluate(context)

        # Initial state: no approvals yet
        assert result.passed is False


class TestHumanApproval:
    """Tests for HumanApproval guardrail."""

    @pytest.mark.asyncio
    async def test_human_approval_requests_approval(self):
        """Test that human approval is requested."""
        from syrin.guardrails.built_in.human import HumanApproval
        from syrin.guardrails.context import GuardrailContext

        guardrail = HumanApproval(approver="admin@example.com")
        context = GuardrailContext(text="Delete database")

        result = await guardrail.evaluate(context)

        assert result.passed is False


class TestCapabilityToken:
    """Tests for capability token system."""

    def test_token_creation(self):
        """Test creating a capability token."""
        from syrin.guardrails.auth.capability import CapabilityToken

        token = CapabilityToken(scope="finance:transfer", budget=100)

        assert token.scope == "finance:transfer"
        assert token.budget == 100

    def test_token_consumption(self):
        """Test consuming token budget."""
        from syrin.guardrails.auth.capability import CapabilityToken

        token = CapabilityToken(scope="api:call", budget=10)

        assert token.consume(3) is True
        assert token.budget == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
