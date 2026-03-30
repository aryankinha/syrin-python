---
title: Agent Anatomy
description: Understanding every component that makes up a Syrin agent
weight: 61
---

## Dissecting Your Agent

Building an agent is like assembling a team. Each component has a specific job. Understanding what each does helps you know exactly where to look when something goes wrong—or right.

## The Complete Picture

An agent consists of these components:

**Model** — The brain that thinks for you. `Model.OpenAI("gpt-4o")`

**System Prompt** — Your agent's instruction manual. "You are a helpful assistant..."

**Tools** — What your agent can actually do. `@tool search()`, `@tool calculate()`

**Memory** — What your agent remembers. `remember()`, `recall()`, `forget()`

**Context** — The workspace. `max_tokens`, compaction, thresholds

**Budget** — The wallet. `max_cost=1.00`, `rate_limits=RateLimit(day=50)`

**Guardrails** — Safety nets. Input validation, output filtering

**Loop** — The thinking strategy. `REACT`, `SINGLE_SHOT`, `HUMAN_IN_THE_LOOP`

**Events** — The observer. Hooks on every lifecycle moment

Let's crack open each component.

## Model: The Brain

The model is **required**. It's the AI that generates responses.

```python
from syrin import Agent, Model

# OpenAI
agent = Agent(model=Model.OpenAI("gpt-4o", api_key="your-key"))

# Anthropic
agent = Agent(model=Model.Anthropic("claude-3-5-sonnet", api_key="your-key"))

# Ollama (local)
agent = Agent(model=Model.Ollama("llama3"))

# Multiple models for routing
agent = Agent(model=[
    Model.OpenAI("gpt-4o-mini"),  # Fast, cheap
    Model.OpenAI("gpt-4o"),        # Slow, expensive
])
```

**What you control:** Model choice, API key, temperature, max tokens, and more via `Model(... settings=ModelSettings(...))`.

## System Prompt: The Instruction Manual

The system prompt tells the agent *how* to behave. It's sent with every request.

```python
from syrin import Agent, Model
from syrin.prompt import prompt, PromptContext

# Static prompt (simple, but limited)
class Assistant(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = "You are a helpful assistant. Be concise."

# Dynamic prompt with @system_prompt (recommended)
class PersonalizedAssistant(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    
    @system_prompt
    def personality(self, ctx: PromptContext) -> str:
        """Build prompt dynamically based on context."""
        user_name = ctx.template_variables.get("user_name", "friend")
        return f"""
            You are a helpful assistant for {user_name}.
            - Be friendly but professional
            - Ask clarifying questions when needed
            - User's preferences: {ctx.template_variables.get('preferences', 'none')}
        """

# Use with template variables
agent = PersonalizedAssistant()
response = agent.run(
    "Help me plan my day",
    template_variables={"user_name": "Alice", "preferences": "Prefers morning tasks"}
)
```

**What you control:** Static text, dynamic generation, variable injection, built-in variables (`{date}`, `{agent_id}`, `{conversation_id}`).

## Tools: The Abilities

Tools let the agent *do* things—search the web, run calculations, call APIs.

```python
from syrin import Agent, Model
from syrin.tool import tool

@tool
def search(query: str) -> str:
    """Search the web for information."""
    # Real implementation would call a search API
    return f"Results for: {query}"

@tool  
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    return str(eval(expression))

class ResearchAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = "You are a research assistant. Use tools when needed."
    tools = [search, calculate]

agent = ResearchAgent()
response = agent.run("What is 15 * 23?")
# Agent calls calculate tool internally
```

**What you control:** Tool definitions, parameters, descriptions, execution.

## Memory: The Recall System

Memory lets agents remember facts across sessions. Think of it as long-term storage.

```python
from syrin import Agent, Model
from syrin.memory import Memory, MemoryPreset, MemoryType

class RememberingAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    memory = MemoryPreset.STANDARD  # Core + Episodic memory

agent = RememberingAgent()

# Remember something
agent.remember(
    "User prefers dark mode",
    memory_type=MemoryType.CORE,  # Identity facts
    importance=0.9
)

# Later: agent automatically recalls relevant memories
response = agent.run("What are my preferences?")
# Agent recalls "User prefers dark mode" and incorporates it
```

**Memory types:**
| Type | What it stores | Example |
|------|----------------|---------|
| CORE | Identity, preferences | "User is named Alice" |
| EPISODIC | Events, conversations | "Yesterday we discussed X" |
| SEMANTIC | Learned facts | "Python uses indentation" |
| PROCEDURAL | How to do things | "Format dates as YYYY-MM-DD" |

**What you control:** Memory types, storage backend, recall relevance, importance decay.

## Context: The Workspace

Context manages token limits. It's the agent's "working memory"—how much it can fit in a single request.

```python
from syrin import Agent, Model, Context
from syrin.threshold import ContextThreshold

class LongRunningAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    context = Context(
        max_tokens=80000,  # 80k context window
        thresholds=[
            # Compact at 75% utilization
            ContextThreshold(at=75, action=lambda ctx: ctx.compact()),
        ]
    )

agent = LongRunningAgent()

# Agent handles long conversations automatically
for i in range(100):
    response = agent.run(f"Turn {i}: Let's discuss {topic}")
    # Context compacts when needed
```

