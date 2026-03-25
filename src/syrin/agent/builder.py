"""Agent builder — fluent API for constructing agents with many optional params.

Usage:
    >>> from syrin import Agent, Budget
    >>> agent = (
    ...     Agent.builder(Model.OpenAI("gpt-4o-mini"))
    ...     .with_system_prompt("You are helpful.")
    ...     .with_budget(Budget(max_cost=0.5))
    ...     .with_tools([search, calculate])
    ...     .build()
    ... )
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from syrin.agent import Agent
    from syrin.budget import Budget
    from syrin.context import Context
    from syrin.memory import Memory
    from syrin.model import Model


class AgentBuilder:
    """Fluent builder for Agent instances. Use Agent.builder(model).with_*(...).build()."""

    def __init__(self, model: Model) -> None:
        """Start builder with required model.

        Args:
            model: LLM to use (required).
        """
        self._model = model
        self._system_prompt: str | object = ""
        self._template_variables: dict[str, object] = {}
        self._tools: list[object] = []
        self._budget: Budget | None = None
        self._output: object = None
        self._max_tool_iterations: int = 10
        self._budget_store: object = None
        self._budget_store_key: str = "default"
        self._memory: Memory | None = None
        self._loop_strategy: object = None
        self._custom_loop: object = None
        self._guardrails: object = None
        self._context: Context | None = None
        self._rate_limit: object = None
        self._checkpoint: object = None
        self._debug: bool = False
        self._tracer: object = None
        self._event_bus: object = None

    def with_system_prompt(self, prompt: str | object) -> AgentBuilder:
        """Set system prompt (str, Prompt from @prompt, or callable)."""
        self._system_prompt = prompt if prompt is not None else ""
        return self

    def with_template_variables(self, variables: dict[str, object]) -> AgentBuilder:
        """Set template variables for dynamic system prompts."""
        self._template_variables = dict(variables) if variables else {}
        return self

    def with_tools(self, tools: list[object]) -> AgentBuilder:
        """Set tools list."""
        self._tools = list(tools) if tools else []
        return self

    def with_budget(self, budget: Budget) -> AgentBuilder:
        """Set budget (run/period limits)."""
        self._budget = budget
        return self

    def with_output(self, output: object) -> AgentBuilder:
        """Set structured output config."""
        self._output = output
        return self

    def with_max_tool_iterations(self, n: int) -> AgentBuilder:
        """Set max tool-call iterations per response."""
        self._max_tool_iterations = n
        return self

    def with_budget_store(self, store: object, key: str = "default") -> AgentBuilder:
        """Set budget store for persistence."""
        self._budget_store = store
        self._budget_store_key = key
        return self

    def with_memory(self, memory: Memory) -> AgentBuilder:
        """Set conversation or persistent memory."""
        self._memory = memory
        return self

    def with_loop_strategy(self, strategy: object) -> AgentBuilder:
        """Set loop strategy (REACT, SINGLE_SHOT, etc.)."""
        self._loop_strategy = strategy
        return self

    def with_custom_loop(self, loop: object) -> AgentBuilder:
        """Set custom Loop instance."""
        self._custom_loop = loop
        return self

    def with_guardrails(self, guardrails: object) -> AgentBuilder:
        """Set guardrails."""
        self._guardrails = guardrails
        return self

    def with_context(self, context: Context) -> AgentBuilder:
        """Set context config (max_tokens, thresholds)."""
        self._context = context
        return self

    def with_rate_limit(self, rate_limit: object) -> AgentBuilder:
        """Set rate limit config."""
        self._rate_limit = rate_limit
        return self

    def with_checkpoint(self, checkpoint: object) -> AgentBuilder:
        """Set checkpoint config."""
        self._checkpoint = checkpoint
        return self

    def with_debug(self, debug: bool = True) -> AgentBuilder:
        """Enable debug (print events to console)."""
        self._debug = debug
        return self

    def with_tracer(self, tracer: object) -> AgentBuilder:
        """Set custom tracer."""
        self._tracer = tracer
        return self

    def with_event_bus(self, event_bus: object) -> AgentBuilder:
        """Set event bus for typed domain events."""
        self._event_bus = event_bus
        return self

    def build(self) -> Agent:
        """Build and return the Agent."""
        from syrin.agent import Agent
        from syrin.agent.config import AgentConfig

        config: AgentConfig | None = None
        if any(
            x is not None
            for x in (
                self._context,
                self._rate_limit,
                self._checkpoint,
                self._tracer,
                self._event_bus,
            )
        ):
            config = AgentConfig(
                context=self._context,
                rate_limit=self._rate_limit,  # type: ignore[arg-type]
                checkpoint=self._checkpoint,  # type: ignore[arg-type]
                tracer=self._tracer,  # type: ignore[arg-type]
                event_bus=self._event_bus,  # type: ignore[arg-type]
            )

        return Agent(
            model=self._model,
            system_prompt=self._system_prompt,  # type: ignore[arg-type]
            template_variables=self._template_variables,
            tools=self._tools,  # type: ignore[arg-type]
            budget=self._budget,
            output=self._output,  # type: ignore[arg-type]
            max_tool_iterations=self._max_tool_iterations,
            budget_store=self._budget_store,  # type: ignore[arg-type]
            budget_store_key=self._budget_store_key,
            memory=self._memory,
            loop_strategy=self._loop_strategy,  # type: ignore[arg-type]
            custom_loop=self._custom_loop,  # type: ignore[arg-type]
            guardrails=self._guardrails,  # type: ignore[arg-type]
            debug=self._debug,
            config=config,
        )
