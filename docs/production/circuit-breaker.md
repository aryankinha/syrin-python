---
title: Circuit Breaker
description: Prevent cascading failures when LLM providers go down
weight: 140
---

## When the Provider Goes Silent

Your agent is handling 1,000 requests per minute. Suddenly, the LLM provider starts timing out. Each request waits 30 seconds before failing. Your users experience slow responses, then timeouts, then frustration.

Without protection, one provider failure cascades through your entire system. Requests pile up. Resources exhaust. Recovery becomes harder.

The circuit breaker pattern exists to prevent this. When failures exceed a threshold, the circuit "opens" and fails fast—immediately returning an error instead of waiting. This lets the system recover and protects downstream components.

## The Problem

LLM providers fail in real ways:
- **Rate limits** — Too many requests, provider rejects them
- **Outages** — Provider goes down entirely
- **Latency spikes** — Responses take minutes instead of milliseconds
- **Partial failures** — Some models work, others don't

Without protection:
- Requests queue up waiting for failed providers
- Memory and connections exhaust
- Recovery takes longer because the provider is overloaded
- Your users experience cascading timeouts

## The Solution

Syrin's circuit breaker monitors LLM calls and trips when failures exceed a threshold:

```python
from syrin import Agent, CircuitBreaker, Model

primary = Model.OpenAI("gpt-4o", api_key="your-api-key")
fallback = Model.Almock()  # Fallback when circuit opens

breaker = CircuitBreaker(
    failure_threshold=5,      # Trip after 5 consecutive failures
    recovery_timeout=60,      # Try again after 60 seconds
    fallback=fallback,       # Use this when circuit is open
)


class ResilientAgent(Agent):
    model = primary
    circuit_breaker = breaker
```

**What just happened**: The circuit breaker monitors the primary model. After 5 consecutive failures, it trips open. New requests fail immediately (using the fallback) instead of waiting for the broken provider.

## How the Circuit Breaker Works

The circuit breaker has three states:

```
CLOSED ──────► OPEN ──────► HALF_OPEN ──────► CLOSED
   │             │              │                │
   │             │              │                │
   ▼             ▼              ▼                ▼
 Normal      Fail fast       Test if          Recover
 operation   (blocked)       provider         (reset)
                           is healthy
```

### CLOSED State (Normal)

The circuit is closed, allowing requests through normally:
- Every request passes through to the provider
- Failures are counted
- When failures reach `failure_threshold`, the circuit opens

### OPEN State (Failing Fast)

The circuit is open, blocking requests:
- Requests immediately fail or use the fallback
- No calls are made to the provider
- After `recovery_timeout` seconds, the circuit moves to HALF_OPEN

### HALF_OPEN State (Testing)

The circuit is testing if the provider recovered:
- One (or `half_open_max`) request passes through
- If it succeeds, the circuit closes (resets)
- If it fails, the circuit opens again

## Configuration

```python
from syrin import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,      # Trip after N consecutive failures
    recovery_timeout=60,      # Wait N seconds before testing recovery
    half_open_max=1,         # Allow N requests in HALF_OPEN state
    fallback="I'm temporarily unavailable. Please try again.",  # String fallback
    on_trip=my_callback,     # Called when circuit trips
)
```

### Parameter Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `failure_threshold` | `int` | `5` | Failures before trip (min: 1) |
| `recovery_timeout` | `int` | `60` | Seconds before retry (min: 1) |
| `half_open_max` | `int` | `1` | Requests allowed in HALF_OPEN |
| `fallback` | `str \| Model` | `None` | Response when open |
| `on_trip` | `Callable` | `None` | Callback when circuit trips |

## Fallback Options

### String Fallback

```python
breaker = CircuitBreaker(
    failure_threshold=3,
    fallback="Service temporarily unavailable. Please try again later.",
)
```

Simple but static. Users get the same message every time.

### Model Fallback

```python
cheaper_model = Model.OpenAI("gpt-3.5-turbo", api_key="your-api-key")

breaker = CircuitBreaker(
    failure_threshold=5,
    fallback=cheaper_model,  # Route to cheaper model when primary fails
)
```

When the circuit opens, requests go to the fallback model. This provides degraded but functional service.

### Custom Fallback Logic

```python
def handle_trip(state):
    # Send alert to monitoring
    slack.notify("Circuit breaker tripped!")
    # Log for debugging
    logger.warning(f"Circuit open: {state.failures} failures")


breaker = CircuitBreaker(
    failure_threshold=5,
    fallback="Please try again in a few minutes.",
    on_trip=handle_trip,
)
```

## Observability with Hooks

Monitor circuit breaker state changes:

```python
from syrin import Agent, CircuitBreaker, Hook


class MonitoredAgent(Agent):
    model = primary
    circuit_breaker = CircuitBreaker(
        failure_threshold=3,
        fallback=fallback,
    )


agent = MonitoredAgent()


def on_trip(ctx):
    print(f"Circuit tripped! Failures: {ctx.failures}")
    print(f"State: {ctx.state}")
    # Send to your monitoring system

agent.events.on(Hook.CIRCUIT_TRIP, on_trip)

def on_reset(ctx):
    print("Circuit reset - provider recovered!")
    # Clear alerts

agent.events.on(Hook.CIRCUIT_RESET, on_reset)
```