**What you control:** Max tokens, reserve for response, thresholds with actions, compaction strategies.

## Budget: The Wallet

Budget controls spending. It's how you prevent surprise bills.

```python
from syrin import Agent, Model, Budget
from syrin.enums import ExceedPolicy, RateLimit

class CautiousAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    budget = Budget(
        max_cost=0.50,  # Max $0.50 per request
        rate_limits=RateLimit(day=5.00),  # Max $5.00 per day
        exceed_policy=ExceedPolicy.STOP  # Stop when exceeded
    )

agent = CautiousAgent()

try:
    response = agent.run("Do something expensive...")
except BudgetExceededError:
    print("Budget limit reached!")
```

**What you control:** Per-run limits, per-period limits (hour/day/week/month), threshold actions (warn, stop, switch model).

## Guardrails: The Safety Nets

Guardrails validate input and output. They prevent harmful content and enforce policies.

```python
from syrin import Agent, Model
from syrin.guardrails import Guardrail, GuardrailResult

class SafeAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    guardrails = [
        # Block harmful content
        Guardrail(
            name="no_harmful_content",
            description="Block harmful or illegal requests",
            validate=lambda text: "blocked" not in text.lower()
        ),
    ]

agent = SafeAgent()
result = agent.run("Tell me something blocked")
# Guardrail intercepts if needed
```

**What you control:** Input validation, output filtering, PII detection, custom logic.

## Loop: The Thinking Strategy

The loop determines how the agent approaches problems.

```python
from syrin import Agent, Model
from syrin.enums import LoopStrategy

# REACT (default): Think → Act → Observe → loop
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    loop_strategy=LoopStrategy.REACT,  # Tool use enabled
)

# SINGLE_SHOT: One response, no tools
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    loop_strategy=LoopStrategy.SINGLE_SHOT,  # Just one call
)

# HUMAN_IN_THE_LOOP: Approve each tool call
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    loop_strategy=LoopStrategy.HUMAN_IN_THE_LOOP,
)
```

## Events: The Observer

Events give you visibility into what happens during a run.

```python
from syrin import Agent, Model, Hook

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    debug=True,  # Print all events to console
)

# Or subscribe to specific events
agent.events.on(Hook.LLM_REQUEST_END, lambda ctx: print(f"Tokens: {ctx.get('total_tokens')}"))
agent.events.on(Hook.TOOL_CALL_END, lambda ctx: print(f"Tool: {ctx.get('tool_name')}"))
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: print(f"Cost: ${ctx.get('cost', 0):.4f}"))

response = agent.run("Hello!")
```

## Putting It All Together

Here's an agent using everything:

```python
from syrin import Agent, Model, Budget, Context, Hook
from syrin.tool import tool
from syrin.memory import Memory, MemoryPreset
from syrin.enums import ExceedPolicy, LoopStrategy, MemoryType

@tool
def search(query: str) -> str:
    """Search the web."""
    return f"Results for: {query}"

class FullFeaturedAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    
    system_prompt = """
        You are a helpful research assistant.
        Use tools when you need current information.
        Remember user preferences from memory.
    """
    
    tools = [search]
    
    memory = MemoryPreset.STANDARD
    
    budget = Budget(max_cost=1.00, exceed_policy=ExceedPolicy.WARN)
    
    context = Context(max_tokens=80000)
    
    loop_strategy = LoopStrategy.REACT

agent = FullFeaturedAgent()

# Subscribe to events
agent.events.on(Hook.AGENT_RUN_END, lambda ctx: print(f"Run complete!"))

# Remember user preferences
agent.remember("User prefers concise answers", memory_type=MemoryType.CORE)

# Use the agent
response = agent.run("Research quantum computing")
print(f"Content: {response.content[:100]}...")
print(f"Cost: ${response.cost:.4f}")
print(f"Spent: ${agent.budget_state.spent:.4f}")
```

## Component Comparison

| Component | Purpose | Required? | Default |
|-----------|---------|----------|---------|
| Model | AI brain | Yes | None |
| System Prompt | Instructions | No | Empty string |
| Tools | Abilities | No | None |
| Memory | Long-term storage | No | Disabled |
| Context | Token limits | No | 128k tokens |
| Budget | Cost control | No | Unlimited |
| Guardrails | Safety | No | None |
| Loop | Thinking strategy | No | REACT |
| Events | Observability | No | Silent |

## What's Next?

- [Creating Agents](/agent-kit/agent/creating-agents) - Build your first agent
- [Builder Pattern](/agent-kit/agent/builder-pattern) - Fluent agent construction
- [Tools](/agent-kit/agent/tools) - Deep dive into tool creation
- [Memory](/agent-kit/core/memory) - Persistent memory details

## See Also

- [Models](/agent-kit/core/models) - Model configuration
- [Budget](/agent-kit/core/budget) - Cost control
- [Context](/agent-kit/core/context) - Token management
- [Prompts](/agent-kit/core/prompts) - Effective system prompts
