"""Agent configuration — grouped advanced options to reduce constructor parameters.

Use AgentConfig to pass context, rate_limit, checkpoint, circuit_breaker, approval_gate,
tracer, event_bus, audit, and dependencies in a single object. Keeps Agent.__init__
under 20 parameters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from syrin.checkpoint import CheckpointConfig, Checkpointer
from syrin.enums import ToolErrorMode

if TYPE_CHECKING:
    from syrin.audit import AuditLog
    from syrin.circuit import CircuitBreaker
    from syrin.context import Context, DefaultContextManager
    from syrin.domain_events import EventBus
    from syrin.hitl import ApprovalGate
    from syrin.observability import Tracer
    from syrin.ratelimit import APIRateLimit, RateLimitManager


class AgentConfig:
    """Grouped advanced configuration for Agent. Reduces constructor parameter count.

    Pass to Agent(config=AgentConfig(...)) for context, rate_limit, checkpoint,
    circuit_breaker, approval_gate, tracer, event_bus, audit, and dependencies.

    Example:
        >>> from syrin import Agent, AgentConfig, Budget
        >>> from syrin.audit import AuditLog
        >>> config = AgentConfig(
        ...     context=Context(max_tokens=4000),
        ...     audit=AuditLog(path="./audit.jsonl"),
        ... )
        >>> agent = Agent(model=Model.Almock(), system_prompt="Hi", config=config)
    """

    __slots__ = (
        "context",
        "rate_limit",
        "checkpoint",
        "circuit_breaker",
        "approval_gate",
        "tracer",
        "event_bus",
        "audit",
        "dependencies",
        "spotlight_tool_outputs",
        "normalize_inputs",
        "tool_error_mode",
    )

    def __init__(  # type: ignore[explicit-any]
        self,
        *,
        context: Context | DefaultContextManager | None = None,
        rate_limit: APIRateLimit | RateLimitManager | None = None,
        checkpoint: CheckpointConfig | Checkpointer | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        approval_gate: ApprovalGate | None = None,
        tracer: Tracer | None = None,
        event_bus: EventBus[Any] | None = None,
        audit: AuditLog | None = None,
        dependencies: object | None = None,
        spotlight_tool_outputs: bool = False,
        normalize_inputs: bool = False,
        tool_error_mode: ToolErrorMode = ToolErrorMode.PROPAGATE,
    ) -> None:
        """Create AgentConfig with optional advanced options.

        Args:
            context: Context config (max_tokens, token_limits, thresholds).
            rate_limit: APIRateLimit or RateLimitManager for RPM/TPM enforcement.
            checkpoint: CheckpointConfig or Checkpointer for save/restore state.
            circuit_breaker: CircuitBreaker for LLM provider failure handling.
            approval_gate: ApprovalGate for human-in-the-loop tool approval.
            tracer: Custom Tracer for observability (spans, traces).
            event_bus: EventBus for typed domain events (BudgetThresholdReached, etc.).
            audit: AuditLog for compliance logging (LLM calls, tool calls, handoffs).
            dependencies: Injected deps for tools (RunContext.deps). Enables testing
                and multi-tenant (different deps per user).
            spotlight_tool_outputs: 6.2: Wrap tool output in trust-label delimiters
                (spotlighting) before inserting into context. Reduces prompt injection
                risk from tool outputs. Default: False.
            normalize_inputs: 6.1: Apply NFKC normalization + control-char stripping
                to user input before processing. Default: False.
            tool_error_mode: How tool exceptions are handled. PROPAGATE (default) re-raises
                immediately. RETURN_AS_STRING returns error message to LLM. STOP raises
                ToolExecutionError to the caller.
        """
        self.context = context
        self.rate_limit = rate_limit
        self.checkpoint = checkpoint
        self.circuit_breaker = circuit_breaker
        self.approval_gate = approval_gate
        self.tracer = tracer
        self.event_bus = event_bus
        self.audit = audit
        self.dependencies = dependencies
        self.spotlight_tool_outputs = spotlight_tool_outputs
        self.normalize_inputs = normalize_inputs
        self.tool_error_mode = tool_error_mode
