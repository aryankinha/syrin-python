# Agent Constructor Reference

Complete reference for every `Agent` constructor parameter.

## Signature

```python
Agent(
    model=None,                    # Required (or set on class)
    system_prompt=None,
    tools=None,
    budget=None,
    *,
    output=None,
    max_tool_iterations=10,
    budget_store=None,
    budget_store_key="default",
    memory=None,
    loop_strategy=LoopStrategy.REACT,
    loop=None,
    guardrails=None,
    context=None,
    rate_limit=None,
    checkpoint=None,
    debug=False,
    tracer=None,
)
```

Parameters marked `None` use class-level defaults when available. Use `_UNSET` internally; users omit them or pass `None`.

---

## Positional Parameters

### `model` — **Required**

LLM used by the agent.

**Type:** `Model | ModelConfig | None`  
**Default:** From class `model` if not provided

```python
from syrin.model import Model

agent = Agent(model=Model.OpenAI("gpt-4o-mini"))
agent = Agent(model=Model.Anthropic("claude-sonnet-4-5"))
agent = Agent(model=Model.Ollama("llama3"))
```

Must be provided on the class or at construction. Raises `TypeError` if missing.

---

### `system_prompt`

Instructions that define the agent’s behavior. Sent with every request.

**Type:** `str | None`  
**Default:** `""` or class `system_prompt`

```python
agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant. Be concise.",
)
```

---

### `tools`

Functions the agent can call during execution.

**Type:** `list[ToolSpec] | None`  
**Default:** `[]` or class `tools` (merged on inheritance)

```python
from syrin.tool import tool

@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results: {query}"

agent = Agent(model=model, tools=[search])
```

Tools are built from `@tool`-decorated functions or equivalent specs.

---

### `budget`

Cost limits and behavior when limits are exceeded.

**Type:** `Budget | None`  
**Default:** `None` or class `budget`

```python
from syrin import Budget, stop_on_exceeded

agent = Agent(
    model=model,
    budget=Budget(run=1.0, on_exceeded=stop_on_exceeded),
)
```

See [Budget](budget.md) for full options.

---

## Keyword-Only Parameters

### `output`

Structured output configuration (Pydantic model, retries, validator).

**Type:** `Output | None`  
**Default:** `None`

```python
from pydantic import BaseModel
from syrin.output import Output

class Answer(BaseModel):
    text: str
    confidence: float

agent = Agent(
    model=model,
    output=Output(
        type=Answer,
        validation_retries=3,
        context={"allowed_domains": ["example.com"]},
    ),
)
```

See [Structured Output](structured-output.md).

---

### `max_tool_iterations`

Maximum tool-call loop iterations.

**Type:** `int`  
**Default:** `10`

```python
agent = Agent(model=model, max_tool_iterations=5)
```

Prevents unbounded tool loops.

---

### `budget_store`

Where budget state is persisted.

**Type:** `BudgetStore | None`  
**Default:** `None`

```python
from syrin.budget_store import FileBudgetStore

agent = Agent(
    model=model,
    budget=Budget(run=1.0),
    budget_store=FileBudgetStore("/tmp/budget.json"),
    budget_store_key="user_123",
)
```

Use with `budget` for persistent tracking.

---

### `budget_store_key`

Key used to load/save budget in `budget_store`.

**Type:** `str`  
**Default:** `"default"`

---

### `memory`

Memory configuration: persistent config or conversation memory instance.

**Type:** `ConversationMemory | MemoryConfig | None`  
**Default:** Persistent memory with `MemoryConfig(types=[CORE, EPISODIC], top_k=10)`

```python
from syrin.memory.config import Memory as MemoryConfig
from syrin.enums import MemoryType

# Persistent memory
agent = Agent(
    model=model,
    memory=MemoryConfig(
        types=[MemoryType.CORE, MemoryType.EPISODIC],
        top_k=10,
        auto_store=True,
    ),
)

# Or pass None to disable
agent = Agent(model=model, memory=None)  # Uses default MemoryConfig
```

See [Memory](memory.md).

---

### `loop_strategy`

