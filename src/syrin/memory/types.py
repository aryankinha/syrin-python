"""Memory type classes for Core, Episodic, Semantic, and Procedural memory."""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict, Unpack

from syrin.enums import MemoryScope, MemoryType
from syrin.memory.config import MemoryEntry


class MemoryEntryKwargs(TypedDict, total=False):
    """Optional kwargs for MemoryEntry subclasses."""

    source: str | None
    created_at: datetime
    last_accessed: datetime | None
    access_count: int
    valid_from: datetime | None
    valid_until: datetime | None
    keywords: list[str]
    related_ids: list[str]
    supersedes: str | None
    metadata: dict[str, object]


class CoreMemory(MemoryEntry):  # type: ignore[explicit-any]
    """Core memory - persistent facts about the agent/user.

    Core memories are high-importance, long-lasting facts that should
    rarely decay. Examples: user name, preferences, identity.
    """

    def __init__(
        self,
        id: str,
        content: str,
        importance: float = 0.9,
        scope: MemoryScope = MemoryScope.USER,
        **kwargs: Unpack[MemoryEntryKwargs],
    ) -> None:
        super().__init__(
            id=id,
            content=content,
            type=MemoryType.CORE,
            importance=min(importance, 0.9),  # Core defaults high
            scope=scope,
            **kwargs,
        )


class EpisodicMemory(MemoryEntry):  # type: ignore[explicit-any]
    """Episodic memory - specific events and experiences.

    Episodic memories capture specific moments, conversations, or events.
    They decay over time unless reinforced. Examples: what happened yesterday.
    """

    def __init__(
        self,
        id: str,
        content: str,
        importance: float = 0.7,
        scope: MemoryScope = MemoryScope.USER,
        **kwargs: Unpack[MemoryEntryKwargs],
    ) -> None:
        super().__init__(
            id=id,
            content=content,
            type=MemoryType.EPISODIC,
            importance=importance,
            scope=scope,
            **kwargs,
        )


class SemanticMemory(MemoryEntry):  # type: ignore[explicit-any]
    """Semantic memory - facts and knowledge.

    Semantic memories store factual knowledge that can be recalled
    regardless of when it was learned. Examples: facts, definitions.
    """

    def __init__(
        self,
        id: str,
        content: str,
        importance: float = 0.8,
        scope: MemoryScope = MemoryScope.USER,
        **kwargs: Unpack[MemoryEntryKwargs],
    ) -> None:
        super().__init__(
            id=id,
            content=content,
            type=MemoryType.SEMANTIC,
            importance=importance,
            scope=scope,
            **kwargs,
        )


class ProceduralMemory(MemoryEntry):  # type: ignore[explicit-any]
    """Procedural memory - how-to knowledge and skills.

    Procedural memories store instructions and procedures. They should
    decay slowly as they represent learned skills. Examples: how to make coffee.
    """

    def __init__(
        self,
        id: str,
        content: str,
        importance: float = 0.85,
        scope: MemoryScope = MemoryScope.USER,
        **kwargs: Unpack[MemoryEntryKwargs],
    ) -> None:
        super().__init__(
            id=id,
            content=content,
            type=MemoryType.PROCEDURAL,
            importance=importance,
            scope=scope,
            **kwargs,
        )


def create_memory(
    memory_type: MemoryType,
    id: str,
    content: str,
    importance: float | None = None,
    **kwargs: Unpack[MemoryEntryKwargs],
) -> MemoryEntry:
    """Factory function to create memory entries by type.

    Args:
        memory_type: The type of memory to create
        id: Unique identifier for the memory
        content: The memory content
        importance: Optional importance (type-specific default if not provided)
        **kwargs: Additional fields for MemoryEntry

    Returns:
        A MemoryEntry of the appropriate type

    Example:
        >>> mem = create_memory(MemoryType.CORE, "user-name", "My name is John")
        >>> assert mem.type == MemoryType.CORE
    """
    defaults = {
        MemoryType.CORE: 0.9,
        MemoryType.EPISODIC: 0.7,
        MemoryType.SEMANTIC: 0.8,
        MemoryType.PROCEDURAL: 0.85,
    }

    imp = importance if importance is not None else defaults.get(memory_type, 0.5)

    if memory_type == MemoryType.CORE:
        return CoreMemory(id=id, content=content, importance=imp, **kwargs)
    elif memory_type == MemoryType.EPISODIC:
        return EpisodicMemory(id=id, content=content, importance=imp, **kwargs)
    elif memory_type == MemoryType.SEMANTIC:
        return SemanticMemory(id=id, content=content, importance=imp, **kwargs)
    elif memory_type == MemoryType.PROCEDURAL:
        return ProceduralMemory(id=id, content=content, importance=imp, **kwargs)
    else:
        return MemoryEntry(id=id, content=content, type=memory_type, importance=imp, **kwargs)


__all__ = [
    "CoreMemory",
    "EpisodicMemory",
    "MemoryEntryKwargs",
    "ProceduralMemory",
    "SemanticMemory",
    "create_memory",
]
