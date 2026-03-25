<p align="center">
  <img src="https://raw.githubusercontent.com/Syrin-Labs/cli/main/assets/syrin-logo-dark-bg.png" alt="Syrin" width="200">
</p>

<h1 align="center">Syrin</h1>

<p align="center">
  <b>Agents that ship. Not surprise you with bills.</b>
</p>
<p align="center">
  <i>Python library for AI agents with budget control, memory, and observability built-in.</i>
</p>

<p align="center">
  <a href="https://pypi.org/project/syrin/"><img src="https://img.shields.io/pypi/v/syrin.svg" alt="PyPI"></a>
  <a href="https://github.com/syrin-labs/syrin-python/blob/main/LICENSE"><img src="https://img.shields.io/github/license/syrin-labs/syrin-python.svg" alt="License"></a>
  <a href="https://pypi.org/project/syrin/"><img src="https://img.shields.io/pypi/pyversions/syrin.svg" alt="Python"></a>
  <a href="https://github.com/syrin-labs/syrin-python/stargazers"><img src="https://img.shields.io/github/stars/syrin-labs/syrin-python.svg?style=social" alt="Stars"></a>
</p>

<p align="center">
  <a href="https://syrin.ai">Website</a> ·
  <a href="docs/getting-started/quick-start.md">Docs</a> ·
  <a href="https://discord.gg/p4jnKxYKpB">Discord</a> ·
  <a href="https://x.com/syrin_dev">Twitter</a>
</p>

---

## The Problem: "Why Did My AI Agent Cost $10,000 Last Month?"

You built an AI agent. It worked perfectly in testing. Then came the bill — a surprise invoice for thousands of dollars with **zero warning**.

This is the #1 reason AI agents never make it to production. Not because they don't work — because they're financially reckless.

> *"I had no idea when my agent hit the budget."*
> *"My logs don't show where tokens went."*
> *"I spent 3 weeks building memory from scratch."*
> *"My agent crashed after 2 hours — no way to resume."*

**Syrin solves this.** One library. Zero surprises. Production-ready from day one.

---

## Installation

```bash
pip install syrin

# With Anthropic support
pip install syrin[anthropic]

# With voice capabilities
pip install syrin[voice]
```

---

## 60-Second Quickstart

```python
from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy

class Assistant(Agent):
    model = Model.Almock()  # No API key needed for testing
    budget = Budget(max_cost=0.50, exceed_policy=ExceedPolicy.STOP)

result = Assistant().run("Explain quantum computing simply")
print(result.content)
print(f"Cost: ${result.cost:.6f}  |  Remaining: ${result.budget_remaining}")
```

Switch to a real model by replacing one line:

```python
model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
# or
model = Model.Anthropic("claude-sonnet-4-5", api_key="your-key")
```

---

## What Syrin Solves

### 1. Budget & Cost Control

No more surprise bills. Set a cap, pick a policy — done.

```python
from syrin import Agent, Budget, Model, raise_on_exceeded, warn_on_exceeded
from syrin.enums import ExceedPolicy
from syrin.threshold import BudgetThreshold

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="..."),
    budget=Budget(
        max_cost=1.00,         # Hard cap per run
        reserve=0.10,          # Hold back $0.10 for the reply
        exceed_policy=ExceedPolicy.STOP,  # STOP | WARN | IGNORE | SWITCH

        # Alert at 80% before you hit the wall
        thresholds=[
            BudgetThreshold(at=80, action=lambda ctx: alert_ops(ctx.percentage)),
        ],
    ),
)

result = agent.run("Process this report")
print(f"Estimated (pre-call): ${result.cost_estimated:.6f}")
print(f"Actual    (post-call): ${result.cost:.6f}")
print(f"Cache savings:         ${result.cache_savings:.6f}")
```

**How it works:**
- **Pre-call check:** estimates cost before sending to the LLM — fails fast if it would exceed
- **Post-call recording:** records actual tokens from the provider
- **Thresholds:** fire callbacks at any percentage of budget consumed
- **ExceedPolicy:** `STOP` raises, `WARN` logs, `IGNORE` continues silently

**Rate limits across time windows:**

