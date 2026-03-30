---
title: Rate Limiting
description: Manage API quotas with proactive threshold actions and multi-backend support
weight: 150
---

## The Day the Bill Arrived

Your agent worked beautifully for weeks. Then the end of the month came. You opened the API bill and nearly fell out of your chair.

You'd sent 10 million tokens in a single day because a script ran wild. The budget that was supposed to last months was gone in hours.

API providers have rate limits for good reasons:
- Prevent abuse
- Ensure fair access
- Protect their infrastructure
- Help you control costs

Without rate limiting, you're at the mercy of your own code. One bug, one misconfigured script, one runaway loop—and your API access is throttled (or your bill skyrockets).

## The Problem

Managing API quotas is harder than it sounds:
- **Hard limits** — Providers cut you off when exceeded
- **Soft limits** — Providers warn, then cut off
- **Burst traffic** — Sudden spikes can trigger limits
- **Cost surprises** — Token counts add up fast
- **No visibility** — You don't know you're close until you're blocked

Traditional approaches:
- Simple counters (easy to misconfigure)
- No threshold actions (no warning before limits hit)
- No persistence (state lost on restart)

## The Solution

Syrin's rate limiting gives you proactive control:

```python
from syrin import Agent, Model
from syrin.ratelimit import APIRateLimit
from syrin.threshold import RateLimitThreshold
from syrin.enums import ThresholdMetric

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(
    model=model,
    rate_limit=APIRateLimit(
        rpm=500,          # 500 requests per minute
        tpm=150000,       # 150k tokens per minute
        rpd=10000,        # 10k requests per day
    ),
)
```

**What just happened**: The agent now tracks requests and token usage against these limits. When limits are approached or exceeded, you get warnings (or can take action).

## How It Works

The rate limiter tracks usage in rolling windows. Each request is recorded with a timestamp, and entries older than the window (60 seconds for RPM/TPM, 24 hours for RPD) are automatically pruned.

### Tracking Metrics

| Metric | Tracks | Window |
|--------|--------|--------|
| RPM | Requests per minute | Rolling 60 seconds |
| TPM | Tokens per minute | Rolling 60 seconds |
| RPD | Requests per day | Rolling 24 hours |

## Threshold Actions

The real power comes from threshold actions—functions that run when you hit a percentage of a limit:

```python
from syrin.threshold import RateLimitThreshold
from syrin.enums import ThresholdMetric


def warn_rpm(ctx):
    print(f"⚠️  RPM at {ctx.percentage}% ({ctx.current_value}/{ctx.limit_value})")
    send_alert_to_ops(f"RPM usage: {ctx.percentage}%")


def warn_tpm(ctx):
    print(f"⚠️  TPM at {ctx.percentage}%")
    if ctx.percentage >= 90:
        # Switch to a more efficient model
        model_manager.switch_to_efficient_model()


agent = Agent(
    model=model,
    rate_limit=APIRateLimit(
        rpm=500,
        tpm=150000,
        thresholds=[
            RateLimitThreshold(
                at=80,
                action=warn_rpm,
                metric=ThresholdMetric.RPM,
            ),
            RateLimitThreshold(
                at=80,
                action=warn_tpm,
                metric=ThresholdMetric.TPM,
            ),
        ],
    ),
)
```

**What just happened**: At 80% RPM, you get a warning and can alert ops. At 90% TPM, you switch to a more efficient model.

## Threshold Reference

### Threshold Types

```python
from syrin.threshold import RateLimitThreshold
from syrin.enums import ThresholdMetric

# Warn at 80%
RateLimitThreshold(at=80, action=warn, metric=ThresholdMetric.RPM)

# Warn at specific range (70-75%)
RateLimitThreshold(
    at_range=(70, 75),
    action=alert,
    metric=ThresholdMetric.TPM,
)

# Critical at 95%
RateLimitThreshold(at=95, action=critical_alert, metric=ThresholdMetric.RPD)
```

### Trigger Conditions