### Hook Reference

| Hook | When | Context |
|------|------|---------|
| `CIRCUIT_TRIP` | Circuit opens | `state`, `failures`, `reason` |
| `CIRCUIT_RESET` | Circuit closes | `state` |

## Checking Circuit State

```python
from syrin.enums import CircuitState

state = breaker.get_state()
print(f"State: {state.state}")           # CLOSED, OPEN, or HALF_OPEN
print(f"Failures: {state.failures}")     # Consecutive failures
print(f"Last failure: {state.last_failure_time}")
print(f"Last success: {state.last_success_time}")
print(f"Half-open attempts: {state.half_open_attempts}")
```

### State Properties

```python
if breaker.is_open():
    print("Circuit is open - using fallback")
elif breaker.state == CircuitState.HALF_OPEN:
    print("Testing recovery...")
else:
    print("Normal operation")
```

## Real-World Patterns

### Graceful Degradation

```python
from syrin import Agent, Model, CircuitBreaker

primary = Model.OpenAI("gpt-4o", api_key="your-api-key")
fallback = Model.OpenAI("gpt-3.5-turbo", api_key="your-api-key")  # Cheaper backup

class DegradingAgent(Agent):
    model = primary
    circuit_breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=60,
        fallback=fallback,
        on_trip=lambda s: send_alert("GPT-4 degraded, using GPT-3.5"),
    )
```

### Multiple Providers

```python
from syrin import Agent, Model, CircuitBreaker
from syrin.enums import CircuitState

primary = Model.OpenAI("gpt-4o", api_key="your-api-key")
backup = Model.Anthropic("claude-3-opus", api_key="your-api-key")

breaker_primary = CircuitBreaker(failure_threshold=5, fallback=backup)
breaker_backup = CircuitBreaker(failure_threshold=3, fallback="Service unavailable")


class MultiProviderAgent(Agent):
    model = primary
    circuit_breaker = breaker_primary


agent = MultiProviderAgent()

# Check which circuit is open
if breaker_primary.is_open():
    # Primary down, check backup
    if breaker_backup.is_open():
        print("All providers down!")
    else:
        print("Using backup provider")
```

### Testing Circuit Breaker Behavior

```python
import time

breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=5,  # 5 seconds for testing
    fallback="Fallback response",
)

# Simulate failures
for i in range(3):
    breaker.record_failure(Exception("Simulated failure"))
    print(f"After failure {i+1}: {breaker.state}")

print(f"Circuit is open: {breaker.is_open()}")

# Wait for recovery timeout
time.sleep(6)

# Should now be HALF_OPEN
print(f"After timeout: {breaker.state}")

# Successful request
breaker.record_success()
print(f"After success: {breaker.state}")  # CLOSED
```

## Integration with Serving

The circuit breaker works seamlessly with HTTP serving:

```python
from syrin import Agent, Model, CircuitBreaker
from syrin.serve import ServeConfig

primary = Model.OpenAI("gpt-4o", api_key="your-api-key")
fallback = Model.Almock()  # Mock fallback for demo

class ProductionAgent(Agent):
    model = primary
    circuit_breaker = CircuitBreaker(
        failure_threshold=10,
        recovery_timeout=120,
        fallback=fallback,
    )


agent = ProductionAgent()

# Monitor the health endpoint
def alert_trip(ctx):
    # Update health check to show degraded
    pass

agent.events.on(Hook.CIRCUIT_TRIP, alert_trip)

agent.serve(port=8000)
```

## Best Practices

### Setting Thresholds

| Scenario | failure_threshold | recovery_timeout |
|----------|------------------|------------------|
| Sensitive system | 2-3 | 30-60 |
| Normal system | 5 | 60-120 |
| Tolerant system | 10 | 120-300 |

**Rule of thumb**: Set `failure_threshold` based on how many failures indicate a real problem. Set `recovery_timeout` based on how long the provider typically takes to recover.

### Fallback Design

1. **Don't return garbage**: Return something useful
2. **Log everything**: You need to know when fallbacks are used
3. **Alert on fallback**: Users should know service is degraded
4. **Test fallbacks**: Regularly verify fallbacks work

### Monitoring

Always monitor:
- Circuit state changes
- Fallback usage frequency
- Recovery success rate
- Time spent in each state

## See Also

- [Rate Limiting](/agent-kit/production/rate-limiting) — Manage API quotas
- [Error Handling](/agent-kit/agent/error-handling) — Handle failures gracefully
- [Serving: HTTP API](/agent-kit/production/serving-http) — HTTP deployment
- [Debugging: Hooks](/agent-kit/debugging/hooks) — Lifecycle hooks reference
