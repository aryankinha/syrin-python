"""Budget-related exceptions."""

from __future__ import annotations


class BudgetAllocationError(Exception):
    """Raised when a budget allocation fails.

    Allocation fails when:
    - The requested amount exceeds ``per_agent_max``
    - The requested amount exceeds the pool's remaining balance
    - The agent was already allocated a budget in the current pool

    Attributes:
        agent_id: The agent ID that triggered the error.
        amount: The amount that was requested.
        reason: Human-readable explanation.

    Example::

        try:
            await pool.allocate("agent-1", 5.00)
        except BudgetAllocationError as exc:
            print(exc.reason)
    """

    def __init__(
        self,
        message: str,
        *,
        agent_id: str = "",
        amount: float = 0.0,
        reason: str = "",
    ) -> None:
        """Initialise BudgetAllocationError.

        Args:
            message: Exception message.
            agent_id: The agent whose allocation failed.
            amount: The amount requested.
            reason: Additional context.
        """
        super().__init__(message)
        self.agent_id = agent_id
        self.amount = amount
        self.reason = reason or message
