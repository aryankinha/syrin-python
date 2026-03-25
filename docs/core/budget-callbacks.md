---
title: Budget Callbacks & Thresholds
description: React to budget events with custom callbacks, alerts, and automatic model switching. The intelligence layer of budget control.
weight: 41
---

## Budget Limits Are Meaningless Without Actions

You've set a budget. Great. But what happens when the budget is exceeded? If you just set `Budget(max_cost=1.00)` and nothing else, the agent will happily spend \$10, \$100, \$1,000—whatever it takes to answer the question.

A budget without a response strategy is like a smoke detector without a fire alarm: it detects the problem but doesn't do anything about it.

**The solution?** Budget callbacks and thresholds—the intelligence layer that makes your budget actually work.

---

## The Three Built-in Callbacks

Syrin provides three ready-to-use callbacks for common scenarios:

```python
from syrin import raise_on_exceeded, warn_on_exceeded, stop_on_exceeded
from syrin.budget import BudgetExceededContext
```

### 1. `warn_on_exceeded`: Log and Continue

The gentlest option. When the budget is exceeded, it logs a warning but lets the agent continue:

```python
from syrin import Agent, Budget, Model, warn_on_exceeded

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    budget=Budget(
        max_cost=0.50,
        on_exceeded=warn_on_exceeded,  # Just logs, continues running
    ),
)

response = agent.run("Complex question...")
# If exceeded: logs warning, but still returns response
print(f"Got response despite warning: {response.content[:50]}...")
```

**When to use:**
- Development and testing (you want to see results even if over budget)
- Non-critical applications where completion matters more than budget
- When you have other safeguards in place

### 2. `raise_on_exceeded`: Hard Stop

The strict option. When exceeded, raises `BudgetExceededError` and stops immediately:

```python
from syrin import Agent, Budget, Model, raise_on_exceeded
from syrin.exceptions import BudgetExceededError

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    budget=Budget(
        max_cost=0.50,
        on_exceeded=raise_on_exceeded,  # Stops immediately
    ),
)

try:
    response = agent.run("Complex question...")
except BudgetExceededError as e:
    print(f"Budget exceeded: {e}")
    print(f"Current cost: ${e.current_cost:.4f}")
    print(f"Limit: ${e.limit:.4f}")
```

**When to use:**
- Production systems where budget discipline is critical
- Cost-sensitive applications
- When you have retry logic that can handle the error

### 3. `stop_on_exceeded`: Threshold-Based Stop

Similar to `raise_on_exceeded`, but specifically for threshold-triggered stops:

```python
from syrin import Agent, Budget, Model, stop_on_exceeded

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    budget=Budget(
        max_cost=0.50,
        on_exceeded=stop_on_exceeded,  # For threshold-triggered stops
    ),
)
```

**When to use:** When you want to distinguish between hard limit exceeded vs threshold-based stopping.

---

## The BudgetExceededContext: Your Window into Budget Events

When a callback is triggered, it receives a `BudgetExceededContext` object with all the details:

```python
from syrin.budget import BudgetExceededContext

def my_callback(ctx: BudgetExceededContext):
    print(f"Limit exceeded!")
    print(f"  Type: {ctx.budget_type}")      # e.g., "run", "hour", "day"
    print(f"  Current cost: ${ctx.current_cost:.4f}")
    print(f"  Limit: ${ctx.limit:.4f}")
    print(f"  Message: {ctx.message}")
```

| Field | Type | Description |
|-------|------|-------------|
| `current_cost` | `float` | Amount spent when exceeded |
| `limit` | `float` | The limit that was exceeded |
| `budget_type` | `BudgetLimitType` | Which limit: RUN, HOUR, DAY, WEEK, MONTH, etc. |
| `message` | `str` | Human-readable description |

---

## Custom Callbacks: Making Budget Work for You

The real power comes from custom callbacks. You can do anything:

### Example 1: Send Alerts to Slack

```python
import httpx

def alert_to_slack(ctx: BudgetExceededContext):
    """Send alert when budget is exceeded."""
    payload = {
        "text": f"⚠️ Budget Alert",
        "attachments": [{
            "color": "danger",
            "fields": [
                {"title": "Limit Type", "value": ctx.budget_type.value},
                {"title": "Current Cost", "value": f"${ctx.current_cost:.4f}"},
                {"title": "Limit", "value": f"${ctx.limit:.4f}"},
            ]
        }]
    }
    httpx.post("https://hooks.slack.com/services/YOUR/WEBHOOK", json=payload)

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    budget=Budget(max_cost=1.00, on_exceeded=alert_to_slack),
)
```

