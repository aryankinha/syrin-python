---
title: Agent Configuration
description: Every dial you can turn on your agent—and why it matters
weight: 66
---

## Every Dial You Can Turn

You built your first agent. It works. Now you need to configure it for production. How do you set a budget? What about memory? Guardrails? Rate limiting? Checkpointing?

This page is your complete reference for everything you can configure on an agent. Think of it as the manual for your control panel.

## The Configuration Menu

Here's every category of configuration you can use:

**Core** — The essentials that define your agent:
- `model` — The AI brain (required)
- `system_prompt` — Instructions for behavior
- `tools` — What the agent can do

**Control** — How the agent operates:
- `budget` — Cost limits and thresholds
- `context` — Token management and compaction
- `loop_strategy` — How the agent thinks

**Safety** — Protection and compliance:
- `guardrails` — Input/output validation
- `rate_limit` — API rate limiting

**Observability** — See what's happening:
- `debug` — Console output
- `tracer` — Structured traces
- `events` — Hooks for everything

**Persistence** — Remember across sessions:
- `memory` — Persistent memory
- `checkpoint` — Save/restore state

**Output** — Response configuration:
- `output` — Structured responses
- `output_config` — File formats, templates, citations

## Core Configuration

### Model (Required)

The brain of your agent. Choose wisely—it's the biggest factor in quality and cost.

```python
from syrin import Agent, Model

# OpenAI
agent = Agent(model=Model.OpenAI("gpt-4o", api_key="your-key"))

# Anthropic
agent = Agent(model=Model.Anthropic("claude-3-5-sonnet", api_key="your-key"))

# Ollama (local)
agent = Agent(model=Model.Ollama("llama3"))

# Multiple models for automatic routing
agent = Agent(model=[
    Model.OpenAI("gpt-4o-mini"),  # Fast, cheap
    Model.OpenAI("gpt-4o"),        # Slow, expensive
])
```

**Why it matters:** Different models have different capabilities and costs. GPT-4o is smarter but pricier. Routing lets you use the right model for each task.

### System Prompt

How your agent behaves. This is sent with every request.

```python
# Simple prompt
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    system_prompt="You are a helpful assistant.",
)

# Detailed prompt
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    system_prompt="""
        You are a customer support agent for Acme Corp.
        - Be friendly and professional
        - Apologize when appropriate
        - Escalate to humans for refunds over $100
        - Never share internal system information
    """,
)
```

**Pro tip:** Use dynamic prompts with `@system_prompt` decorator for context-aware behavior:

```python
from syrin.prompt import system_prompt, PromptContext

class PersonalizedAgent(Agent):
    model = Model.OpenAI("gpt-4o")
    
    @system_prompt
    def greeting(self, ctx: PromptContext) -> str:
        """Build prompt based on user context."""
        hour = ctx.builtins.get("hour", 12)
        greeting = "Good evening" if hour > 17 else "Good morning"
        return f"You are a helpful assistant. Use a {greeting} tone."
```

### Tools

What your agent can actually *do*. Without tools, it's just a fancy text generator.

```python
from syrin import Agent, Model
from syrin.tool import tool

@tool
def search(query: str) -> str:
    """Search the web for information."""
    # Real implementation: call search API
    return f"Results for: {query}"

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    return str(eval(expression))

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    tools=[search, calculate],  # Agent can use these
)
```

## Cost Control

### Budget

This is where production gets serious. Set a budget or wake up to a surprise bill.

```python
from syrin import Agent, Model, Budget
from syrin.enums import ExceedPolicy, RateLimit

# Simple: $1 per request
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    budget=Budget(max_cost=1.00),
)

# Per-period limits: $5 per day
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    budget=Budget(
        max_cost=0.50,                      # $0.50 per request
        rate_limits=RateLimit(day=5.00),   # $5 per day
        exceed_policy=ExceedPolicy.STOP,         # Stop when exceeded
    ),
)
```

**What happens when budget is exceeded?**

| `on_exceeded` | Behavior |
|----------------|----------|
| `ExceedPolicy.STOP` | Raises `BudgetExceededError` |
| `ExceedPolicy.WARN` | Logs warning, continues |
| `ExceedPolicy.ERROR` | Logs error, continues |

**Budget thresholds for proactive alerts:**

```python
from syrin import Agent, Model, Budget, Hook

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    budget=Budget(
        max_cost=1.00,
        thresholds=[
            BudgetThreshold(at=50, action=lambda ctx: print("50% spent!")),
            BudgetThreshold(at=80, action=lambda ctx: print("80% spent!")),
        ],
    ),
)

# Or switch to a cheaper model
def switch_to_cheap(ctx):
    ctx.parent.switch_model(Model.OpenAI("gpt-4o-mini"))

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    budget=Budget(
        max_cost=1.00,
        thresholds=[
            BudgetThreshold(at=75, action=switch_to_cheap),
        ],
    ),
)
```

### Budget Persistence

