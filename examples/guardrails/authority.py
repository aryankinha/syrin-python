"""
Syrin Guardrails - Authority Layer Examples

Permission-based authorization, budget enforcement, human approval,
threshold consensus, and capability tokens.
"""

import asyncio
from unittest.mock import Mock


async def example_authority_check():
    """Permission-based authorization."""
    print("\n=== Authority Check ===\n")

    from syrin.enums import GuardrailStage
    from syrin.guardrails import AuthorityCheck, GuardrailContext

    # Create a user with permissions
    user = Mock()
    user.id = "trader123"
    user.has_permission = Mock(return_value=True)

    context = GuardrailContext(text="Transfer $5000", stage=GuardrailStage.ACTION, user=user)

    # Check permission
    guardrail = AuthorityCheck(requires="finance:transfer")
    result = await guardrail.evaluate(context)

    print(f"User has 'finance:transfer' permission: {result.passed}")

    # Now check a permission the user doesn't have
    user.has_permission.return_value = False
    result = await guardrail.evaluate(context)

    print(f"User lacks permission: {not result.passed}")
    print(f"  Reason: {result.reason}")


async def example_budget_enforcer():
    """Budget enforcement for actions."""
    print("\n=== Budget Enforcer ===\n")

    from syrin.guardrails import BudgetEnforcer, GuardrailContext

    # Mock budget
    budget = Mock()
    budget.remaining = 1000.0
    budget.consume = Mock()

    # Mock action
    action = Mock()
    action.name = "transfer_funds"
    action.amount = 500.0

    context = GuardrailContext(text="Transfer $500", budget=budget, action=action)

    guardrail = BudgetEnforcer(max_amount=1000)
    result = await guardrail.evaluate(context)

    print(f"Transfer $500 with $1000 budget: {'✓' if result.passed else '✗'}")

    # Try to transfer too much
    action.amount = 1500.0
    result = await guardrail.evaluate(context)

    print(f"Transfer $1500 with $1000 limit: {'✓' if result.passed else '✗'}")
    print(f"  Reason: {result.reason}")


async def example_threshold_approval():
    """K-of-N threshold approval."""
    print("\n=== Threshold Approval ===\n")

    from syrin.guardrails import GuardrailContext, ThresholdApproval

    # Create threshold requiring 2 of 3 approvals
    guardrail = ThresholdApproval(
        k=2, n=3, approvers=["alice@example.com", "bob@example.com", "charlie@example.com"]
    )

    context = GuardrailContext(
        text="Delete production database", metadata={"request_id": "req_delete_001"}
    )

    # Initial state - no approvals
    result = await guardrail.evaluate(context)
    print(f"Initial state: {result.passed}")
    print(f"  Status: {result.reason}")
    print(f"  Approvals needed: {result.metadata['approvals_needed']}")

    # Add first approval
    guardrail.add_approval("req_delete_001", "alice@example.com")
    result = await guardrail.evaluate(context)
    print(f"\nAfter 1 approval: {result.passed}")
    print(f"  Approvals: {result.metadata.get('approvals_received', 0)}/2")

    # Add second approval - threshold met!
    guardrail.add_approval("req_delete_001", "bob@example.com")
    result = await guardrail.evaluate(context)
    print(f"\nAfter 2 approvals: {result.passed}")
    print(f"  ✓ Threshold met! Approved by: {result.metadata.get('approvers', [])}")


async def example_human_approval():
    """Human-in-the-loop approval."""
    print("\n=== Human Approval ===\n")

    from syrin.guardrails import GuardrailContext, HumanApproval

    guardrail = HumanApproval(
        approver="admin@example.com",
        requires_justification=True,
        timeout=300,  # 5 minutes
    )

    context = GuardrailContext(
        text="Deploy to production", metadata={"request_id": "req_deploy_001"}
    )

    # Request approval
    result = await guardrail.evaluate(context)
    print(f"Approval requested: {not result.passed}")
    print(f"  Approver: {result.metadata['approver']}")
    print(f"  Requires justification: {result.metadata['requires_justification']}")

    # Simulate admin approval
    guardrail.approve(
        request_id="req_deploy_001",
        approver="admin@example.com",
        justification="Code reviewed and tested",
    )

    result = await guardrail.evaluate(context)
    print(f"\nAfter approval: {result.passed}")
    print(f"  Approved by: {result.metadata['approved_by']}")
    print(f"  Justification: {result.metadata.get('justification')}")