### Example 2: Upgrade User Tier

```python
def upgrade_user_tier(ctx: BudgetExceededContext):
    """Upgrade user when they hit budget limits."""
    user_id = get_current_user_id()
    db.update_user_tier(user_id, "pro")  # Upgrade to paid tier
    print(f"User {user_id} upgraded to pro tier")

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    budget=Budget(max_cost=5.00, on_exceeded=upgrade_user_tier),
)
```

### Example 3: Store for Audit Trail

```python
import json
from datetime import datetime

exceeded_events = []

def audit_budget_exceeded(ctx: BudgetExceededContext):
    """Store exceeded events for later analysis."""
    exceeded_events.append({
        "timestamp": datetime.now().isoformat(),
        "budget_type": ctx.budget_type.value,
        "current_cost": ctx.current_cost,
        "limit": ctx.limit,
        "message": ctx.message,
    })
    # Save to file
    with open("budget_exceeded.json", "w") as f:
        json.dump(exceeded_events, f, indent=2)

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    budget=Budget(max_cost=1.00, on_exceeded=audit_budget_exceeded),
)
```

### Example 4: Graceful Degradation

```python
def graceful_degradation(ctx: BudgetExceededContext):
    """Fallback to cheaper model when budget exceeded."""
    print("Budget exceeded—switching to fallback model")
    # The callback can modify agent state
    # (In practice, use thresholds for model switching)

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    budget=Budget(max_cost=0.50, on_exceeded=graceful_degradation),
)
```

---

## Thresholds: Proactive Budget Intelligence

While `on_exceeded` is reactive (something already happened), **thresholds are proactive** (something is about to happen).

### The Core Concept

A threshold triggers an action when budget usage reaches a certain percentage:

```python
from syrin import Budget
from syrin.threshold import BudgetThreshold

budget = Budget(
    max_cost=1.00,
    thresholds=[
        BudgetThreshold(at=50, action=lambda ctx: print("Halfway there!")),
        BudgetThreshold(at=80, action=lambda ctx: print("Getting expensive!")),
        BudgetThreshold(at=95, action=lambda ctx: print("Almost out of budget!")),
    ],
)
```

**How it works:**
- At 0-49%: No thresholds triggered
- At 50-79%: Only 50% threshold runs
- At 80-94%: Only 80% threshold runs
- At 95%+: Only 95% threshold runs

By default, **only the highest crossed threshold runs**. This prevents a cascade of alerts.

---

## Threshold Windows: Different Perspectives

Thresholds can watch different windows:

```python
from syrin import Budget, RateLimit
from syrin.threshold import BudgetThreshold
from syrin.enums import ThresholdWindow

budget = Budget(
    max_cost=1.00,
    rate_limits=RateLimit(day=10.00),
    thresholds=[
        # Monitor per-request budget
        BudgetThreshold(at=80, action=alert_request),
        
        # Monitor daily spending
        BudgetThreshold(
            at=90,
            action=alert_daily,
            window=ThresholdWindow.DAY,
        ),
        
        # Monitor hourly spending
        BudgetThreshold(
            at=75,
            action=alert_hourly,
            window=ThresholdWindow.HOUR,
        ),
    ],
)
```

| Window | What It Tracks |
|--------|----------------|
| `RUN` | This specific request's budget |
| `HOUR` | Spending in the last hour |
| `DAY` | Spending in the last 24 hours |
| `WEEK` | Spending in the last 7 days |
| `MONTH` | Spending in the last 30 days (or calendar month) |

---

## Threshold Actions: Beyond Logging

### Action 1: Switch to a Cheaper Model

Automatically downgrade when budget gets low:

```python
from syrin import Agent, Budget, Model

cheap_model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
expensive_model = Model.OpenAI("gpt-4o", api_key="your-key")

def switch_to_cheap(ctx):
    """Switch to cheaper model when 80% budget used."""
    if hasattr(ctx.parent, "switch_model"):
        ctx.parent.switch_model(cheap_model)
        print("Switched to gpt-4o-mini to conserve budget")

agent = Agent(
    model=expensive_model,
    budget=Budget(
        max_cost=1.00,
        thresholds=[
            BudgetThreshold(at=80, action=switch_to_cheap),
        ],
    ),
)
```

### Action 2: Compact Context to Save Tokens

Reduce context size to lower costs:

```python
from syrin.threshold import BudgetThreshold, compact_if_available

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    budget=Budget(max_cost=0.50),
    # ... (needs context configuration)
)

# When budget is 75% used, compact context
BudgetThreshold(at=75, action=compact_if_available)
```

