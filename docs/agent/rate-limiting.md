# Rate Limiting

> **Full guide:** For APIRateLimit config, backends, thresholds, and auto-detect, see [Rate Limiting](../ratelimit.md).

Enforce API rate limits (requests and tokens per minute).

## Basic Usage

```python
from syrin import Agent
from syrin.ratelimit import APIRateLimit

agent = Agent(
    model=model,
    rate_limit=APIRateLimit(
        requests_per_minute=60,
        tokens_per_minute=90000,
    ),
)
```

## APIRateLimit

```python
APIRateLimit(
    requests_per_minute=60,
    tokens_per_minute=90000,
    wait_backoff=60.0,
    thresholds=[...],
)
```

| Parameter | Description |
|-----------|-------------|
| `requests_per_minute` | Max requests per minute |
| `tokens_per_minute` | Max tokens per minute |
| `wait_backoff` | Seconds to wait on threshold |
| `thresholds` | Switch/warn/stop at % usage |

## Threshold Actions

At a given percentage of the limit, you can:

- **Switch model** — Use a cheaper model
- **Wait** — Sleep before retrying
- **Warn** — Log and continue
- **Stop** — Raise and stop

## Properties

- `agent.rate_limit` — Config
- `agent.rate_limit_stats` — Usage stats

## Report

`response.report.ratelimits`:

- `checks` — Number of checks
- `exceeded` — Limit exceeded
- `throttles` — Throttle events

## See Also

- [Rate Limiting](../ratelimit.md) — Full guide, backends, thresholds