async def example_capability_tokens():
    """Capability tokens with budget and TTL."""
    print("\n=== Capability Tokens ===\n")

    from syrin.guardrails import CapabilityIssuer

    # Issue a capability token
    issuer = CapabilityIssuer()
    token = issuer.issue(
        scope="reports:generate",
        budget=5,
        ttl=3600,  # 1 hour
        issued_to="analyst789",
    )

    print("Token issued:")
    print(f"  Scope: {token.scope}")
    print(f"  Budget: {token.budget}")
    print(f"  Valid: {token.is_valid()}")

    # Check permissions
    print(f"\nCan generate reports: {token.can('reports:generate')}")
    print(f"Can delete data: {token.can('data:delete')}")

    # Consume budget
    for i in range(6):
        success = token.consume(1)
        print(f"  Use {i + 1}: {'✓' if success else '✗'} (budget: {token.budget})")

    print(f"\nToken exhausted: {not token.is_valid()}")


async def example_capability_guardrail():
    """Capability-based guardrail."""
    print("\n=== Capability Guardrail ===\n")

    from unittest.mock import Mock

    from syrin.guardrails import CapabilityGuardrail, CapabilityToken

    # Create token
    token = CapabilityToken(scope="finance:transfer", budget=10)

    # Create user with token
    user = Mock()
    user.get_capability_token = Mock(return_value=token)

    context = Mock()
    context.user = user

    # Check capability
    guardrail = CapabilityGuardrail(required_capability="finance:transfer")
    result = await guardrail.evaluate(context)

    print(f"Has capability 'finance:transfer': {result.passed}")
    print(f"  Remaining budget: {result.metadata.get('remaining_budget')}")

    # Check different capability
    guardrail = CapabilityGuardrail(required_capability="admin:delete")
    result = await guardrail.evaluate(context)

    print(f"\nHas capability 'admin:delete': {result.passed}")
    print(f"  Reason: {result.reason}")


async def example_combined_authority_workflow():
    """Complete authority workflow combining all features."""
    print("\n=== Complete Authority Workflow ===\n")

    from syrin.guardrails import (
        AuthorityCheck,
        BudgetEnforcer,
        GuardrailContext,
        ParallelEvaluationEngine,
        ThresholdApproval,
    )

    # Setup user
    user = Mock()
    user.id = "manager456"
    user.has_permission = Mock(return_value=True)

    # Setup budget
    budget = Mock()
    budget.remaining = 50000
    budget.consume = Mock()

    # Setup action
    action = Mock()
    action.name = "large_transfer"
    action.amount = 25000

    context = GuardrailContext(
        text="Transfer $25000",
        user=user,
        budget=budget,
        action=action,
        metadata={"request_id": "req_large_001"},
    )

    # Combine all guardrails
    guardrails = [
        AuthorityCheck(requires="finance:transfer"),
        BudgetEnforcer(max_amount=25000),
        ThresholdApproval(k=2, n=3, condition=lambda ctx: ctx.action.amount > 10000),
    ]

    engine = ParallelEvaluationEngine()
    result = await engine.evaluate(context, guardrails)

    print(f"Workflow result: {'✓ PASSED' if result.passed else '✗ BLOCKED'}")
    print("  Decisions:")
    for decision in result.decisions:
        status = "✓" if decision.passed else "✗"
        print(f"    {status} {decision.rule}: {decision.reason[:50]}...")

    if not result.passed:
        print(f"\n  Blocking reason: {result.reason}")


async def main():
    """Run all authority examples."""
    print("=" * 70)
    print("Syrin Guardrails - Authority Layer Examples")
    print("=" * 70)

    await example_authority_check()
    await example_budget_enforcer()
    await example_threshold_approval()
    await example_human_approval()
    await example_capability_tokens()
    await example_capability_guardrail()
    await example_combined_authority_workflow()

    print("\n" + "=" * 70)
    print("All authority examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
