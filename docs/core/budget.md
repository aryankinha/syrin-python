---
title: Budget Control
description: Control AI spending with per-run limits, rate limits, and automatic safeguards. The most important feature for production deployments.
weight: 40
---

## AI Bills Can Spiral Out of Control

Imagine you're running a customer support chatbot. One day, a user asks a complex question, and your agent goes into a loop—calling the LLM dozens of times, each request costing money. By the end of the day, your \$50 "reasonable budget" has become $500. Your finance team is not happy.

Or think about a development team using AI agents for code review. Without spending controls, a single aggressive agent could burn through your entire monthly API budget in one sprint.

This is the reality of working with LLMs: every token costs money, and without controls, costs can explode unexpectedly.

**The solution?** Syrin's Budget system—the most important feature for anyone running AI agents in production.

---

## The Core Idea: A Personal Accountant for Your AI

Think of the Budget system as hiring an accountant for your agent. You tell it: "You have $10 to spend." The accountant tracks every dollar, warns you when you're at 80%, and pulls the plug before you go broke.

```
You: "Process this request, but don't spend more than $1"
         ↓
Budget Accountant: "I'll watch every penny"
         ↓
Agent runs... costs $0.50
         ↓
Budget Accountant: ✓ "Stayed within budget!"
         ↓
Agent runs again... costs would be $0.80
         ↓
Budget Accountant: "At 80%—flagging this..."
         ↓
Agent runs again... costs would be $0.40 MORE (total $1.30)
         ↓
Budget Accountant: ✗ "STOP! Would exceed budget by $0.30!"
```

---

## Quick Start: Your First Budget

```python
from syrin import Agent, Budget, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    budget=Budget(max_cost=1.00),  # Max $1 per request
)

response = agent.run("What is machine learning?")
print(f"Cost: ${response.cost:.6f}")
print(f"Remaining: ${agent.budget_state.remaining:.2f}")
```

**What just happened?**
- You created an agent with a **$1 per-request budget**
- The agent processed your question and tracked the cost
- You can see exactly how much was spent and what's left

**Try it without an API key:**
```python
from syrin import Model
agent = Agent(model=Model.Almock(), budget=Budget(max_cost=1.00))
```

---

## Understanding the Two Types of Limits

Syrin separates spending controls into two distinct concepts:

| What | Controls | Use When |
|------|----------|----------|
| **Budget** | **Cost in USD** | You care about dollars. Production cost control. |
| **TokenLimits** | **Number of tokens** | You care about API rate limits. Separate from cost. |

**Why separate?** Sometimes you want to limit spending without caring about token counts. Sometimes you hit provider rate limits (tokens/minute) even if you're not worried about cost. Syrin lets you use one, the other, or both.

---

## Budget Limits: A Complete Tour

### 1. Per-Run Budget (The Most Common)

The simplest budget: "Don't spend more than X per request."

```python
from syrin import Agent, Budget, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    budget=Budget(max_cost=0.50),  # $0.50 max per request
)
```

**When to use:** 
- Simple chatbots
- One-off queries
- When each request should be independent

### 2. The Reserve: Always Leave Something for the Reply

When you set `max_cost=1.00`, that's your total budget. But what if the model needs to reply and runs out of money mid-response?

Use `reserve` to hold back some budget specifically for the reply:

```python
budget = Budget(
    max_cost=1.00,
    reserve=0.20,  # Always keep $0.20 for the reply
)
# Effective limit: $0.80 for processing
```

**The math:** `effective_limit = max_cost - reserve = $0.80`

**Why this matters:** Without reserve, a $1 budget might spend $0.95 on processing, leaving only $0.05 for the reply. The response would be cut short. Reserve guarantees room for the answer.

### 3. Rate Limits: The Time-Based Guards

Rate limits let you set spending caps over time windows:

```python
from syrin import Agent, Budget, RateLimit, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    budget=Budget(
        max_cost=0.10,  # $0.10 per request
        rate_limits=RateLimit(
            hour=5.00,    # $5 per hour
            day=50.00,    # $50 per day
            week=100.00,  # $100 per week
            month=500.00, # $500 per month
        ),
    ),
)
```