Don't lose your budget state when the server restarts:

```python
from syrin import Agent, Model, Budget
from syrin.budget_store import FileBudgetStore

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    budget=Budget(max_cost=1.00),
    budget_store=FileBudgetStore("/tmp/budgets.json"),
    budget_store_key="user-123",  # Isolate per user
)
```

## Token Management

### Context

The agent's "working memory"—how much it can fit in a single request.

```python
from syrin import Agent, Model, Context
from syrin.threshold import ContextThreshold

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    config=AgentConfig(
        context=Context(
            max_tokens=80000,  # Context window
            reserve=2000,        # Room for response
            thresholds=[
                # Warn at 50%
                ContextThreshold(at=50, action=lambda ctx: print("50% tokens used")),
                # Compact at 75%
                ContextThreshold(at=75, action=lambda ctx: ctx.compact()),
            ],
        )
    ),
)
```

**Why this matters:** Long conversations grow unbounded. Without context management, you'll hit token limits or waste money sending the same history repeatedly.

### Proactive Compaction

Let Syrin handle context pressure automatically:

```python
from syrin import Agent, Model, Context

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    config=AgentConfig(
        context=Context(
            max_tokens=80000,
            auto_compact_at=0.6,  # Compact when 60% full
        )
    ),
)
```

## Safety and Compliance

### Guardrails

Validate input and output. Block harmful content before it reaches the model or your users.

```python
from syrin import Agent, Model
from syrin.guardrails import ContentFilter, Guardrail

# Built-in content filter
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    guardrails=[
        ContentFilter(
            blocked_words=["hack", "steal", "password"],
            action="block",
        ),
    ],
)

# Custom guardrail
def no_sensitive_data(text: str) -> GuardrailResult:
    """Block requests with sensitive data."""
    sensitive_patterns = ["ssn", "credit card", "password"]
    for pattern in sensitive_patterns:
        if pattern in text.lower():
            return GuardrailResult(
                passed=False,
                reason=f"Contains sensitive data: {pattern}",
            )
    return GuardrailResult(passed=True)

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    guardrails=[
        Guardrail(
            name="no_sensitive_data",
            description="Block sensitive information",
            validate=no_sensitive_data,
        ),
    ],
)
```

### Rate Limiting

Protect your API keys and enforce fair usage:

```python
from syrin import Agent, Model
from syrin.ratelimit import APIRateLimit

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    config=AgentConfig(
        rate_limit=APIRateLimit(
            requests_per_minute=60,
            tokens_per_minute=90000,
        ),
    ),
)
```

## Observability: See Everything

This is where Syrin shines. You can see exactly what's happening.

### Debug Mode

The fastest way to see your agent's internals:

```python
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    debug=True,  # Prints all events to console
)

response = agent.run("Hello")
```

**Output:**
```
[AGENT_RUN_START] input="Hello"
[LLM_REQUEST_START] iteration=1
[LLM_REQUEST_END] tokens=42, duration=0.32s
[AGENT_RUN_END] cost=$0.000142, iterations=1
```

### Hooks: Subscribe to Any Event

Every moment in the agent's lifecycle emits a hook. Subscribe to what you care about:

```python
from syrin import Agent, Model, Hook

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    budget=Budget(max_cost=1.00),
)

# Track cost
agent.events.on(Hook.LLM_REQUEST_END, lambda ctx: 
    print(f"Tokens: {ctx.get('total_tokens')}")
)

# Alert on budget threshold
agent.events.on(Hook.BUDGET_THRESHOLD, lambda ctx:
    send_alert(f"Budget at {ctx.get('percentage')}%")
)

# Log all tool calls
agent.events.on(Hook.TOOL_CALL_END, lambda ctx:
    log_tool(ctx.get('tool_name'), ctx.get('duration_ms'))
)

# Memory operations
agent.events.on(Hook.MEMORY_STORE, lambda ctx:
    audit_log(f"Memory stored: {ctx.get('memory_type')}")
)
```

**Available hooks by category:**

| Category | Hooks | When |
|----------|-------|------|
| **Agent** | `AGENT_RUN_START`, `AGENT_RUN_END` | Run begins/ends |
| **LLM** | `LLM_REQUEST_START`, `LLM_REQUEST_END` | Each LLM call |
| **Tools** | `TOOL_CALL_START`, `TOOL_CALL_END`, `TOOL_ERROR` | Tool execution |
| **Budget** | `BUDGET_THRESHOLD`, `BUDGET_EXCEEDED` | Budget events |
| **Memory** | `MEMORY_RECALL`, `MEMORY_STORE`, `MEMORY_FORGET` | Memory ops |
| **Context** | `CONTEXT_COMPACT`, `CONTEXT_THRESHOLD` | Context events |
| **Guardrails** | `GUARDRAIL_TRIGGERED`, `GUARDRAIL_PASSED` | Guardrail events |
| **Routing** | `ROUTING_DECISION` | Model selected |
| **Handoff** | `HANDOFF_START`, `HANDOFF_END`, `HANDOFF_BLOCKED` | Handoff events |
| **Spawn** | `SPAWN_START`, `SPAWN_END` | Child agents |
| **HITL** | `HITL_PENDING`, `HITL_APPROVED`, `HITL_REJECTED` | Human approval |

