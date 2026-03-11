# Agent Constructor Reference

Complete reference for every `Agent` constructor parameter.

## Signature

```python
Agent(
    model=None,                    # Required (or set on class); Model or list[Model] for routing
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
    model_router=None,            # When model is list; RoutingConfig for routing
    checkpoint=None,
    debug=False,
    tracer=None,
)
```

Parameters marked `None` use class-level defaults when available. Use `_UNSET` internally; users omit them or pass `None`.

---

## Positional Parameters

### `model` — **Required**

LLM(s) used by the agent. Single model or list for routing.

**Type:** `Model | ModelConfig | list[Model | ModelConfig] | None`  
**Default:** From class `model` if not provided

```python
from syrin.model import Model

agent = Agent(
    # model=Model.OpenAI("gpt-4o-mini"),
    model=Model.Almock(),  # No API key needed
)
# Or: Model.Anthropic("claude-sonnet-4-5"), Model.Ollama("llama3"), etc.

# Multiple models + model_router for per-request routing
agent = Agent(
    model=[Model.Anthropic(...), Model.OpenAI(...)],
    model_router=RoutingConfig(routing_mode=RoutingMode.AUTO),
)
```

Must be provided on the class or at construction. Raises `TypeError` if missing. When `model` is a list, use `model_router` to enable routing. See [Routing](../routing.md).

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

### `output_config`

Output configuration: format (TEXT, MARKDOWN, HTML, PDF, DOCX), optional template for slot-based generation, optional citation styling, and title. When `template` is set, requires `output=Output(SomeModel)`. File generation produces `response.file` and `response.file_bytes`. When `citation` is set, citations are parsed from content and `response.citations` is populated.

**Type:** `OutputFormat | OutputConfig | None`  
**Default:** `None`

```python
from syrin import CitationConfig, CitationStyle, OutputConfig, OutputFormat, Template, SlotConfig

# Bare format (file generation)
agent = Agent(model=model, output_config=OutputFormat.TEXT)

# With template (requires output=)
tpl = Template("cap", "Amount: {{amount}}", slots={"amount": SlotConfig("str")})
agent = Agent(
    model=model,
    output=Output(CapitalData),
    output_config=OutputConfig(format=OutputFormat.MARKDOWN, template=tpl),
)

# With citations (financial, legal, medical)
agent = Agent(
    model=model,
    output_config=OutputConfig(
        format=OutputFormat.PDF,
        citation=CitationConfig(style=CitationStyle.FOOTNOTE, include_page=True),
    ),
)
```

See [Template Engine](../template-engine.md).

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

**Type:** `ConversationMemory | Memory | None`  
**Default:** Persistent memory with `Memory(types=[CORE, EPISODIC], top_k=10)`

```python
from syrin.memory.config import Memory as Memory
from syrin.enums import MemoryType

# Persistent memory
agent = Agent(
    model=model,
    memory=Memory(
        types=[MemoryType.CORE, MemoryType.EPISODIC],
        top_k=10,
        auto_store=True,
    ),
)

# Or pass None to disable
agent = Agent(model=model, memory=None)  # Uses default Memory
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
from syrin.guardrails import ContentFilter

agent = Agent(
    model=model,
    guardrails=[ContentFilter(blocked_words=["spam", "offensive"])],
)
```

See [Guardrails](guardrails.md).

---

### `context`

Context manager for message preparation and compression. Pass via `AgentConfig`.

**Type:** `Context | ContextConfig | DefaultContextManager | None`  
**Default:** `DefaultContextManager(Context())`

Use **ContextConfig** when you only need the main knobs (max_tokens, reserve, thresholds, token_limits, auto_compact_at); it builds a full `Context` internally.

```python
from syrin import Agent, AgentConfig
from syrin.context import Context, ContextConfig

# Full Context (all options)
agent = Agent(model=model, config=AgentConfig(context=Context(max_tokens=8000)))

# ContextConfig (3–5 knobs for 90% of cases)
agent = Agent(model=model, config=AgentConfig(context=ContextConfig(max_tokens=8000, auto_compact_at=0.6)))
```

---

### `rate_limit`

API rate limit configuration. Pass via `AgentConfig`.

**Type:** `APIRateLimit | RateLimitManager | None`  
**Default:** `None`

```python
from syrin import AgentConfig
from syrin.ratelimit import APIRateLimit

agent = Agent(
    model=model,
    config=AgentConfig(
        rate_limit=APIRateLimit(
            requests_per_minute=60,
            tokens_per_minute=90000,
        ),
    ),
)
```

See [Rate Limiting](rate-limiting.md).

---

### `model_router`

Routing configuration when `model` is a list. Enables per-request model selection by task, cost, and modality.

**Type:** `RoutingConfig | None`  
**Default:** `None`

```python
from syrin.router import RoutingConfig, RoutingMode

agent = Agent(
    model=[claude, gpt],
    model_router=RoutingConfig(
        routing_mode=RoutingMode.AUTO,
        budget_optimisation=True,
    ),
)
```

Options: `routing_mode`, `force_model`, `classifier`, `routing_rule_callback`, budget thresholds. See [Routing](../routing.md) and [Agent: Model](model.md#model-list--routing).

---

### `checkpoint`

Checkpoint configuration for saving/loading state. Pass via `AgentConfig`.

**Type:** `CheckpointConfig | Checkpointer | None`  
**Default:** `None`

```python
from syrin import AgentConfig
from syrin.checkpoint import CheckpointConfig

agent = Agent(
    model=model,
    config=AgentConfig(
        checkpoint=CheckpointConfig(
        enabled=True,
        storage="sqlite",
        path="/tmp/checkpoints.db",
            trigger=CheckpointTrigger.STEP,
            max_checkpoints=10,
        ),
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

Custom tracer for observability. Pass via `AgentConfig`. If `None`, uses the default tracer.

**Type:** `Tracer | None`  
**Default:** `None`

```python
from syrin import AgentConfig
from syrin.observability import get_tracer

agent = Agent(model=model, config=AgentConfig(tracer=get_tracer()))
```

---

## Complete Example

```python
from syrin import Agent, Budget, Hook
from syrin.model import Model
from syrin.tool import tool
from syrin.checkpoint import CheckpointConfig
from syrin.enums import CheckpointTrigger, LoopStrategy, MemoryType
from syrin.memory.config import Memory as Memory

@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results: {query}"

agent = Agent(
    # model=Model.OpenAI("gpt-4o-mini"),
    model=Model.Almock(),  # No API Key needed
    system_prompt="You are a research assistant.",
    tools=[search],
    budget=Budget(run=0.50),
    max_tool_iterations=10,
    memory=Memory(
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
