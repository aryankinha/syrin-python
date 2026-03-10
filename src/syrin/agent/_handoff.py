"""Handoff use case: delegate task to another agent.

Agent delegates to handoff_impl. Public API stays on Agent.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from syrin.enums import Hook
from syrin.events import EventContext
from syrin.exceptions import HandoffBlockedError, HandoffRetryRequested, ValidationError
from syrin.memory import Memory
from syrin.memory.backends import get_backend
from syrin.response import Response

if TYPE_CHECKING:
    from syrin.agent import Agent

_log = logging.getLogger(__name__)


def handoff(
    agent: Any,
    target_agent: type[Agent],
    task: str,
    *,
    transfer_context: bool = True,
    transfer_budget: bool = False,
) -> Response[str]:
    """Delegate task to target agent and return its response.

    Transfers memory and optionally budget. Emits HANDOFF_START, HANDOFF_END, HANDOFF_BLOCKED.
    """
    if target_agent is None or not isinstance(target_agent, type):
        raise ValidationError(
            "handoff target_agent must be Agent class, not None or instance",
            last_error=None,
        )
    if task is None or (isinstance(task, str) and not task.strip()):
        raise ValidationError("handoff task must be non-empty str", last_error=None)

    mem_count = 0
    if transfer_context and agent._memory_backend is not None:
        mem_count = len(agent._memory_backend.list())

    src_name = type(agent).__name__
    tgt_name = target_agent.__name__

    from syrin.context.snapshot import ContextSnapshot

    handoff_context = (
        agent._context.snapshot() if hasattr(agent._context, "snapshot") else ContextSnapshot()
    )

    start_ctx = EventContext(
        {
            "source_agent": src_name,
            "target_agent": tgt_name,
            "task": task,
            "mem_count": mem_count,
            "transfer_context": transfer_context,
            "transfer_budget": transfer_budget,
            "handoff_context": handoff_context,
        }
    )

    try:
        agent._emit_event(Hook.HANDOFF_START, start_ctx)
    except HandoffBlockedError as e:
        blocked_ctx = EventContext(
            {
                "source_agent": src_name,
                "target_agent": tgt_name,
                "task": task,
                "reason": str(e),
                "handoff_context": handoff_context,
            }
        )
        agent._emit_event(Hook.HANDOFF_BLOCKED, blocked_ctx)
        raise

    target = target_agent()

    if transfer_budget and agent._budget:
        target._budget = agent._budget
        target._budget_tracker = agent._budget_tracker

    if transfer_context:
        if agent._memory_backend is None:
            _log.warning(
                "handoff: transfer_context=True but source agent has no memory backend. "
                "Did you set memory=Memory() on the source agent?"
            )
        else:
            memories = agent._memory_backend.list()
            if memories:
                if target._memory_backend is None:
                    mem_config = Memory(top_k=10, relevance_threshold=0.7)
                    target._persistent_memory = mem_config
                    target._memory_backend = get_backend(
                        mem_config.backend, **mem_config._backend_kwargs()
                    )
                for mem in memories:
                    target.remember(mem.content, memory_type=mem.type, importance=mem.importance)
                _log.debug("handoff: transferred %d memories to target agent", len(memories))

    t0 = time.perf_counter()
    try:
        resp = target.response(task)
    except HandoffRetryRequested:
        raise
    duration = time.perf_counter() - t0

    preview_len = 200
    preview = (resp.content or "")[:preview_len]
    if len(resp.content or "") > preview_len:
        preview = preview + "..."

    end_ctx = EventContext(
        {
            "source_agent": src_name,
            "target_agent": tgt_name,
            "task": task,
            "cost": resp.cost,
            "duration": duration,
            "response_preview": preview,
        }
    )
    agent._emit_event(Hook.HANDOFF_END, end_ctx)

    return resp