```python
from syrin import RateLimit

budget = Budget(
    max_cost=0.10,           # $0.10 per run
    rate_limits=RateLimit(
        hour=5.00,           # $5/hour
        day=50.00,           # $50/day
        month=500.00,        # $500/month
    ),
)
```

**Shared budget across parallel agents:**

```python
shared = Budget(max_cost=10.00, shared=True)
orchestrator = Agent(model=model, budget=shared)
# All spawned children deduct from the same $10 pool — thread-safe
```

**Dashboard:**

```python
summary = agent.budget_summary()
# → run_cost, run_tokens, hourly/daily totals, remaining, percent_used

costs = agent.export_costs(format="json")
# → [{cost_usd, total_tokens, model, timestamp}, ...]
```

---

### 2. Memory That Persists

Agents that remember users, facts, and skills across sessions.

```python
from syrin import Agent, Model
from syrin.enums import MemoryType

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="..."))

# Store facts (persisted across sessions)
agent.remember("User prefers TypeScript", memory_type=MemoryType.CORE)
agent.remember("Last session: discussed API design", memory_type=MemoryType.EPISODIC)

# Recall relevant memories (semantic search)
memories = agent.recall("user preferences", limit=5)

# Forget when needed
agent.forget("outdated fact")
```

**4 memory types:**

| Type | Use For |
|------|---------|
| `CORE` | Long-term facts — user profile, preferences |
| `EPISODIC` | Conversation history and past events |
| `SEMANTIC` | Knowledge with embeddings (RAG) |
| `PROCEDURAL` | Skills, instructions, how-to knowledge |

**Backends:** SQLite (default, zero config), Qdrant (vector search), Redis (cache), PostgreSQL (production).

---

### 3. Observability Built-In

See everything that happens inside your agent.

```python
from syrin import Agent, Model
from syrin.enums import Hook

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="..."), debug=True)

# Subscribe to lifecycle events
def log_cost(ctx):
    print(f"Run complete. Cost: ${ctx.cost:.6f}  Tokens: {ctx.tokens}")

def on_budget_warning(ctx):
    print(f"Budget at {ctx.percentage}% — ${ctx.current_value:.4f} spent")

agent.events.on(Hook.AGENT_RUN_END, log_cost)
agent.events.on(Hook.BUDGET_THRESHOLD, on_budget_warning)
agent.events.on(Hook.TOOL_CALL_END, lambda ctx: print(f"Tool: {ctx.name}"))

result = agent.run("Research quantum computing")
```

**CLI tracing — no code changes needed:**

```bash
python my_agent.py --trace
```

**72+ hook events** covering every lifecycle moment: LLM requests, tool calls, budget events, memory operations, handoffs, checkpoints, circuit breaker trips.

---

### 4. Multi-Agent Orchestration

```python
from syrin import Agent, Budget, Model

class Researcher(Agent):
    model = Model.OpenAI("gpt-4o", api_key="...")
    system_prompt = "You research topics thoroughly."

class Writer(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="...")
    system_prompt = "You write clear, concise reports."

# Handoff: researcher passes context to writer
researcher = Researcher()
result = researcher.handoff(Writer, "Write a report from the research")

# Spawn: orchestrator creates sub-agents
orchestrator = Agent(model=model, budget=Budget(max_cost=5.00, shared=True))
orchestrator.spawn(Researcher, task="Research AI trends")
orchestrator.spawn(Writer, task="Summarize findings")

# Parallel: multiple agents at once
results = orchestrator.spawn_parallel([
    (Researcher, {"task": "Topic A"}),
    (Researcher, {"task": "Topic B"}),
])

# DynamicPipeline: LLM decides which agents to use
from syrin import DynamicPipeline
pipeline = DynamicPipeline(agents=[Researcher, Writer], model=model)
result = pipeline.run("Research AI trends and write a summary")
print(f"{result.content}  |  Cost: ${result.cost:.4f}")
```

---

### 5. Guardrails & Safety

```python
from syrin import Agent, Model
from syrin.guardrails.built_in.pii import PIIScanner
from syrin.guardrails.built_in.length import LengthGuardrail

class SafeAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="...")
    guardrails = [
        LengthGuardrail(max_length=4000),
        PIIScanner(redact=True),   # Automatically redact PII
    ]

result = SafeAgent().run("Process: call me at 555-123-4567")
print(result.report.guardrail.passed)    # False (PII found)
print(result.content)                    # "call me at ***-***-****" (redacted)
```