**How rate windows work:**
- **Hour:** Fixed 60-minute window
- **Day:** Fixed 24-hour window
- **Week:** Fixed 7-day window
- **Month:** Rolling window by default (last N days)

### 4. Calendar Month vs. Rolling Month

By default, the month window is "last 30 days" (rolling). You can also use calendar months:

```python
# Rolling 30-day window (default)
RateLimit(month=500.00, month_days=30)

# Current calendar month (Nov 1-30, for example)
RateLimit(month=500.00, calendar_month=True)
```

**When to use calendar:** For billing cycles that align with calendar months (most companies).

**When to use rolling:** For consistent tracking regardless of billing cycles.

---

## What Counts Toward Budget?

Syrin tracks these costs automatically:

| Cost Type | What's Included |
|-----------|-----------------|
| **LLM tokens** | Input + output tokens from API calls |
| **Image generation** | DALL·E, Imagen, GPT Image generation |
| **Video generation** | Video generation APIs |
| **Voice generation** | TTS/voice synthesis |

**What doesn't count:** Tool execution (your code), external API calls your tools make, memory operations.

---

## Configuration Table: All Budget Options

```python
Budget(
    max_cost=10.00,               # Max USD per run
    reserve=0.50,                 # Reserve for reply
    rate_limits=RateLimit(...),  # Time-based limits
    on_exceeded=callback,         # What to do when exceeded
    thresholds=[...],             # Alert thresholds
    threshold_fallthrough=False,  # Run all or just highest threshold
    shared=False,                 # Share with child agents
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_cost` | `float \| None` | `None` | Maximum USD per single request/response cycle |
| `reserve` | `float` | `0` | Amount held for reply; effective limit is `max_cost - reserve` |
| `rate_limits` | `RateLimit \| None` | `None` | Time-based spending limits (hour/day/week/month) |
| `on_exceeded` | `Callable \| None` | `None` | Callback when any limit is exceeded |
| `thresholds` | `list[BudgetThreshold]` | `[]` | Alert thresholds (e.g., warn at 80%) |
| `threshold_fallthrough` | `bool` | `False` | If True, run all crossed thresholds; else only the highest |
| `shared` | `bool` | `False` | Share budget with spawned child agents |

### RateLimit Parameters

```python
RateLimit(
    hour=10.00,           # Max USD per hour
    day=50.00,            # Max USD per day
    week=200.00,          # Max USD per week
    month=500.00,         # Max USD per month
    month_days=30,        # Days in month window (1-31)
    calendar_month=False,  # Use calendar month instead of rolling
)
```

---

## Real-World Examples

### Example 1: Customer Support Bot

You want a bot that answers questions cheaply:

```python
from syrin import Agent, Budget, Model

class SupportBot(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = "You are a helpful customer support agent. Be concise."
    
    def __init__(self):
        super().__init__()
        self.budget = Budget(
            max_cost=0.05,  # 5 cents per question max
            rate_limits=RateLimit(day=10.00),  # $10 per day max
        )
```

### Example 2: Code Review Agent (Production)

A more complex agent with multiple safeguards:

```python
from syrin import Agent, Budget, RateLimit, Model
from syrin.threshold import BudgetThreshold
from syrin.enums import ThresholdWindow

class CodeReviewAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = "You are a senior code reviewer. Be thorough but efficient."
    
    def __init__(self):
        super().__init__()
        self.budget = Budget(
            max_cost=0.50,  # $0.50 per review
            rate_limits=RateLimit(
                hour=10.00,    # $10/hour to prevent runaway loops
                day=100.00,    # $100/day for safety
                month=500.00,  # $500/month budget
            ),
            on_exceeded=raise_on_exceeded,
            thresholds=[
                # Warn at 75% of request budget
                BudgetThreshold(
                    at=75,
                    action=lambda ctx: print(f"Using {ctx.percentage}% of request budget")
                ),
                # Alert if approaching daily limit
                BudgetThreshold(
                    at=90,
                    action=lambda ctx: print("Approaching daily limit!"),
                    window=ThresholdWindow.DAY,
                ),
            ],
        )
```

### Example 3: Multi-Tier Budget System

