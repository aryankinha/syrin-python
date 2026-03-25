---
title: Error Handling
description: Handle agent failures gracefully with try/catch patterns and recovery strategies.
weight: 85
---

## Things Break — Plan for It

Network timeouts. Rate limits. Budget exceeded. Tool failures. Model unavailability. The question isn't if your agent encounters errors—it's whether your code handles them gracefully.

Syrin gives you a complete exception hierarchy and retry mechanisms so your agents stay resilient when the unexpected happens.

## The Problem

Consider what can go wrong:

```python
result = agent.run("Analyze this report")
# What if:
# - API key is invalid?
# - Model is rate limited?
# - Budget is exhausted?
# - Tool execution fails?
# - Guardrails block the response?
```

Without proper error handling, your application crashes, users see stack traces, and you have no visibility into what happened.

## The Solution

Syrin's exception hierarchy lets you catch exactly what you need:

```python
from syrin import Agent, Model
from syrin.exceptions import (
    SyrinError,
    BudgetExceededError,
    ToolExecutionError,
    ProviderError,
    GuardrailBlockedError,
)

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a helpful assistant.",
)

try:
    result = agent.run("Analyze this data")
    print(result.content)
    
except BudgetExceededError as e:
    print(f"Budget exceeded: {e.limit}")
    # Suggest upgrading or wait for reset
    
except ToolExecutionError as e:
    print(f"Tool failed: {e}")
    # Log, retry, or fallback
    
except ProviderError as e:
    print(f"API error: {e}")
    # Retry with backoff or switch provider
    
except GuardrailBlockedError as e:
    print(f"Blocked: {e.reason}")
    # Inform user about policy violation
    
except SyrinError as e:
    print(f"Unexpected Syrin error: {e}")
    # Catch-all for any Syrin-specific error
```

**What just happened:** We caught specific error types with appropriate handlers. Each exception carries context about what went wrong.

## Exception Hierarchy

All Syrin exceptions inherit from `SyrinError`:

```
SyrinError
├── BudgetExceededError
├── BudgetThresholdError
├── ModelNotFoundError
├── ProviderError
├── ProviderNotFoundError
├── ToolExecutionError
├── TaskError
├── ValidationError
├── HandoffBlockedError
├── HandoffRetryRequested
├── CircuitBreakerOpenError
└── NoMatchingProfileError
```

### BudgetExceededError

Raised when a cost or token limit is hit:

```python
except BudgetExceededError as e:
    print(f"Spent ${e.current_cost} of ${e.limit} ({e.budget_type})")
```

### ToolExecutionError

Raised when a tool fails during execution:

```python
except ToolExecutionError as e:
    print(f"Tool '{e.tool_name}' failed")
    print(f"Original error: {e.__cause__}")
```

### ProviderError

Raised when the LLM provider returns an error:

```python
except ProviderError as e:
    if "rate_limit" in str(e).lower():
        # Wait and retry
        time.sleep(60)
    else:
        raise
```

### ValidationError

Raised when structured output validation fails:

```python
except ValidationError as e:
    print(f"Validation failed after {len(e.attempts)} attempts")
    print(f"Last error: {e.last_error}")
```

## Retry Patterns

Implement intelligent retries for transient failures:

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(ProviderError),
)
async def call_agent_with_retry(agent, prompt):
    return await agent.arun(prompt)
```

**What just happened:** We used the `tenacity` library to implement exponential backoff for provider errors. Three attempts with increasing waits between them.

## Circuit Breaker Pattern

Prevent cascade failures when a service is down:

```python
from syrin.circuit import CircuitBreaker, CircuitState

breaker = CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60,      # Try again after 60 seconds
)

try:
    with breaker:
        result = agent.run(prompt)
except CircuitBreakerOpenError as e:
    print(f"Circuit open until {e.recovery_at}")
    # Fallback to cached response or degraded mode
```

## Fallback Strategies

Provide alternatives when the primary path fails:

```python
def get_agent_response(agent, user_input):
    try:
        return agent.run(user_input)
    except BudgetExceededError:
        return agent.run(
            "Please summarize your question in 50 words or less.",
        )
    except ProviderError:
        # Use cached response or static answer
        return fallback_response(user_input)
```

**What just happened:** We implemented tiered fallbacks. Budget exceeded gets a shorter prompt. Provider errors get a static or cached response.

## Error Recovery Hooks

Use hooks to monitor and respond to errors:

```python
agent.events.on("tool.error", lambda e: 
    log_error(f"Tool {e['tool_name']} failed: {e['error']}")
)

agent.events.on("budget.threshold", lambda e:
    notify(f"Budget at {e['percent']}%")
)

agent.events.on("llm.retry", lambda e:
    log_warning(f"Retrying after {e.get('error', 'unknown error')}")
)
```

## Stop Reasons

When an agent run ends, `result.stop_reason` tells you why:

```python
result = agent.run("Complex task")

stop_reasons = {
    "end_turn": "Normal completion",
    "budget": "Budget limit reached",
    "max_iterations": "Iteration limit reached",
    "timeout": "Execution timed out",
    "tool_error": "A tool failed",
    "guardrail": "Blocked by guardrails",
    "cancelled": "Cancelled by user",
}
print(stop_reasons.get(result.stop_reason, "Unknown"))
```

## Complete Error Handling Pattern

A production-ready pattern:

```python
from syrin import Agent, Model
from syrin.exceptions import (
    SyrinError,
    BudgetExceededError,
    ProviderError,
    ToolExecutionError,
)

class AgentHandler:
    def __init__(self):
        self.agent = Agent(
            model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
            system_prompt="You are a helpful assistant.",
        )
        self.setup_hooks()
    
    def setup_hooks(self):
        self.agent.events.on("tool.error", self._log_tool_error)
        self.agent.events.on("budget.threshold", self._log_budget_warning)
    
    def _log_tool_error(self, event):
        logger.error(f"Tool error: {event}")
    
    def _log_budget_warning(self, event):
        logger.warning(f"Budget warning: {event}")
    
    def get_response(self, user_input: str) -> str:
        try:
            result = self.agent.run(user_input)
            return result.content
            
        except BudgetExceededError as e:
            return f"I've reached my spending limit for now. ({e.limit})"
            
        except ToolExecutionError as e:
            logger.error(f"Tool failed: {e}")
            return "A tool encountered an error. Please try again."
            
        except ProviderError as e:
            logger.error(f"Provider error: {e}")
            return "The AI service is temporarily unavailable."
            
        except SyrinError as e:
            logger.exception("Syrin error")
            return "An unexpected error occurred."
```

**What just happened:** We created a handler class with proper error categorization, logging, and user-friendly messages for each error type.

---

## What's Next?

- [Debugging: Overview](/debugging/overview) — Tools for understanding failures
- [Production: Circuit Breaker](/production/circuit-breaker) — Prevent cascade failures
- [Production: Rate Limiting](/production/rate-limiting) — Handle provider limits

## See Also

- [Core Concepts: Budget](/core/budget) — Budget error handling
- [Agents: Guardrails](/agent/guardrails) — Content validation errors
- [Debugging: Hooks Reference](/debugging/hooks-reference) — Error-related hooks
