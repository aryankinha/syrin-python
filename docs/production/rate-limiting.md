---
title: Rate Limiting
description: Manage API quotas with proactive threshold actions and multi-backend support
weight: 150
---

## Why Rate Limiting Matters

API providers enforce rate limits for good reasons — they protect their infrastructure, ensure fair access for all customers, and help you from accidentally running up a massive bill. Without explicit limits on your end, one misconfigured script or runaway loop can hit the API's hard ceiling, causing throttling errors, or worse, a bill that ends your career.

Syrin's rate limiting tracks your usage in rolling windows and fires threshold actions before you hit provider limits, not after.

## Basic Setup

```python
from syrin import Agent, Model
from syrin.ratelimit import APIRateLimit

agent = Agent(
    model=Model.mock(),
    rate_limit=APIRateLimit(
        rpm=500,     # 500 requests per minute
        tpm=150000,  # 150k tokens per minute
        rpd=10000,   # 10k requests per day
    ),
)
```

At least one of `rpm`, `tpm`, or `rpd` must be set. When a limit is reached, the request is blocked with a `RateLimitExceeded` error.

The tracker uses rolling windows: RPM and TPM track a rolling 60-second window, RPD tracks a rolling 24-hour window. Old entries are pruned automatically.

## Threshold Actions

The real power is in thresholds — actions that fire when you're getting close to a limit, before you actually hit it:

```python
from syrin import Agent, Model
from syrin.ratelimit import APIRateLimit
from syrin.threshold import RateLimitThreshold
from syrin.enums import ThresholdMetric

def warn_ops(ctx):
    print(f"RPM at {ctx.percentage}% ({ctx.current_value}/{ctx.limit_value})")

def switch_model(ctx):
    if ctx.percentage >= 90:
        print("Switching to more efficient model")

agent = Agent(
    model=Model.mock(),
    rate_limit=APIRateLimit(
        rpm=500,
        tpm=150000,
        thresholds=[
            RateLimitThreshold(at=80, action=warn_ops, metric=ThresholdMetric.RPM),
            RateLimitThreshold(at=80, action=warn_ops, metric=ThresholdMetric.TPM),
            RateLimitThreshold(at=90, action=switch_model, metric=ThresholdMetric.TPM),
        ],
    ),
)
```

Threshold actions execute the callback but don't block the request — only hitting the hard limit blocks. Use `at=80` to warn, `at=95` to take emergency action.

You can also trigger within a specific range instead of at a fixed percentage:

```python
RateLimitThreshold(
    at_range=(70, 80),
    action=alert,
    metric=ThresholdMetric.RPM,
)
```

## Auto-Detecting Limits

Let Syrin look up known limits for your model:

```python
from syrin.ratelimit import APIRateLimit

rate_limit = APIRateLimit.auto_detect_for_model("openai/gpt-4o")
print(f"RPM: {rate_limit.rpm}, TPM: {rate_limit.tpm}")
```

Or enable auto-detection directly in the config:

```python
rate_limit = APIRateLimit(auto_detect=True)
```

## Persistence Backends

By default, rate limit state lives in memory and resets when your process restarts. For production deployments that need state across restarts or across multiple instances, choose a backend.

### SQLite — Single-Instance Persistence

```python
from syrin.ratelimit import APIRateLimit, DefaultRateLimitManager
from syrin.ratelimit.backends import SQLiteRateLimitBackend

backend = SQLiteRateLimitBackend(path="/var/data/ratelimits.db")
manager = DefaultRateLimitManager(config=APIRateLimit(rpm=500))
manager.set_backend(backend)
manager.load()  # Restore state from disk
```

### Redis — Distributed Rate Limiting

For multi-instance deployments where you need shared rate limit state across pods:

```python
from syrin.ratelimit import APIRateLimit, DefaultRateLimitManager
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

rate_limit = APIRateLimit(
    rpm=500,             # Requests per minute
    tpm=150000,          # Tokens per minute
    rpd=10000,           # Requests per day
    thresholds=[...],    # Threshold actions (default: [])
    wait_backoff=1.0,    # Seconds to wait when WAIT action triggers
    auto_switch=True,    # Auto-switch model on limit exceeded
    auto_detect=False,   # Auto-detect limits from model ID
    retry_on_429=True,   # Retry automatically on 429 responses
    max_retries=3,       # Max retries on 429
)
```

## Monitoring Usage

Check current usage at any time:

```python
from syrin.ratelimit import RateLimitStats

stats: RateLimitStats = rate_limit_manager.stats
print(f"RPM: {stats.rpm_used}/{stats.rpm_limit}")
print(f"TPM: {stats.tpm_used}/{stats.tpm_limit}")
print(f"RPD: {stats.rpd_used}/{stats.rpd_limit}")
print(f"Thresholds triggered: {stats.thresholds_triggered}")
```

## Production Patterns

### Alert Before Limits Hit

```python
from syrin import Agent, Model
from syrin.ratelimit import APIRateLimit
from syrin.threshold import RateLimitThreshold
from syrin.enums import ThresholdMetric

def alert_ops(ctx):
    # Send to Slack, PagerDuty, etc.
    print(f"Rate limit alert: {ctx.metric} at {ctx.percentage}%")

agent = Agent(
    model=Model.mock(),
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

Per-tenant limits with shared Redis backend:

```python
from syrin.ratelimit import DefaultRateLimitManager, APIRateLimit
from syrin.ratelimit.backends import RedisRateLimitBackend

backend = RedisRateLimitBackend(url="redis://redis:6379", prefix="ratelimit:")

def create_tenant_manager(tenant_id: str, tenant_config: dict) -> DefaultRateLimitManager:
    manager = DefaultRateLimitManager(
        config=APIRateLimit(
            rpm=tenant_config["rpm"],
            tpm=tenant_config["tpm"],
        ),
    )
    manager.set_backend(backend, key=f"tenant:{tenant_id}")
    manager.load()
    return manager
```

## Hooks

Subscribe to rate limit events:

```python
from syrin.enums import Hook

agent.events.on(Hook.RATELIMIT_EXCEEDED, lambda ctx: print(
    f"Rate limit exceeded: {ctx.get('metric')} — {ctx.get('used')}/{ctx.get('limit')}"
))

agent.events.on(Hook.RATELIMIT_THRESHOLD, lambda ctx: print(
    f"Threshold reached: {ctx.get('percentage')}%"
))
```

## Rate Limiting vs Budget

Rate limiting and budget control different things and complement each other.

Rate limiting protects against provider throttling. It tracks requests and tokens against API quotas (RPM, TPM, RPD). When a provider limit is hit, the request is rejected. Use it when you don't want 429 errors.

Budget controls your spending. It tracks costs in USD against your own financial limits. When a budget is exceeded, the run stops (or warns, depending on configuration). Use it when you don't want surprise bills.

Use both together: rate limiting prevents API throttling, budget prevents runaway costs.

## See Also

- [Budget](/core/budget) — Spending controls
- [Budget Callbacks](/core/budget-callbacks) — Budget threshold actions
- [Circuit Breaker](/production/circuit-breaker) — Provider failure protection
- [Hooks Reference](/debugging/hooks-reference) — All lifecycle hooks