Which loop strategy to use when `loop` is not provided.

**Type:** `LoopStrategy`  
**Default:** `LoopStrategy.REACT`

**Values:**

- `LoopStrategy.REACT` — Think → Act → Observe
- `LoopStrategy.SINGLE_SHOT` — One LLM call, no tool loop
- `LoopStrategy.PLAN_EXECUTE` — Plan steps, then execute
- `LoopStrategy.CODE_ACTION` — Generate and run code

```python
from syrin.enums import LoopStrategy

agent = Agent(model=model, loop_strategy=LoopStrategy.SINGLE_SHOT)
```

Only used when `loop` is `None`.

---

### `loop`

Custom loop instance or class. Overrides `loop_strategy` when provided.

**Type:** `Loop | type[Loop] | None`  
**Default:** `None` (use `loop_strategy`)

```python
from syrin.loop import ReactLoop, HumanInTheLoop

agent = Agent(model=model, loop=ReactLoop(max_iterations=5))

async def approve(name, args):
    return True

agent = Agent(model=model, loop=HumanInTheLoop(approve=approve))
```

See [Loop Strategies](loop-strategies.md).

---

### `guardrails`

Input/output guardrails.

**Type:** `list[Guardrail] | GuardrailChain | None`  
**Default:** `[]` or class `guardrails` (merged on inheritance)

```python
from syrin.guardrails import BlockedWordsGuardrail

agent = Agent(
    model=model,
    guardrails=[BlockedWordsGuardrail(["spam", "offensive"])],
)
```

See [Guardrails](guardrails.md).

---

### `context`

Context manager for message preparation and compression.

**Type:** `Context | DefaultContextManager | None`  
**Default:** `DefaultContextManager(Context())`

```python
from syrin.context import Context

agent = Agent(model=model, context=Context())
```

---

### `rate_limit`

API rate limit configuration.

**Type:** `APIRateLimit | RateLimitManager | None`  
**Default:** `None`

```python
from syrin.ratelimit import APIRateLimit

agent = Agent(
    model=model,
    rate_limit=APIRateLimit(
        requests_per_minute=60,
        tokens_per_minute=90000,
    ),
)
```

See [Rate Limiting](rate-limiting.md).

---

### `checkpoint`

Checkpoint configuration for saving/loading state.

**Type:** `CheckpointConfig | Checkpointer | None`  
**Default:** `None`

```python
from syrin.checkpoint import CheckpointConfig

agent = Agent(
    model=model,
    checkpoint=CheckpointConfig(
        enabled=True,
        storage="sqlite",
        path="/tmp/checkpoints.db",
        trigger=CheckpointTrigger.STEP,
        max_checkpoints=10,
    ),
)
```

See [Checkpointing](checkpointing.md).

---

### `debug`

Enable debug logging (prints events to console).

**Type:** `bool`  
**Default:** `False`

```python
agent = Agent(model=model, debug=True)
```

---

### `tracer`

Custom tracer for observability. If `None`, uses the default tracer.

**Type:** `Any`  
**Default:** `None`

```python
from syrin.observability import get_tracer

agent = Agent(model=model, tracer=get_tracer())
```

---

## Complete Example

```python
from syrin import Agent, Budget, Hook
from syrin.model import Model
from syrin.tool import tool
from syrin.checkpoint import CheckpointConfig
from syrin.enums import CheckpointTrigger, LoopStrategy, MemoryType
from syrin.memory.config import Memory as MemoryConfig

@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results: {query}"

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini"),
    system_prompt="You are a research assistant.",
    tools=[search],
    budget=Budget(run=0.50),
    max_tool_iterations=10,
    memory=MemoryConfig(
        types=[MemoryType.CORE, MemoryType.EPISODIC],
        top_k=10,
    ),
    loop_strategy=LoopStrategy.REACT,
    guardrails=[],
    checkpoint=CheckpointConfig(
        enabled=True,
        trigger=CheckpointTrigger.STEP,
        max_checkpoints=5,
    ),
    debug=False,
)

response = agent.response("What is quantum computing?")
```