For a SaaS product with different user tiers:

```python
TIERS = {
    "free": Budget(max_cost=0.01, rate_limits=RateLimit(day=1.00, month=5.00)),
    "pro": Budget(max_cost=0.10, rate_limits=RateLimit(day=10.00, month=50.00)),
    "enterprise": Budget(max_cost=1.00, rate_limits=RateLimit(month=1000.00)),
}

def get_agent_for_tier(tier: str) -> Agent:
    return Agent(
        model=Model.OpenAI("gpt-4o-mini", api_key="your-key"),
        budget=TIERS.get(tier, TIERS["free"]),
    )
```

---

## Shared Budgets: Parent-Child Agent Patterns

When you spawn child agents, they can share the parent's budget:

```python
from syrin import Agent, Budget, Model

# Parent with shared budget
parent_budget = Budget(max_cost=5.00, shared=True)
parent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    budget=parent_budget,
)

# Child borrows from parent's shared budget
class ChildAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")

# Child's costs count against parent's budget
result = parent.spawn(ChildAgent, task="Research this topic")
print(f"Parent's remaining budget: ${parent.budget_state.remaining}")
```

**When to use:** Complex workflows where one agent delegates to specialists, and you want one unified spending limit.

---

## Checking Budget Status

### After Each Response

```python
response = agent.run("Hello!")

# Cost of this specific request
print(f"This request cost: ${response.cost:.6f}")

# Budget state (if Budget configured)
print(f"Remaining: ${response.budget_remaining}")
print(f"Used: ${response.budget_used}")
```

### Agent Budget State

```python
state = agent.budget_state

if state:
    print(f"Limit: ${state.limit:.2f}")
    print(f"Remaining: ${state.remaining:.2f}")
    print(f"Spent: ${state.spent:.2f}")
    print(f"Percent used: {state.percent_used:.1f}%")
```

### Full Budget Summary (with Rate Limits)

For detailed stats including hourly/daily/weekly/monthly spending:

```python
tracker = agent.get_budget_tracker()

if tracker:
    summary = tracker.get_summary()
    print(f"Run cost: ${summary.current_run_cost:.4f}")
    print(f"Hourly cost: ${summary.hourly_cost:.4f}")
    print(f"Daily cost: ${summary.daily_cost:.4f}")
    print(f"Monthly cost: ${summary.monthly_cost:.4f}")
```

---

## Budget and Streaming

When using `agent.stream()` or `agent.astream()`, budget works seamlessly:

- **Cost recorded per chunk:** You see costs accumulate in real-time
- **Budget checked after each chunk:** If you hit the limit mid-stream, it stops
- **You get partial output:** Even if budget is exceeded, you receive what was generated

```python
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    budget=Budget(max_cost=0.10),
)

for chunk in agent.stream("Write a long story"):
    print(chunk.content, end="", flush=True)
    # Budget is checked after each chunk
```

---

## Best Practices

### 1. Always Set a Reserve for Production

```python
# Good: Leaves room for the reply
Budget(max_cost=1.00, reserve=0.10)

# Risky: Might cut off the response
Budget(max_cost=1.00)
```

### 2. Use Multiple Safeguards

```python
# Good: Defense in depth
Budget(
    max_cost=0.10,
    rate_limits=RateLimit(hour=10.00, day=100.00),
    on_exceeded=raise_on_exceeded,
)

# Thin: One limit isn't enough
Budget(max_cost=10.00)  # What if someone calls it 1000 times?
```

### 3. Start Conservative, Adjust Based on Data

```python
# Start with conservative limits
Budget(max_cost=0.05, rate_limits=RateLimit(day=10.00))

# After monitoring real usage, adjust
Budget(max_cost=0.10, rate_limits=RateLimit(day=25.00))
```

### 4. Use Thresholds for Proactive Alerts

```python
from syrin.threshold import BudgetThreshold

Budget(
    max_cost=1.00,
    thresholds=[
        BudgetThreshold(at=50, action=lambda ctx: send_alert("Half budget used")),
        BudgetThreshold(at=75, action=lambda ctx: send_alert("75% used!")),
    ],
)
```

---

## Common Patterns

