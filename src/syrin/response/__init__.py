"""Response object returned by agent.response() with content, cost, and metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from syrin.enums import StopReason
from syrin.types import TokenUsage
from syrin.types.validation import ValidationAttempt

T = TypeVar("T")

__all__ = [
    "StructuredOutput",
    "TraceStep",
    "Response",
    "BudgetStatus",
    "GuardrailReport",
    "ContextReport",
    "MemoryReport",
    "TokenReport",
    "OutputReport",
    "RateLimitReport",
    "CheckpointReport",
    "AgentReport",
]


@dataclass
class StructuredOutput:
    """Wrapper for structured output responses.

    Provides easy access to parsed content and raw data with full validation tracking.

    Usage:
        result = agent.response("What is 2+2?", output=MathResult)
        result.structured.result  # Access parsed field
        result.structured.raw    # Raw JSON string

    With validation tracking:
        result.structured.validation_attempts  # All validation attempts
        result.structured.final_error          # Error if validation failed
        result.structured.is_valid             # Whether validation succeeded
        result.structured.all_errors           # List of all errors

    Example:
        # Check if validation succeeded
        if result.structured.is_valid:
            print(result.structured.parsed)
        else:
            print(f"Failed: {result.structured.final_error}")
            # Debug: see all attempts
            for attempt in result.structured.validation_attempts:
                print(f"Attempt {attempt.attempt}: {attempt.error}")
    """

    raw: str = ""
    parsed: Any = None
    _data: dict[str, Any] = field(default_factory=dict)
    validation_attempts: list[ValidationAttempt] = field(default_factory=list)
    final_error: Exception | None = None
    tool_name: str | None = None

    def __getattr__(self, name: str) -> Any:
        """Allow accessing parsed fields directly."""
        if name.startswith("_") or name in (
            "raw",
            "parsed",
            "_data",
            "validation_attempts",
            "final_error",
            "tool_name",
        ):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        # First try _data
        if name in self._data:
            return self._data[name]
        # Then try parsed object
        if self.parsed is not None and hasattr(self.parsed, name):
            return getattr(self.parsed, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    @property
    def is_valid(self) -> bool:
        """Whether validation succeeded."""
        return self.final_error is None and self.parsed is not None

    @property
    def last_error(self) -> str | None:
        """Last error message if any."""
        if self.validation_attempts:
            return self.validation_attempts[-1].error
        return str(self.final_error) if self.final_error else None

    @property
    def all_errors(self) -> list[str]:
        """All error messages from all attempts."""
        return [a.error for a in self.validation_attempts if a.error]

    @property
    def parse_error(self) -> Exception | None:
        """JSON parsing error if any."""
        if self.final_error and "JSON" in str(self.final_error):
            return self.final_error
        return None

    def __str__(self) -> str:
        if self.parsed is not None:
            return str(self.parsed)
        return self.raw

    def __repr__(self) -> str:
        return (
            f"StructuredOutput(raw={self.raw!r}, parsed={self.parsed!r}, is_valid={self.is_valid})"
        )


@dataclass
class TraceStep:
    """A single step in an execution trace."""

    step_type: str
    timestamp: float
    model: str = ""
    tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """One chunk from agent.stream() or agent.astream().

    Why: Build real-time UIs. text is the delta; accumulated_text is full so far.
    cost_so_far and tokens_so_far update as the stream progresses.

    Fields:
        text: New text in this chunk (delta).
        accumulated_text: Full text received so far.
        cost_so_far: Total cost up to this chunk (USD).
        tokens_so_far: TokenUsage (input/output/total) so far.
    """

    text: str = ""
    accumulated_text: str = ""
    cost_so_far: float = 0.0
    tokens_so_far: TokenUsage = field(default_factory=TokenUsage)
    is_final: bool = False
    response: Response[Any] | None = None


@dataclass
class BudgetStatus:
    """Budget status returned by response.budget"""

    remaining: float | None
    used: float
    total: float | None
    cost: float

    def __str__(self) -> str:
        def _fmt(val: float | None) -> str:
            if val is None:
                return "N/A"
            if val < 0.0001:
                return f"{val:.6f}"
            return f"{val:.4f}"

        if self.total is not None:
            return f"BudgetStatus(remaining=${_fmt(self.remaining)}, used=${_fmt(self.used)}, total=${_fmt(self.total)})"
        return f"BudgetStatus(used=${_fmt(self.used)}, unlimited)"


@dataclass
class GuardrailReport:
    """Report of guardrail evaluations for a single run."""

    input_passed: bool = True
    input_reason: str | None = None
    input_guardrails: list[str] = field(default_factory=list)
    output_passed: bool = True
    output_reason: str | None = None
    output_guardrails: list[str] = field(default_factory=list)
    blocked: bool = False
    blocked_stage: str | None = None

    @property
    def passed(self) -> bool:
        return self.input_passed and self.output_passed and not self.blocked


@dataclass
class ContextReport:
    """Report of context usage for a single run."""

    initial_tokens: int = 0
    final_tokens: int = 0
    max_tokens: int = 0
    compressions: int = 0
    offloads: int = 0


@dataclass
class MemoryReport:
    """Report of memory operations for a single run."""

    recalls: int = 0
    stores: int = 0
    forgets: int = 0
    consolidated: int = 0


@dataclass
class TokenReport:
    """Report of token usage for a single run."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class OutputReport:
    """Report of output validation for a single run."""

    validated: bool = False
    attempts: int = 0
    is_valid: bool = True
    final_error: str | None = None


