"""Rate limit use case: check and record rate limit usage.

Agent delegates to functions here. Public API stays on Agent.
"""

from __future__ import annotations

import logging
from typing import Any

from syrin.types import TokenUsage

_log = logging.getLogger(__name__)


def check_and_apply_rate_limit(agent: Any) -> None:
    """Check rate limits. Raise RuntimeError if exceeded."""
    if agent._rate_limit_manager is None:
        return
    manager = agent._rate_limit_manager
    allowed, reason = manager.check()
    agent._run_report.ratelimits.checks += 1
    if not allowed:
        agent._run_report.ratelimits.exceeded = True
        _log.error("Rate limit exceeded: %s", reason)
        raise RuntimeError(f"Rate limit exceeded: {reason}")


def record_rate_limit_usage(agent: Any, token_usage: TokenUsage) -> None:
    """Record token usage for rate limit tracking."""
    if agent._rate_limit_manager is None:
        return
    agent._rate_limit_manager.record(tokens_used=token_usage.total_tokens)