### Pattern 1: Per-User Budgets

Track spending per user in a multi-user application:

```python
from syrin.budget_store import FileBudgetStore

# Each user gets their own budget tracking
for user_id in user_ids:
    agent = Agent(
        model=Model.OpenAI("gpt-4o-mini", api_key="your-key"),
        budget=Budget(max_cost=1.00),
        budget_store=FileBudgetStore("/data/budgets.json"),
        budget_store_key=f"user:{user_id}",  # Isolated per user
    )
```

### Pattern 2: Organization-Level Budgets

Enforce a cap across all agents in an organization:

```python
# Shared store for the organization
store = FileBudgetStore("/data/org_budgets.json")

# All agents in org_123 share the same rate limit tracking
for agent_config in org_agents:
    agent = Agent(
        model=Model.OpenAI("gpt-4o-mini", api_key="your-key"),
        budget=Budget(max_cost=0.10, rate_limits=RateLimit(day=100.00)),
        budget_store=store,
        budget_store_key=f"org:{org_id}",  # Shared across org
    )
```

### Pattern 3: Budget-Aware Model Switching

Automatically switch to cheaper models when budget runs low:

```python
from syrin.threshold import BudgetThreshold

expensive_model = Model.OpenAI("gpt-4o", api_key="your-key")
cheap_model = Model.OpenAI("gpt-4o-mini", api_key="your-key")

agent = Agent(
    model=[expensive_model, cheap_model],  # Fallback chain
    budget=Budget(
        max_cost=1.00,
        thresholds=[
            BudgetThreshold(
                at=80,
                action=lambda ctx: ctx.parent.switch_model(cheap_model)
            ),
        ],
    ),
)
```

---

## Troubleshooting

### "Budget is being ignored"

1. Check that `Budget` is actually set on the agent
2. Verify `on_exceeded` isn't just logging (use `raise_on_exceeded` for hard stops)
3. For rate limits, ensure you're using a persistent store if you need limits across restarts

### "Rate limits not persisting"

Rate limits use in-memory tracking by default. To persist across restarts:

```python
agent = Agent(
    model=model,
    budget=Budget(rate_limits=RateLimit(day=50.00)),
    budget_store=FileBudgetStore("/tmp/budget.json"),
    budget_store_key="production",
)
```

### "Response got cut off"

You likely need a reserve to leave budget for the reply:

```python
Budget(max_cost=1.00, reserve=0.20)  # Reserve $0.20 for the reply
```

---

## FAQs

### How is budget calculated — pre-LLM call or after?

**Both.** Syrin runs a two-stage budget check:

1. **Pre-call (estimate):** Before sending to the LLM, Syrin estimates the cost from token count and the model's per-token price. If the estimate would exceed the limit, it fails fast — you never make the API call and never spend money.
2. **Post-call (actual):** After the LLM responds, the real token counts from the provider are recorded. This is the `response.cost` you see.

```python
result = agent.run("Hello")
print(f"Estimated (pre-call):  ${result.cost_estimated:.6f}")
print(f"Actual    (post-call): ${result.cost:.6f}")
print(f"Cache savings:         ${result.cache_savings:.6f}")
```

The pre-call check is conservative. If the estimate overshoots (which can happen with very short prompts), the actual cost is still recorded accurately. You won't be double-charged.

---

### What if an important task is running when the budget is exceeded?

Choose the right policy for the task's criticality:

```python
# Critical task — never abort, always complete
Budget(max_cost=1.00, exceed_policy=ExceedPolicy.WARN)   # logs + continues
Budget(max_cost=1.00, exceed_policy=ExceedPolicy.IGNORE) # silent + continues

# Non-critical task — hard stop
Budget(max_cost=1.00, exceed_policy=ExceedPolicy.STOP)   # raises BudgetExceededError
```

Pair with `reserve` to guarantee the agent always has budget left for its final reply:

```python
Budget(
    max_cost=1.00,
    reserve=0.20,               # Hold $0.20 back — used only for the reply
    exceed_policy=ExceedPolicy.WARN,  # Keep going even if processing exceeds $0.80
)
```

---

### How will I get warnings about budget?

Two mechanisms — use both:

**1. Threshold callbacks** — fires at a percentage of budget, proactively:

```python
from syrin.threshold import BudgetThreshold

Budget(
    max_cost=1.00,
    thresholds=[
        BudgetThreshold(at=75, action=lambda ctx: send_slack_alert(f"75% budget used")),
        BudgetThreshold(at=90, action=lambda ctx: page_oncall("90% budget used!")),
    ],
)
```

**2. `on_exceeded` / `ExceedPolicy.WARN`** — fires when the hard limit is hit:

```python
Budget(max_cost=1.00, exceed_policy=ExceedPolicy.WARN)
# → logs: "Budget exceeded: run cost $1.02 >= $1.00"
```

Both emit hook events you can subscribe to programmatically:

```python
from syrin.enums import Hook

agent.events.on(Hook.BUDGET_THRESHOLD, lambda p: ...)
agent.events.on(Hook.BUDGET_EXCEEDED, lambda p: ...)
```

---

### Is model switching working? Do I have to do it manually?

**Threshold-driven switching works today** — you wire it to a threshold action:

```python
cheap_model = Model.OpenAI("gpt-4o-mini", api_key="...")

Budget(
    max_cost=1.00,
    thresholds=[
        BudgetThreshold(
            at=70,
            action=lambda ctx: ctx.parent.switch_model(cheap_model),
        ),
    ],
)
```

When 70% of budget is consumed, the agent automatically switches to the cheaper model for remaining calls — no manual intervention.

**Fully automatic routing** (no threshold needed, based on task type + budget state) is planned for v0.10.0.

---

### What is `reserve` for?

`reserve` holds back a portion of the budget specifically for the final reply. Without it, the agent might spend 99% of its budget on tool calls and receive a truncated response because the model ran out of money mid-sentence.

```python
Budget(max_cost=1.00, reserve=0.20)
# effective processing limit = $0.80
# $0.20 is always available for the response
```

**Rule of thumb:** Set reserve to ~10–20% of your max_cost, or at least enough for a full reply at your model's output price.

---

### Is budget tracked in observability / tracing?

Yes — budget state is emitted on every lifecycle hook event. Every `BUDGET_EXCEEDED` and `BUDGET_THRESHOLD` hook carries the full budget state (spent, remaining, limit, policy).

When using `agent.serve(debug=True)`, each request's trace span includes the budget cost for that call.

For structured access, use the dashboard API:

```python
summary = agent.budget_summary()
# → run_cost, run_tokens, hourly/daily/weekly/monthly totals,
#    max_cost, reserve, budget_remaining, budget_percent_used, exceed_policy

rows = agent.export_costs(format="json")
# → [{cost_usd, total_tokens, model, timestamp}, ...]
```

Export to any monitoring system (Datadog, Grafana, CloudWatch) from `export_costs()`.

---

### Can I tweak budget limits using remote config?

Yes. `Budget` implements `RemoteConfigurable`. Wire a config source (feature flags, LaunchDarkly, your own config server) and push new limits to running agents without restart:

```python
from syrin.remote import RemoteConfig

rc = RemoteConfig(source=YourConfigSource())
rc.attach(agent)
# Config push: {"budget": {"max_cost": 5.0, "reserve": 0.5}}
# → agent budget updates live
```

Remotely configurable fields: `max_cost`, `reserve`, `shared`.

Rate limits are intentionally not remote-configurable — changing them live could cause race conditions in accumulated window counts.

---

### How does budget work with parallel multi-agents?

Use `Budget(shared=True)` to create a single pool that all spawned agents draw from:

```python
pool = Budget(max_cost=10.00, shared=True, on_exceeded=warn_on_exceeded)
orchestrator = Agent(model=model, budget=pool)

# All spawned children deduct from the same $10 pool
orchestrator.spawn(ResearchAgent, task="Research topic A")
orchestrator.spawn(ResearchAgent, task="Research topic B")
orchestrator.spawn(WriterAgent, task="Write summary")
```

**Thread safety:** The budget tracker uses SQLite in WAL (write-ahead logging) mode with a `threading.Lock()` around all operations. Parallel agents cannot double-spend.