### Action 3: Send Real-Time Notifications

```python
import logging

def notify_budget_alert(ctx):
    """Send alert through multiple channels."""
    # Log
    logging.warning(f"Budget alert: {ctx.percentage}% used")
    
    # Email (pseudocode)
    email.send(
        to="team@company.com",
        subject=f"Budget at {ctx.percentage}%",
        body=f"Current spend: ${ctx.current_value:.2f}"
    )
    
    # Metrics
    metrics.increment(f"budget.alert.{ctx.percentage}")

budget = Budget(
    max_cost=10.00,
    thresholds=[
        BudgetThreshold(at=50, action=notify_budget_alert),
        BudgetThreshold(at=75, action=notify_budget_alert),
        BudgetThreshold(at=90, action=notify_budget_alert),
    ],
)
```

### Action 4: Record for Analytics

```python
from datetime import datetime
import json

class BudgetAnalytics:
    def __init__(self, filename="budget_analytics.json"):
        self.filename = filename
        self.events = []
    
    def record(self, ctx):
        event = {
            "timestamp": datetime.now().isoformat(),
            "percentage": ctx.percentage,
            "current_value": ctx.current_value,
            "limit_value": ctx.limit_value,
            "metric": str(ctx.metric),
        }
        self.events.append(event)
        
        with open(self.filename, "w") as f:
            json.dump(self.events, f, indent=2)
    
    def get_report(self):
        return {
            "total_events": len(self.events),
            "peak_percentage": max(e["percentage"] for e in self.events),
            "total_spend": sum(e["current_value"] for e in self.events),
        }

analytics = BudgetAnalytics()

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    budget=Budget(
        max_cost=10.00,
        thresholds=[
            BudgetThreshold(at=25, action=analytics.record),
            BudgetThreshold(at=50, action=analytics.record),
            BudgetThreshold(at=75, action=analytics.record),
        ],
    ),
)
```

---

## Threshold Fallthrough: Run All Crossed Thresholds

By default, only the highest crossed threshold runs. To run all:

```python
budget = Budget(
    max_cost=1.00,
    threshold_fallthrough=True,  # Run ALL crossed thresholds
    thresholds=[
        BudgetThreshold(at=50, action=log_info),
        BudgetThreshold(at=75, action=log_warning),
        BudgetThreshold(at=90, action=log_critical),
    ],
)
```

**With fallthrough=True and 85% usage:** All three thresholds run (50%, 75%, 90%).

**With fallthrough=False (default) at 85%:** Only 75% threshold runs.

---

## Threshold Ranges: Precise Control

Use `at_range` to trigger only within a specific percentage band:

```python
from syrin.threshold import BudgetThreshold

budget = Budget(
    max_cost=1.00,
    thresholds=[
        # Only trigger between 70-80%
        BudgetThreshold(
            at_range=(70, 80),
            action=lambda ctx: print("In the danger zone!")
        ),
    ],
)
```

**Why use ranges?** To avoid duplicate alerts when usage is stable (e.g., sitting at exactly 75%).

---

## Token Usage Thresholds

Budget thresholds work with both cost AND token usage:

```python
from syrin import Budget, TokenLimits, TokenRateLimit
from syrin.threshold import BudgetThreshold, ThresholdContext
from syrin.enums import ThresholdMetric, ThresholdWindow

budget = Budget(
    max_cost=1.00,  # $1 USD budget
    rate_limits=RateLimit(hour=10.00),
    thresholds=[
        # Alert when 80% of dollar budget used
        BudgetThreshold(
            at=80,
            metric=ThresholdMetric.COST,
            action=lambda ctx: print(f"${ctx.current_value:.2f} spent"),
        ),
        # Alert when 90% of hourly rate limit used
        BudgetThreshold(
            at=90,
            metric=ThresholdMetric.COST,
            window=ThresholdWindow.HOUR,
            action=lambda ctx: print("Hourly rate limit warning!"),
        ),
    ],
)
```

---

## Complete Example: A Production-Grade Budget System

Here's a comprehensive example showing all concepts together:

```python
from syrin import Agent, Budget, RateLimit, Model
from syrin.threshold import BudgetThreshold
from syrin.enums import ThresholdWindow
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Analytics tracking
class BudgetAnalytics:
    def __init__(self):
        self.alerts = []
        self.thresholds_triggered = 0
    
    def alert(self, ctx: ThresholdContext):
        self.thresholds_triggered += 1
        event = {
            "timestamp": datetime.now().isoformat(),
            "percentage": ctx.percentage,
            "current": ctx.current_value,
            "limit": ctx.limit_value,
            "window": str(ctx.parent.thresholds[0].window) if ctx.parent.thresholds else "run",
        }
        self.alerts.append(event)
        logger.warning(f"Budget {ctx.percentage}%: ${ctx.current_value:.2f}/${ctx.limit_value:.2f}")
    
    def exceeded_callback(self, ctx):
        logger.error(f"BUDGET EXCEEDED: {ctx.budget_type.value}")
        self.alerts.append({
            "timestamp": datetime.now().isoformat(),
            "type": "exceeded",
            "budget_type": ctx.budget_type.value,
            "cost": ctx.current_cost,
            "limit": ctx.limit,
        })

# Initialize
analytics = BudgetAnalytics()

# Production budget
production_budget = Budget(
    max_cost=0.50,  # $0.50 per request
    rate_limits=RateLimit(
        hour=10.00,    # $10/hour
        day=100.00,    # $100/day
        month=500.00,  # $500/month
    ),
    on_exceeded=analytics.exceeded_callback,
    thresholds=[
        # Per-request alerts
        BudgetThreshold(
            at=50,
            action=analytics.alert,
            window=ThresholdWindow.RUN,
        ),
        BudgetThreshold(
            at=80,
            action=analytics.alert,
            window=ThresholdWindow.RUN,
        ),
        
        # Daily spending alerts
        BudgetThreshold(
            at=75,
            action=analytics.alert,
            window=ThresholdWindow.DAY,
        ),
        BudgetThreshold(
            at=90,
            action=analytics.alert,
            window=ThresholdWindow.DAY,
        ),
    ],
    threshold_fallthrough=True,
)

# Production agent
class ProductionAgent(Agent):
    model = Model.OpenAI("gpt-4o", api_key="your-key")
    system_prompt = "You are a helpful assistant. Be efficient."
    
    def __init__(self):
        super().__init__()
        self.budget = production_budget

# Usage
agent = ProductionAgent()

try:
    response = agent.run("Help me with this task")
    print(f"Response: {response.content[:100]}...")
    print(f"Cost: ${response.cost:.6f}")
except Exception as e:
    print(f"Request blocked: {e}")

# Check analytics
print(f"Total alerts: {analytics.thresholds_triggered}")
print(f"Recent events: {json.dumps(analytics.alerts[-3:], indent=2)}")
```

---

## The ThresholdContext Object

When a threshold triggers, it receives a `ThresholdContext`:

```python
from syrin.threshold import ThresholdContext

def my_action(ctx: ThresholdContext):
    # Utilization percentage (0-100) that triggered
    print(f"Percentage: {ctx.percentage}%")
    
    # What metric: COST or TOKENS
    print(f"Metric: {ctx.metric}")
    
    # Current value: cost so far OR tokens used
    print(f"Current: {ctx.current_value}")
    
    # The limit
    print(f"Limit: {ctx.limit_value}")
    
    # The parent object (the Budget or Agent)
    print(f"Parent: {ctx.parent}")
    
    # Extra data
    print(f"Metadata: {ctx.metadata}")
```

| Field | Type | Description |
|-------|------|-------------|
| `percentage` | `int` | Utilization percentage (0-100) |
| `metric` | `ThresholdMetric` | COST or TOKENS |
| `current_value` | `float` | Current cost or token count |
| `limit_value` | `float` | The limit (run budget, rate cap) |
| `budget_run` | `float` | Alias for limit_value (when metric is COST) |
| `parent` | `Any` | The Budget or Agent object |
| `metadata` | `dict` | Extra context data |

---

## Event Hooks for Budget

Syrin emits lifecycle events for budget operations:

```python
agent.events.on("budget.threshold", lambda e: print(f"Budget {e['percent']}%"))
agent.events.on("budget.exceeded", lambda e: print(f"Budget exceeded: {e}"))
```

| Event | When | Payload |
|-------|------|---------|
| `budget.check` | Budget checked during run | Status, exceeded_limit |
| `budget.threshold` | Threshold crossed | at, at_range, percent, metric, tokens, max_tokens |
| `budget.exceeded` | Hard limit exceeded | used, limit, exceeded_by |

---

## Common Patterns

### Pattern 1: Tiered Alerting

```python
def tiered_alert(ctx):
    if ctx.percentage >= 95:
        send_sms("CRITICAL: Budget nearly exhausted!")
        notify_slack("@here Budget critical!")
    elif ctx.percentage >= 80:
        send_sms("WARNING: Budget at 80%")
    else:
        log_info(f"Budget at {ctx.percentage}%")

BudgetThreshold(at=50, action=lambda ctx: log_info("50%"))
BudgetThreshold(at=80, action=tiered_alert)
BudgetThreshold(at=95, action=tiered_alert)
```