@dataclass
class RateLimitReport:
    """Report of rate limit checks for a single run."""

    checks: int = 0
    throttles: int = 0
    exceeded: bool = False


@dataclass
class CheckpointReport:
    """Report of checkpoint operations for a single run."""

    saves: int = 0
    loads: int = 0


@dataclass
class AgentReport:
    """Aggregated report of all agent operations for a single run.

    Access via response.report or agent.report:

        result = agent.response("Hello")
        result.report.guardrail       # GuardrailReport
        result.report.context         # ContextReport
        result.report.memory         # MemoryReport
        result.report.budget         # BudgetReport (same as response.budget)
        result.report.tokens         # TokenReport
        result.report.output         # OutputReport
        result.report.ratelimits     # RateLimitReport
        result.report.checkpoints    # CheckpointReport
    """

    guardrail: GuardrailReport = field(default_factory=GuardrailReport)
    context: ContextReport = field(default_factory=ContextReport)
    memory: MemoryReport = field(default_factory=MemoryReport)
    budget_remaining: float | None = None
    budget_used: float | None = None
    tokens: TokenReport = field(default_factory=TokenReport)
    output: OutputReport = field(default_factory=OutputReport)
    ratelimits: RateLimitReport = field(default_factory=RateLimitReport)
    checkpoints: CheckpointReport = field(default_factory=CheckpointReport)

    @property
    def budget(self) -> BudgetStatus:
        return BudgetStatus(
            remaining=self.budget_remaining,
            used=self.budget_used or 0.0,
            total=self.budget_remaining + self.budget_used
            if self.budget_remaining is not None and self.budget_used is not None
            else None,
            cost=self.budget_used or 0.0,
        )


@dataclass
class Response(Generic[T]):
    """Result returned by agent.response(), agent.arun().

    Why: Single object for content, cost, tokens, model, and full report. Use
    str(response) for quick printing (returns content).

    Key fields:
        content: Main reply text (or parsed type if output= set).
        cost: USD cost of this run.
        tokens: TokenUsage (input_tokens, output_tokens, total_tokens).
        model: Model ID used.
        stop_reason: Why the run ended (END_TURN, BUDGET, MAX_ITERATIONS, etc.).
        structured: StructuredOutput if output= configured; else None.
        report: Full AgentReport (guardrails, memory, budget, etc.).

    For structured output (output=Output(MyModel)):
        result.data           # Parsed dict
        result.structured.parsed  # Pydantic instance
        result.structured.is_valid  # Validation succeeded

    Example:
        >>> r = agent.response("What is 2+2?")
        >>> print(r.content)
        4
        >>> print(r.cost, r.tokens.total_tokens)
    """

    content: T
    raw: str = ""
    cost: float = 0.0
    tokens: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    duration: float = 0.0
    budget_remaining: float | None = None
    budget_used: float | None = None
    trace: list[TraceStep] = field(default_factory=list)
    tool_calls: list[Any] = field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN
    structured: StructuredOutput | None = None
    iterations: int = 1
    report: AgentReport = field(default_factory=AgentReport)

    @property
    def data(self) -> dict[str, Any] | None:
        """Get parsed data as dictionary - fields from the structured output."""
        if self.structured is not None:
            return self.structured._data
        return None

    def __str__(self) -> str:
        return str(self.content)

    def __bool__(self) -> bool:
        """True if the response completed successfully."""
        return self.stop_reason == StopReason.END_TURN

    @property
    def budget(self) -> BudgetStatus:
        """Get the budget object associated with this response.

        This is a property that returns the full budget object with current status.
        The budget object includes:
        - budget.remaining: remaining budget amount
        - budget.run: total budget cap
        - budget.shared: whether budget is shared with children
        - budget.cost: alias for response.cost (convenience)
        """
        # Return a BudgetStatus object with convenience properties
        return BudgetStatus(
            remaining=self.budget_remaining,
            used=self.budget_used or self.cost,
            total=self.budget_remaining + (self.budget_used or self.cost)
            if self.budget_remaining is not None
            else None,
            cost=self.cost,
        )