**Per-user isolation:** Use `budget_store_key` to isolate separate users or organizations even when they share the same agent definition:

```python
agent = Agent(
    model=model,
    budget=Budget(max_cost=1.00, rate_limits=RateLimit(day=10.00)),
    budget_store=FileBudgetStore("/data/budgets.json"),
    budget_store_key=f"user:{user_id}",
)
```

---

### Why should I trust your budget system?

- **Pre-call estimates** mean you fail before spending — not after.
- **Post-call actuals** are from provider token counts, not guesses.
- **Thread-safe SQLite** prevents double-spend in parallel workloads.
- **`reserve`** guarantees the reply is never truncated by an empty budget.
- **Threshold re-fire guard** prevents the same threshold from spamming callbacks on every subsequent call.
- **100+ unit tests** cover budget contract edge cases (what happens if `on_exceeded` raises, returns, or is `None`).

All budget logic is in `src/syrin/budget/` — open source, auditable, no hidden state.

---

### What if a provider updates their LLM pricing?

Two options:

**Option A — Override per model instance (immediate, no code change):**

```python
from syrin.cost import ModelPricing

agent = Agent(
    model=Model(
        model_id="openai/gpt-4o",
        pricing=ModelPricing(
            input_per_1m=2.50,    # Updated rate
            output_per_1m=10.00,  # Updated rate
        ),
    ),
)
```

This takes effect immediately for all calls on that agent.

**Option B — Update the built-in pricing table:**

Edit `src/syrin/cost/__init__.py` → `MODEL_PRICING` dict, bump the version, and cut a patch release. The table is clearly commented with sources (Anthropic/OpenAI public pricing pages).

**Option C — Remote config pricing** (planned for v0.10.0): push updated rates via the config server without a code change.

---

### Why use Syrin's budgeting instead of custom logic?

| Feature | DIY | Syrin |
|---------|-----|-------|
| Pre-call estimates | Manual | Automatic |
| Post-call actuals | Parse provider response | Automatic |
| Rate windows (hour/day/month) | Implement + persist | Built-in |
| Threshold alerts at % | Implement | BudgetThreshold |
| Thread-safe parallel agents | Implement locks | Built-in SQLite WAL |
| Per-user isolation | Build key-value store | budget_store_key |
| Reserve for reply | Manual tracking | reserve= param |
| Model auto-switch on budget | Build routing logic | switch_model() |
| Observability integration | Emit events manually | Built-in hooks |

The budget system is integrated into the agent loop — you don't wire it up, it just works.

---

### Can I integrate my own custom budgeting?

Yes. `BudgetStore` is an abstract base class — implement `load()` and `save()` to plug in any persistence backend:

```python
from syrin.budget_store import BudgetStore, BudgetTracker

class PostgresBudgetStore(BudgetStore):
    def load(self, key: str) -> BudgetTracker | None:
        row = db.query("SELECT data FROM budgets WHERE key = %s", key)
        return BudgetTracker.deserialize(row["data"]) if row else None

    def save(self, key: str, tracker: BudgetTracker) -> None:
        db.execute(
            "INSERT INTO budgets (key, data) VALUES (%s, %s) ON CONFLICT DO UPDATE SET data = %s",
            key, tracker.serialize(), tracker.serialize(),
        )

agent = Agent(
    model=model,
    budget=Budget(max_cost=10.00),
    budget_store=PostgresBudgetStore(),
    budget_store_key="org:acme",
)
```

The built-in options are `InMemoryBudgetStore` (default, no persistence) and `FileBudgetStore` (JSON file). Any storage system you can wrap in `load()`/`save()` works.

---

## What's Next?

- **[Budget Callbacks](/core/budget-callbacks)** — Learn how to react to budget events with custom callbacks, thresholds, and alerting
- **[Model Routing](/core/models-routing)** — Automatically switch models based on budget and task requirements
- **[Memory & Budget](/core/memory)** — Understand how memory operations interact with your budget

## See Also

- [Budget Callbacks](/core/budget-callbacks) — Custom budget handling
- [Model Routing](/core/models-routing) — Budget-aware model selection
- [Rate Limiting](/production/rate-limiting) — Production rate limiting patterns