### Pattern 2: Cooldown Between Alerts

```python
import time

last_alert_time = 0
COOLDOWN = 60  # seconds

def cooldown_alert(ctx):
    global last_alert_time
    if time.time() - last_alert_time > COOLDOWN:
        send_alert(f"Budget at {ctx.percentage}%")
        last_alert_time = time.time()

BudgetThreshold(at=75, action=cooldown_alert)
```

### Pattern 3: Aggregate Budget Tracking

```python
class BudgetTracker:
    def __init__(self):
        self.data = defaultdict(list)
    
    def track(self, ctx):
        key = (ctx.metric.value, str(ctx.parent.thresholds[0].window))
        self.data[key].append({
            "timestamp": time.time(),
            "percentage": ctx.percentage,
            "current": ctx.current_value,
        })
    
    def summary(self):
        return {k: len(v) for k, v in self.data.items()}
```

---

## Troubleshooting Callbacks and Thresholds

### "My threshold action isn't running"

1. **Check the percentage:** Thresholds only run when usage >= threshold
2. **Verify the window:** Make sure you're monitoring the right window (RUN vs HOUR vs DAY)
3. **Check fallthrough:** With default settings, only the highest threshold runs
4. **Action signature:** Ensure your action accepts a `ThresholdContext` parameter

### "on_exceeded not triggering"

1. **Verify it's set:** `Budget(max_cost=1.00, on_exceeded=callback)`
2. **It's not raising:** If you want to stop, use `raise_on_exceeded`, not a logging function
3. **Timing:** `on_exceeded` triggers after the LLM call, not before

### "Getting multiple threshold triggers"

Use `at_range` to create bands:

```python
# Bad: Triggers at 75, 76, 77, 78...
BudgetThreshold(at=75, action=alert)

# Good: Triggers only once in the 75-80% band
BudgetThreshold(at_range=(75, 80), action=alert)
```

Or use fallthrough=False (default) and set thresholds at intervals:

```python
# Only one runs: 85 (the highest crossed)
BudgetThreshold(at=50, action=log)
BudgetThreshold(at=75, action=log)
BudgetThreshold(at=85, action=log)
```

---

## Best Practices

### 1. Use Fallthrough Judiciously

```python
# Good: Clear escalation
threshold_fallthrough=False,
thresholds=[
    BudgetThreshold(at=50, action=log),
    BudgetThreshold(at=80, action=alert),
    BudgetThreshold(at=95, action=escalate),
]

# Risky: All run, could cause alert spam
threshold_fallthrough=True
```

### 2. Distinguish Between Warning and Stopping

```python
# on_exceeded: What to do when HARD limit hit
on_exceeded=raise_on_exceeded  # Stop immediately

# thresholds: Proactive warnings before hitting limit
thresholds=[
    BudgetThreshold(at=80, action=warn),  # Warning
    BudgetThreshold(at=95, action=stop),  # Graceful stop
]
```

### 3. Include Context in Alerts

```python
def detailed_alert(ctx):
    message = (
        f"Budget Alert!\n"
        f"  User: {get_current_user()}\n"
        f"  Percentage: {ctx.percentage}%\n"
        f"  Spent: ${ctx.current_value:.2f}\n"
        f"  Limit: ${ctx.limit_value:.2f}\n"
        f"  Window: {ctx.metric}/{ctx.window}"
    )
    send_alert(message)
```

### 4. Test Your Callbacks

```python
def test_callback(ctx: BudgetExceededContext):
    assert ctx.current_cost > 0
    assert ctx.limit > 0
    print("Callback test passed!")

# In tests
from syrin.budget import BudgetExceededContext
test_callback(BudgetExceededContext(
    current_cost=1.05,
    limit=1.00,
    budget_type="run",
    message="Test exceeded",
))
```

---

## What's Next?

- **[Model Routing](/core/models-routing)** — Automatically select models based on budget and task complexity
- **[Production Patterns](/production/serving)** — Deploy budget-controlled agents in production
- **[Memory & Budget](/core/memory)** — Understand memory cost implications

## See Also

- [Budget Overview](/core/budget) — Budget basics and configuration
- [Model Routing](/core/models-routing) — Budget-aware model selection
- [Rate Limiting](/production/rate-limiting) — Production rate limiting
- [Guardrails](/agent/guardrails) — Policy enforcement including budget guards
