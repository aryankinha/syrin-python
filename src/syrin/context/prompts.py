"""Default prompts for context compaction (summarization). Overridable via Summarizer or Context."""

DEFAULT_COMPACTION_SYSTEM_PROMPT = (
    "You are a summarization assistant. Your task is to condense conversation history "
    "into a concise summary that preserves key facts, decisions, and context needed for the next turn. "
    "Output only the summary text, no preamble."
)

DEFAULT_COMPACTION_USER_TEMPLATE = (
    "Summarize the following conversation, preserving key facts and decisions:\n\n{messages}"
)

__all__ = [
    "DEFAULT_COMPACTION_SYSTEM_PROMPT",
    "DEFAULT_COMPACTION_USER_TEMPLATE",
]
