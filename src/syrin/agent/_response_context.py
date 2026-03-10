"""Response context use case: attach context to Response, record conversation turn.

Agent delegates to functions here. Public API stays on Agent.
"""

from __future__ import annotations

from typing import Any

from syrin.response import Response


def with_context_on_response(agent: Any, r: Response[str]) -> Response[str]:
    """Attach per-call context_stats and context to a Response."""
    r.context_stats = getattr(agent._context, "stats", None)
    r.context = getattr(agent, "_call_context", None) or (
        getattr(agent._context, "context", None) if hasattr(agent._context, "context") else None
    )
    return r


def record_conversation_turn(
    agent: Any,
    user_input: str | list[dict[str, Any]],
    assistant_content: str,
) -> None:
    """Append a user/assistant turn to memory for next context."""
    if agent._persistent_memory is None:
        return
    from syrin.agent._context_builder import _user_input_to_search_str

    text = _user_input_to_search_str(user_input)
    agent._persistent_memory.add_conversation_segment(text, role="user")
    agent._persistent_memory.add_conversation_segment(assistant_content or "", role="assistant")
    ctx_config = getattr(agent._context, "context", None)
    if (
        ctx_config is not None
        and getattr(ctx_config, "store_output_chunks", False)
        and (assistant_content or "").strip()
    ):
        strat = getattr(ctx_config, "output_chunk_strategy", None)
        strat_val = strat.value if strat is not None and hasattr(strat, "value") else "paragraph"
        size = getattr(ctx_config, "output_chunk_size", 300)
        agent._persistent_memory.add_output_chunks(
            assistant_content,
            strategy=strat_val,
            chunk_size=max(1, size),
        )