| Threshold | Triggers When |
|-----------|---------------|
| `at=80` | Usage >= 80% |
| `at_range=(70, 80)` | 70% to 80% usage |

## Blocking Behavior

When limits are reached, requests are blocked:

```python
allowed, reason = rate_limit_manager.check(tokens_used=500)

if not allowed:
    raise RateLimitExceeded(f"Rate limit: {reason}")
```

### Default Behavior

- **Threshold actions** (at %): Execute callbacks but don't block
- **Hard limits** (rpm, tpm, rpd): Block when exceeded

## Auto-Detection

Let Syrin auto-detect limits for your model:

```python
from syrin.ratelimit import APIRateLimit

# Auto-detect limits for gpt-4o
rate_limit = APIRateLimit.auto_detect_for_model("openai/gpt-4o")
print(f"RPM: {rate_limit.rpm}, TPM: {rate_limit.tpm}")
```

**What just happened**: Syrin looked up the known limits for this model and configured them automatically.

## Persistence Backends

For multi-instance deployments, use persistent backends:

### Memory (Default)

```python
from syrin.ratelimit import APIRateLimit

rate_limit = APIRateLimit(rpm=500)  # In-memory only
```

State is lost on restart. Good for single-instance deployments.

### SQLite

```python
from syrin.ratelimit import APIRateLimit
from syrin.ratelimit.backends import SQLiteRateLimitBackend

backend = SQLiteRateLimitBackend(path="/var/data/ratelimits.db")
manager = DefaultRateLimitManager(
    config=APIRateLimit(rpm=500),
)
manager.set_backend(backend)
manager.load()  # Restore state from disk
```

### Redis

For distributed rate limiting across multiple instances:

```python
from syrin.ratelimit import APIRateLimit
from syrin.ratelimit.backends import RedisRateLimitBackend

backend = RedisRateLimitBackend(
    url="redis://shared-redis:6379",
    prefix="myagent:",
)
manager = DefaultRateLimitManager(config=APIRateLimit(rpm=500))
manager.set_backend(backend)
```

## Configuration Reference

```python
from syrin.ratelimit import APIRateLimit
from syrin.threshold import RateLimitThreshold
from syrin.enums import ThresholdMetric

rate_limit = APIRateLimit(
    rpm=500,                # Requests per minute limit
    tpm=150000,             # Tokens per minute limit
    rpd=10000,              # Requests per day limit
    thresholds=[
        RateLimitThreshold(at=80, action=warn, metric=ThresholdMetric.RPM),
        RateLimitThreshold(at=80, action=warn, metric=ThresholdMetric.TPM),
    ],
    wait_backoff=1.0,       # Seconds to wait on WAIT action
    auto_switch=True,       # Auto-switch model on exceeded
    auto_detect=False,      # Auto-detect limits from model_id
    retry_on_429=True,      # Retry on 429 response
    max_retries=3,          # Max retries on 429
)
```

### Parameter Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rpm` | `int` | `None` | Requests per minute limit |
| `tpm` | `int` | `None` | Tokens per minute limit |
| `rpd` | `int` | `None` | Requests per day limit |
| `thresholds` | `list` | `[]` | Threshold actions |
| `wait_backoff` | `float` | `1.0` | Seconds to wait on WAIT |
| `auto_switch` | `bool` | `True` | Auto-switch model on exceeded |
| `auto_detect` | `bool` | `False` | Auto-detect from model_id |
| `retry_on_429` | `bool` | `True` | Retry on 429 response |
| `max_retries` | `int` | `3` | Max retries on 429 |

**Note**: At least one of `rpm`, `tpm`, or `rpd` must be set (or `auto_detect=True`).

## Getting Statistics

Monitor your rate limit usage:

```python
from syrin.ratelimit import RateLimitStats

stats: RateLimitStats = rate_limit_manager.stats
print(f"RPM: {stats.rpm_used}/{stats.rpm_limit}")
print(f"TPM: {stats.tpm_used}/{stats.tpm_limit}")
print(f"RPD: {stats.rpd_used}/{stats.rpd_limit}")
print(f"Thresholds triggered: {stats.thresholds_triggered}")
```