---

### 6. State Persistence & Checkpoints

```python
from syrin import Agent, Model
from syrin.checkpoint import CheckpointConfig

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="..."),
    checkpoint_config=CheckpointConfig(dir="/tmp/checkpoints", auto_save=True),
)

result = agent.run("Start a long analysis...")
checkpoint_id = agent.save_checkpoint("mid-analysis")

# Resume later, even after a crash
agent.load_checkpoint(checkpoint_id)
result = agent.run("Continue the analysis")
```

---

### 7. One-Line Serving

```python
agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="..."))
agent.serve(port=8000, enable_playground=True)
# → POST /chat  POST /stream  GET /playground
```

---

### 8. Custom Budget Store (Bring Your Own Backend)

```python
from syrin.budget_store import BudgetStore, BudgetTracker

class PostgresBudgetStore(BudgetStore):
    def load(self, key: str) -> BudgetTracker | None:
        row = db.query("SELECT data FROM budgets WHERE key = %s", key)
        return BudgetTracker.deserialize(row["data"]) if row else None

    def save(self, key: str, tracker: BudgetTracker) -> None:
        db.upsert("budgets", key=key, data=tracker.serialize())

agent = Agent(
    model=model,
    budget=Budget(max_cost=10.00),
    budget_store=PostgresBudgetStore(),
    budget_store_key=f"user:{user_id}",   # Per-user isolation
)
```

---

## Why Syrin

| Feature | Syrin | DIY / Others |
|---------|-------|--------------|
| **Budget control** | Built-in, declarative | DIY or missing |
| **Pre-call estimates** | Automatic | Parse manually |
| **Post-call actuals** | Automatic | Parse provider response |
| **Rate windows** | hour/day/week/month built-in | Implement + persist |
| **Threshold alerts** | `BudgetThreshold(at=80, ...)` | Build from scratch |
| **Thread-safe parallel** | SQLite WAL built-in | Implement locks |
| **Agent memory** | 4 types, auto-managed | Manual setup |
| **Observability** | 72+ hooks, full traces | Add-on tools |
| **Multi-agent** | Handoff, spawn, pipeline | Complex orchestration |
| **Type-safe** | StrEnum, mypy strict | String hell |
| **Production API** | One-line serve | Build Flask wrapper |
| **Checkpoints** | State persistence | DIY |
| **Circuit breaking** | Built-in | External library |
| **Custom backends** | BudgetStore ABC | Full reimplementation |

---

## Real Projects Built with Syrin

### Voice AI Recruiter ([examples/resume_agent](examples/resume_agent))

A voice agent that handles recruiter calls using Syrin + Pipecat.

```bash
cd examples/resume_agent && python voice_server.py
```

### IPO Drafting Agent ([examples/ipo_drafting_agent](examples/ipo_drafting_agent))

Multi-agent system that drafts financial documents with full cost control.

### Research Assistant

Multi-agent system that researches topics, verifies facts, and writes reports.

---

## Documentation

| Resource | Description |
|----------|-------------|
| [Getting Started](docs/getting-started/quick-start.md) | 5-minute guide to your first agent |
| [Budget Control](docs/core/budget.md) | Complete budget guide + enterprise FAQ |
| [Memory](docs/core/memory.md) | Memory types, backends, decay |
| [Observability / Hooks](docs/debugging/hooks.md) | 72+ hook events, tracing |
| [Multi-Agent](docs/multi-agent/overview.md) | Handoff, spawn, DynamicPipeline |
| [Guardrails](docs/agent/guardrails.md) | PII, length, content filtering |
| [Serving](docs/production/serving.md) | HTTP API, playground, MCP |
| [Examples](examples/README.md) | Runnable code for every use case |

---

## Community

- [Website](https://syrin.ai)
- [Discord](https://discord.gg/p4jnKxYKpB)
- [Twitter](https://x.com/syrin_dev)
- [Issues](https://github.com/syrin-labs/syrin-python/issues)
- [Discussions](https://github.com/syrin-labs/syrin-python/discussions)

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <b>Agents that ship. Not surprise you with bills.</b>
</p>
