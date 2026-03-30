---
title: Introduction
description: Learn why Syrin is the AI agent framework built for developers who demand control
weight: 1
---

## Finally, an AI Agent Library That Doesn't Get in Your Way

You've tried other frameworks. You know how this goes.

The library promises simplicity. You hit walls. Need custom budget limits? Hope there's a plugin. Need memory that actually works? Dig through five layers of docs. Want to understand why your agent did something? Good luck.

Syrin was built by developers who got tired of fighting their tools.

## What We Heard

After building AI systems in production, three things kept coming up:

1. **Libraries abstract too much** — When something breaks, you can't find why
2. **Cost control is an afterthought** — Budget overruns kill deployments
3. **Observability is missing** — You ship blind and debug blind

Syrin addresses all three. Not with magic—but with control.

## What Makes Syrin Different

**No hidden rewrites.** Every LLM call is yours to see and trace. No framework "help" that changes your prompts.

**First-class budget control.** Set limits per run, per day, per user. Not as an add-on—as a core feature.

**Four memory types.** Core, episodic, semantic, procedural. Memory that thinks the way you do.

**70+ hooks for observability.** See everything. Ship to any platform. Debug at 2 AM.

**Built-in guardrails.** PII detection, content filtering, fact verification. Not an enterprise upsell.

**40% fewer tokens on tools.** TOON schemas actually save you money.

**Checkpointing.** Long-running tasks survive server restarts. Your agent picks up where it left off.

## See the Difference

```python
from syrin import Agent, Budget, Memory, Model, RateLimit
from syrin.enums import MemoryType

class SupportAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = "You are a technical support specialist."
    budget = Budget(max_cost=0.50, rate_limits=RateLimit(day=5.00))
    memory = Memory(restrict_to=[MemoryType.CORE, MemoryType.EPISODIC])

agent = SupportAgent()
agent.remember("User prefers email", memory_type=MemoryType.CORE)
response = agent.run("How do I reset my password?")
```

That's your agent. Your model. Your budget. Your memory.

## The Public Import Surface

Syrin is designed so the package root is the front door for most application code:

```python
from syrin import Agent, Budget, Memory, Model, Output, Response, task, tool
```

That import style is intentional. The package `__init__.py` files show the stable, user-facing API for each module, while the implementation stays in internal modules that can evolve without forcing import rewrites in your app.

Use subpackages when you want a narrower import surface or lower-level APIs:

- `syrin.agent` for the core `Agent` type
- `syrin.prompt` for prompt decorators and prompt metadata
- `syrin.response` for response/report models
- `syrin.debug` for Pry and trace replay
- `syrin.watch` for cron, webhook, and queue-driven triggers

## Quick Comparison

| | LangChain | CrewAI | **Syrin** |
|-|-----------|--------|-----------|
| Budget enforcement | Partial | No | **Yes** |
| Memory types | 1 | 1 | **4** |
| Lifecycle hooks | ~10 | ~5 | **70+** |
| Checkpointing | No | No | **Yes** |
| Built-in guardrails | No | No | **Yes** |

Numbers based on public documentation (March 2026).

## Get Started

```bash
pip install syrin
```

```python
from syrin import Agent, Model

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = "You are helpful."

agent = MyAgent()
print(agent.run("Hello!").content)
```

Serve it with a web interface:

```python
agent.serve(port=8000, enable_playground=True)
```

## What's Next?

- [Installation](/agent-kit/getting-started/installation) — Set up in 60 seconds
- [Quick Start](/agent-kit/getting-started/quick-start) — Build your first agent in 5 minutes
- [Agent Overview](/agent-kit/agent/overview) — How agents work

## See Also

- [Budget](/agent-kit/core/budget) — Cost control that works
- [Memory](/agent-kit/core/memory) — Four memory types
- [Hooks](/agent-kit/debugging/hooks) — Full observability