### Response Reports

After every call, get a complete breakdown:

```python
response = agent.run("Complex task")

# All reports in one place
print(f"Guardrails: {response.report.guardrail.passed}")
print(f"Tokens: {response.report.tokens.total_tokens}")
print(f"Cost: ${response.report.tokens.cost_usd:.6f}")
print(f"Memory ops: {response.report.memory.stores} stores, {response.report.memory.recalls} recalls")
print(f"Context: {response.report.context.compressions} compactions")
print(f"Rate limits: {response.report.ratelimits.checks} checks")
```

### Tracing: The Flight Recorder

Every step of execution is recorded:

```python
response = agent.run("Multi-step task")

for step in response.trace:
    print(f"Step: {step.step_type}")
    print(f"  Model: {step.model}")
    print(f"  Tokens: {step.tokens}")
    print(f"  Cost: ${step.cost_usd:.6f}")
    print(f"  Latency: {step.latency_ms}ms")
```

## Memory: Remember Everything

```python
from syrin import Agent, Model, Memory
from syrin.enums import MemoryType

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    memory=Memory(
        restrict_to=[MemoryType.CORE, MemoryType.EPISODIC],
        top_k=10,
    ),
)

# Remember something
agent.remember(
    "User prefers dark mode",
    memory_type=MemoryType.CORE,
    importance=0.9,
)

# Agent auto-recalls relevant memories before each request
response = agent.run("What are my preferences?")
```

## Checkpointing: Never Lose State

Save and restore agent state for long-running conversations or crash recovery:

```python
from syrin import Agent, Model
from syrin.checkpoint import CheckpointConfig

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    config=AgentConfig(
        checkpoint=CheckpointConfig(
            enabled=True,
            storage="sqlite",
            trigger=CheckpointTrigger.STEP,
            max_checkpoints=10,
        ),
    ),
)

# Auto-save on every step
response = agent.run("Continue the story...")

# Manual save
checkpoint_id = agent.save_checkpoint(reason="milestone")

# Restore later
agent.load_checkpoint(checkpoint_id)
```

## Complete Configuration Example

```python
from syrin import Agent, Model, Budget, Context
from syrin.tool import tool
from syrin.guardrails import ContentFilter
from syrin.memory import Memory
from syrin.enums import ExceedPolicy, MemoryType, LoopStrategy
from syrin.threshold import ContextThreshold

@tool
def search(query: str) -> str:
    """Search the web."""
    return f"Results for: {query}"

# Fully configured production agent
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    
    # Core
    system_prompt="You are a helpful research assistant.",
    tools=[search],
    
    # Cost control
    budget=Budget(
        max_cost=0.50,
        rate_limits=RateLimit(day=5.00),
        exceed_policy=ExceedPolicy.STOP,
    ),
    
    # Token management
    config=AgentConfig(
        context=Context(
            max_tokens=80000,
            auto_compact_at=0.6,
        ),
    ),
    
    # Safety
    guardrails=[
        ContentFilter(blocked_words=["hack", "steal"]),
    ],
    
    # Memory
    memory=Memory(restrict_to=[MemoryType.CORE, MemoryType.EPISODIC]),
    
    # Loop
    loop_strategy=LoopStrategy.REACT,
    max_tool_iterations=10,
    
    # Observability
    debug=True,
)

# Subscribe to events
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: 
    metrics.record("cost", ctx.get("cost", 0))
)
```

## Configuration Quick Reference

| Parameter | Purpose | Default |
|-----------|---------|---------|
| `model` | AI brain | Required |
| `system_prompt` | Instructions | "" |
| `tools` | Abilities | [] |
| `budget` | Cost limits | Unlimited |
| `memory` | Persistence | Disabled |
| `guardrails` | Safety | [] |
| `context` | Token management | 128k tokens |
| `loop_strategy` | Thinking style | REACT |
| `debug` | Console output | False |
| `checkpoint` | State persistence | Disabled |

## What's Next?

- [Loop Strategies](/agent-kit/agent/running-agents) - How the agent thinks
- [Budget Deep Dive](/agent-kit/core/budget) - Complete budget configuration
- [Memory](/agent-kit/core/memory) - Persistent memory
- [Hooks Reference](/agent-kit/debugging/hooks-reference) - All hooks documented

## See Also

- [Creating Agents](/agent-kit/agent/creating-agents) - How to build agents
- [Running Agents](/agent-kit/agent/running-agents) - How to execute them
- [Response Object](/agent-kit/agent/response-object) - What you get back
- [Guardrails](/agent-kit/agent/guardrails) - Safety configuration