## Real-World Patterns

### Cost Control

```python
from syrin import Agent, Model, Budget
from syrin.ratelimit import APIRateLimit
from syrin.threshold import RateLimitThreshold
from syrin.enums import ThresholdMetric


def switch_to_cheaper(ctx):
    if ctx.percentage >= 90:
        # Force cheaper model
        agent.model = Model.OpenAI("gpt-3.5-turbo", api_key="your-api-key")
        notify_ops("Switched to gpt-3.5 due to rate limit pressure")


agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    budget=Budget(max_cost=100.00),  # Cap total spend
    rate_limit=APIRateLimit(
        rpm=500,
        thresholds=[
            RateLimitThreshold(at=80, action=switch_to_cheaper, metric=ThresholdMetric.RPM),
        ],
    ),
)
```

### Alert Before Limits

```python
import logging
import slack_sdk

slack = slack_sdk.WebhookClient(os.environ["SLACK_WEBHOOK_URL"])
logger = logging.getLogger(__name__)


def alert_ops(ctx):
    message = f"🚨 Rate limit alert: {ctx.metric} at {ctx.percentage}%"
    slack.send(text=message)
    logger.warning(message)


agent = Agent(
    model=model,
    rate_limit=APIRateLimit(
        rpm=500,
        thresholds=[
            RateLimitThreshold(at=50, action=alert_ops, metric=ThresholdMetric.RPM),
            RateLimitThreshold(at=75, action=alert_ops, metric=ThresholdMetric.RPM),
            RateLimitThreshold(at=90, action=alert_ops, metric=ThresholdMetric.RPM),
        ],
    ),
)
```

### Multi-Tenant Rate Limiting

```python
from syrin.ratelimit import DefaultRateLimitManager, APIRateLimit
from syrin.ratelimit.backends import RedisRateLimitBackend

# Shared Redis backend for multi-tenant
backend = RedisRateLimitBackend(url="redis://redis:6379", prefix="ratelimit:")


def create_tenant_manager(tenant_id: str) -> DefaultRateLimitManager:
    limits = tenant_rate_config[tenant_id]  # Per-tenant limits
    manager = DefaultRateLimitManager(
        config=APIRateLimit(
            rpm=limits["rpm"],
            tpm=limits["tpm"],
        ),
    )
    manager.set_backend(backend, key=f"tenant:{tenant_id}")
    manager.load()
    return manager
```

## Hooks and Events

Rate limit events emit lifecycle hooks:

```python
def on_exceeded(ctx):
    print(f"Rate limit exceeded: {ctx.metric}")
    print(f"  Used: {ctx.used}, Limit: {ctx.limit}")

agent.events.on(Hook.RATELIMIT_EXCEEDED, on_exceeded)

def on_threshold(ctx):
    print(f"Threshold reached: {ctx.percentage}%")

agent.events.on(Hook.RATELIMIT_THRESHOLD, on_threshold)
```

## Comparison with Budget

| Feature | Rate Limiting | Budget |
|---------|--------------|--------|
| Scope | API provider limits | Your spending |
| Units | RPM, TPM, RPD | USD |
| Blocks on | Hard limit | Budget exhausted |
| Use Case | Prevent API throttling | Control costs |

Use both together: rate limiting prevents provider throttling, budget prevents runaway costs.

## Public Rate-Limit Manager API

The rate-limit package also exports `RateLimitManager`, `DefaultRateLimitManager`, `create_rate_limit_manager()`, `get_rate_limit_backend()`, `MemoryRateLimitBackend`, `SQLiteRateLimitBackend`, and `RedisRateLimitBackend` for custom manager and backend wiring.

## See Also

- [Budget](/agent-kit/core/budget) — Spending controls
- [Circuit Breaker](/agent-kit/production/circuit-breaker) — Provider failure protection
- [Debugging: Hooks](/agent-kit/debugging/hooks) — Lifecycle hooks reference
- [Serving: Advanced](/agent-kit/production/serving-advanced) — Production deployment
