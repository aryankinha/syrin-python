"""Budget enforcer guardrail for cost control."""

from __future__ import annotations

from syrin.enums import DecisionAction
from syrin.guardrails.base import Guardrail
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision


class BudgetEnforcer(Guardrail):
    """Guardrail that enforces budget limits on actions.

    Validates that an action stays within budget constraints.
    Can enforce per-action limits, daily limits, and weekly limits.

    Example:
        >>> guardrail = BudgetEnforcer(max_amount=1000)
        >>> result = await guardrail.evaluate(context)

        >>> guardrail = BudgetEnforcer(
        ...     max_amount=100,
        ...     daily_limit=1000,
        ...     warn_threshold=0.8
        ... )
    """

    def __init__(
        self,
        max_amount: float,
        daily_limit: float | None = None,
        weekly_limit: float | None = None,
        limits_by_action: dict[str, float] | None = None,
        cost: float = 0.0,
        warn_threshold: float | None = None,
        fail_on_no_budget: bool = False,
        name: str | None = None,
    ):
        """Initialize budget enforcer.

        Args:
            max_amount: Maximum amount allowed for this action.
            daily_limit: Optional daily spending limit.
            weekly_limit: Optional weekly spending limit.
            limits_by_action: Dict mapping action names to their limits.
            cost: Cost of this operation (to consume from budget).
            warn_threshold: Fraction of budget remaining to trigger warning.
            fail_on_no_budget: If True, fail when no budget tracker present.
            name: Optional custom name.
        """
        super().__init__(name)
        self.max_amount = max_amount
        self.daily_limit = daily_limit
        self.weekly_limit = weekly_limit
        self.limits_by_action = limits_by_action or {}
        self.cost = cost
        self.warn_threshold = warn_threshold
        self.fail_on_no_budget = fail_on_no_budget

    async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
        """Check if action is within budget.

        Args:
            context: Guardrail context with budget.

        Returns:
            GuardrailDecision indicating budget status.
        """
        # Get action amount
        action_amount = self._get_action_amount(context)

        # Check per-action limits
        if context.action and hasattr(context.action, "name"):
            action_name = context.action.name
            if action_name in self.limits_by_action:
                limit = self.limits_by_action[action_name]
                if action_amount > limit:
                    return GuardrailDecision(
                        passed=False,
                        rule="action_limit_exceeded",
                        reason=f"Amount ${action_amount} exceeds action limit of ${limit}",
                        action=DecisionAction.BLOCK,
                        metadata={"action": action_name, "amount": action_amount, "limit": limit},
                    )

        # Check if no budget
        if context.budget is None:
            if self.fail_on_no_budget:
                return GuardrailDecision(
                    passed=False,
                    rule="no_budget",
                    reason="No budget tracker available",
                    action=DecisionAction.BLOCK,
                )
            else:
                # Pass when no budget (fail open)
                return GuardrailDecision(
                    passed=True,
                    rule="no_budget",
                    reason="No budget tracking, allowing by default",
                    metadata={"fail_on_no_budget": False},
                )

        budget = context.budget
        remaining = getattr(budget, "remaining", 0)
        if remaining is None:
            remaining = float("inf")  # Unlimited budget

        # Check for negative budget
        if remaining < 0:
            return GuardrailDecision(
                passed=False,
                rule="budget_negative",
                reason=f"Budget is negative: ${remaining}",
                action=DecisionAction.BLOCK,
                metadata={"remaining": remaining},
            )

        # Check max amount
        if action_amount > self.max_amount:
            return GuardrailDecision(
                passed=False,
                rule="budget_exceeded",
                reason=f"Amount ${action_amount} exceeds maximum of ${self.max_amount}",
                action=DecisionAction.BLOCK,
                metadata={
                    "amount": action_amount,
                    "max_amount": self.max_amount,
                    "remaining": remaining,
                },
            )

        # Check if sufficient budget remains
        if remaining < action_amount:
            return GuardrailDecision(
                passed=False,
                rule="budget_exceeded",
                reason=f"Insufficient budget: ${remaining} < ${action_amount}",
                action=DecisionAction.BLOCK,
                metadata={
                    "amount": action_amount,
                    "remaining": remaining,
                    "shortfall": action_amount - remaining,
                },
            )

        # Check warning threshold
        if self.warn_threshold is not None:
            limit_raw = getattr(budget, "limit", None) or getattr(budget, "run", remaining)
            warn_limit: float = remaining if limit_raw is None else float(limit_raw)
            if warn_limit > 0:
                ratio = remaining / warn_limit
                if ratio < self.warn_threshold:
                    # Consume budget if checks passed
                    if hasattr(budget, "consume"):
                        budget.consume(self.cost)

                    return GuardrailDecision(
                        passed=True,
                        rule="budget_warning",
                        reason=f"Budget approaching limit: {ratio:.1%} remaining",
                        action=DecisionAction.WARN,
                        metadata={
                            "remaining": remaining,
                            "limit": warn_limit,
                            "ratio": ratio,
                            "threshold": self.warn_threshold,
                        },
                        budget_consumed=self.cost,
                    )

        # All checks passed - consume budget
        if hasattr(budget, "consume"):
            budget.consume(self.cost)

        return GuardrailDecision(
            passed=True,
            rule="budget_sufficient",
            metadata={
                "amount": action_amount,
                "remaining": remaining - action_amount,
                "limits": {
                    "max": self.max_amount,
                    "daily": self.daily_limit,
                    "weekly": self.weekly_limit,
                },
            },
            budget_consumed=self.cost,
        )

    def _get_action_amount(self, context: GuardrailContext) -> float:
        """Extract amount from action or context.

        Args:
            context: Guardrail context.

        Returns:
            Amount value (defaults to 0).
        """
        if context.action is None:
            return 0.0

        # Try common amount attributes
        for attr in ["amount", "cost", "price", "value"]:
            if hasattr(context.action, attr):
                try:
                    return float(getattr(context.action, attr))
                except (TypeError, ValueError):
                    continue

        return 0.0
