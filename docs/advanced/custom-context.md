---
title: Custom Context
description: Implement custom context management strategies for specialized token handling
weight: 220
---

## Default Context Isn't Always Enough

Syrin's default context manager handles token counting, compaction, and thresholds. But what if you need:

- Custom token counting (different encoding, compression)
- Specialized compaction strategies (summarize by topic, keep certain messages)
- Integration with external context stores
- Priority-based message selection

**The challenge:**
- Long conversations bloat context
- Generic strategies miss domain-specific patterns
- External context stores need custom integration
- You need full control over what gets sent to the LLM

**The solution:** Implement the `ContextManager` protocol to create custom context strategies.

## The ContextManager Protocol

```python
from syrin.context import ContextManager, ContextPayload, CompactionResult
from syrin.context.config import Context, ContextWindowCapacity

class ContextManager(Protocol):
    """Protocol for custom context management."""
    
    def prepare(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict],
        memory_context: str,
        capacity: ContextWindowCapacity,
        context: Context | None = None,
    ) -> ContextPayload:
        """Prepare context for LLM call."""
        ...
    
    def on_compact(self, event: CompactionResult) -> None:
        """Called after compaction."""
        ...
```

### ContextPayload

The return value from `prepare()`:

```python
@dataclass
class ContextPayload:
    messages: list[dict]      # Messages ready for the model
    system_prompt: str         # System prompt
    tools: list[dict]          # Tool definitions
    tokens: int                # Total token count
```

## Example: Recent-Only Context Manager

Keep only the last N messages regardless of token count:

```python
from dataclasses import dataclass
from typing import Any, Protocol

from syrin.context import ContextManager, ContextPayload
from syrin.context.config import ContextWindowCapacity


class RecentOnlyManager:
    """Keep only the last N messages. Simple but effective."""
    
    def __init__(self, keep: int = 10):
        self._keep = keep
    
    def prepare(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        memory_context: str,
        capacity: ContextWindowCapacity,
        context: Any | None = None,
    ) -> ContextPayload:
        # Keep only the last N messages
        recent = messages[-self._keep:] if len(messages) > self._keep else messages
        
        return ContextPayload(
            messages=recent,
            system_prompt=system_prompt,
            tools=tools,
            tokens=0,  # Not counting tokens here
        )
    
    def on_compact(self, event) -> None:
        pass  # No-op for this simple manager


# Use it
agent = Agent(
    model=model,
    config=AgentConfig(context=RecentOnlyManager(keep=5)),
)
```

## Example: Priority-Based Context

Prioritize messages by importance:

```python
from dataclasses import dataclass
from typing import Any

from syrin.context import ContextManager, ContextPayload
from syrin.context.config import ContextWindowCapacity


class PriorityContextManager:
    """Select messages by priority when context is limited."""
    
    def __init__(self, max_tokens: int = 8000):
        self._max_tokens = max_tokens
        self._token_counter = None  # Initialize lazily
    
    def _count_tokens(self, text: str) -> int:
        # Simple word-based estimation (replace with real tokenizer)
        return len(text.split()) * 1.3
    
    def prepare(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        memory_context: str,
        capacity: ContextWindowCapacity,
        context: Any | None = None,
    ) -> ContextPayload:
        # Build messages in priority order
        prioritized = []
        current_tokens = 0
        
        # Priority 1: System prompt (always first)
        system_tokens = self._count_tokens(system_prompt)
        
        # Priority 2: Recent messages (last 3)
        recent = messages[-3:] if len(messages) > 3 else messages
        
        # Priority 3: Tool results (high priority)
        tool_results = [m for m in messages if m.get("role") == "tool"]
        
        # Priority 4: Older messages (in order)
        older = messages[:-3] if len(messages) > 3 else []
        
        # Build final list within token budget
        for msg_list in [recent, tool_results, older]:
            for msg in msg_list:
                content = msg.get("content", "")
                msg_tokens = self._count_tokens(str(content))
                
                if current_tokens + msg_tokens + system_tokens <= self._max_tokens:
                    prioritized.append(msg)
                    current_tokens += msg_tokens
        
        return ContextPayload(
            messages=prioritized,
            system_prompt=system_prompt,
            tools=tools,
            tokens=int(current_tokens + system_tokens),
        )
    
    def on_compact(self, event) -> None:
        pass
```

## Example: Topic-Aware Compaction

Summarize messages by topic:

```python
from dataclasses import dataclass, field
from typing import Any

from syrin.context import ContextManager, ContextPayload, CompactionResult
from syrin.context.config import ContextWindowCapacity
from syrin.context.compactors import ContextCompactor, CompactionResult as SyrinCompactionResult


class TopicAwareCompactor:
    """Summarize messages while preserving topic boundaries."""
    
    def __init__(self, model):
        self._model = model
    
    def compact(
        self,
        messages: list[dict[str, Any]],
        available_tokens: int,
    ) -> SyrinCompactionResult:
        # Group messages by topic (simple heuristic: consecutive messages)
        topics = self._group_by_topic(messages)
        
        summarized = []
        total_tokens = 0
        
        for topic_messages in topics:
            topic_tokens = sum(
                self._estimate_tokens(m) for m in topic_messages
            )
            
            if total_tokens + topic_tokens <= available_tokens:
                summarized.extend(topic_messages)
                total_tokens += topic_tokens
            else:
                # Summarize this topic
                summary = self._summarize_topic(topic_messages)
                summarized.append(summary)
        
        return SyrinCompactionResult(
            messages=summarized,
            method="topic_aware_summarize",
            tokens_before=total_tokens,
            tokens_after=self._estimate_tokens_list(summarized),
        )
    
    def _group_by_topic(self, messages: list[dict]) -> list[list[dict]]:
        # Simple grouping: every 5 messages = one topic
        topics = []
        for i in range(0, len(messages), 5):
            topics.append(messages[i:i + 5])
        return topics
    
    def _summarize_topic(self, messages: list[dict]) -> dict:
        # Call LLM to summarize
        prompt = f"Summarize these messages:\n{messages}"
        response = self._model.complete([{"role": "user", "content": prompt}])
        return {
            "role": "system",
            "content": f"[Summary] {response.content}"
        }
    
    def _estimate_tokens(self, msg: dict) -> int:
        return len(str(msg.get("content", "")).split()) * 1.3
    
    def _estimate_tokens_list(self, messages: list[dict]) -> int:
        return sum(self._estimate_tokens(m) for m in messages)


class TopicAwareManager:
    """Context manager with topic-aware compaction."""
    
    def __init__(self, model, max_tokens: int = 80000):
        self._compactor = TopicAwareCompactor(model)
        self._max_tokens = max_tokens
    
    def prepare(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        memory_context: str,
        capacity: ContextWindowCapacity,
        context: Any | None = None,
    ) -> ContextPayload:
        # Check if compaction needed
        total_tokens = self._count_messages(messages)
        
        if total_tokens > self._max_tokens:
            result = self._compactor.compact(messages, self._max_tokens)
            messages = result.messages
            total_tokens = result.tokens_after
        
        return ContextPayload(
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
            tokens=total_tokens,
        )
    
    def _count_messages(self, messages: list[dict]) -> int:
        return sum(len(str(m.get("content", "")).split()) * 1.3 for m in messages)
    
    def on_compact(self, event: CompactionResult) -> None:
        print(f"Compacted with method: {event.method}")
```

## Example: External Context Store Integration

Pull context from an external vector store:

```python
from dataclasses import dataclass
from typing import Any

from syrin.context import ContextManager, ContextPayload
from syrin.context.config import ContextWindowCapacity


class ExternalContextManager:
    """Retrieve relevant context from external vector store."""
    
    def __init__(self, vector_store, embedding_model):
        self._store = vector_store
        self._embedding = embedding_model
    
    def prepare(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        memory_context: str,
        capacity: ContextWindowCapacity,
        context: Any | None = None,
    ) -> ContextPayload:
        # Get the current user message
        current_msg = messages[-1] if messages else {}
        user_content = current_msg.get("content", "")
        
        # Retrieve relevant context from vector store
        query_embedding = self._embedding.embed(user_content)
        relevant_context = self._store.search(
            query_embedding,
            top_k=5,
            threshold=0.7,
        )
        
        # Build context block
        context_block = self._format_context(relevant_context)
        
        # Prepend to system prompt
        enhanced_system = f"{system_prompt}\n\n[Relevant Context]\n{context_block}"
        
        # Keep recent conversation history
        recent_messages = messages[-6:] if len(messages) > 6 else messages
        
        return ContextPayload(
            messages=recent_messages,
            system_prompt=enhanced_system,
            tools=tools,
            tokens=self._estimate_tokens(recent_messages, enhanced_system),
        )
    
    def _format_context(self, results: list) -> str:
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(f"[{i}] {result.content}")
            if result.metadata:
                formatted.append(f"    Source: {result.metadata.get('source', 'Unknown')}")
        return "\n".join(formatted)
    
    def _estimate_tokens(self, messages: list[dict], system: str) -> int:
        text = system + "".join(str(m.get("content", "")) for m in messages)
        return len(text.split()) * 1.3
    
    def on_compact(self, event) -> None:
        pass
```

## Using Custom Managers

Pass your custom manager to the agent:

```python
from syrin import Agent, AgentConfig

agent = Agent(
    model=model,
    config=AgentConfig(
        context=RecentOnlyManager(keep=10)
    ),
)

# Or with the Context configuration (for default manager with overrides)
from syrin import Context
from syrin.context import ContextThreshold

agent = Agent(
    model=model,
    context=Context(
        max_tokens=80000,
        thresholds=[
            ContextThreshold(at=75, action=lambda ctx: ctx.compact()),
        ],
    ),
)
```

## DefaultContextManager Reference

The built-in `DefaultContextManager` handles everything the default `Context` config provides. Key methods:

```python
@dataclass
class DefaultContextManager:
    context: Context                           # Configuration
    _counter: TokenCounter                    # Token counting
    _compactor: ContextCompactorProtocol      # Compaction strategy
    _stats: ContextStats                      # Statistics
    
    def prepare(...) -> ContextPayload        # Main entry point
    def snapshot() -> ContextSnapshot         # Full context view
    def compact() -> None                     # Request compaction
    def get_map() -> ContextMap               # Persistent context map
    def update_map(...) -> None               # Update context map
    def stats: ContextStats                   # Current statistics
```

### Extending DefaultContextManager

Extend the default manager to customize specific parts:

```python
from syrin.context import DefaultContextManager, Context


class EnhancedManager(DefaultContextManager):
    """Custom manager extending the default."""
    
    def prepare(self, *args, **kwargs) -> ContextPayload:
        # Add custom logic before
        print(f"Preparing with {len(args[0])} messages")
        
        result = super().prepare(*args, **kwargs)
        
        # Add custom logic after
        print(f"Prepared {len(result.messages)} messages, {result.tokens} tokens")
        
        return result
```

## Compactor Interface

For custom compaction strategies:

```python
from syrin.context.compactors import (
    Compactor,
    CompactionResult,
    MiddleOutTruncator,
    Summarizer,
)


class ContextCompactorProtocol(Protocol):
    """Protocol for compaction strategies."""
    
    def compact(
        self,
        messages: list[dict[str, Any]],
        available_tokens: int,
    ) -> CompactionResult:
        """Compact messages to fit in available_tokens."""
        ...


@dataclass
class CompactionResult:
    messages: list[dict[str, Any]]
    method: str                    # "middle_out_truncate", "summarize", etc.
    tokens_before: int
    tokens_after: int
```

### Built-in Compactors

```python
from syrin.context.compactors import (
    MiddleOutTruncator,
    Summarizer,
    ContextCompactor,
)

# Middle-out: keep start and end, truncate middle
truncator = MiddleOutTruncator()

# Summarize: use LLM to summarize older messages
summarizer = Summarizer(
    system_prompt="Summarize concisely...",
    model=gpt4_model,
)

# Combined: summarize if very long, else truncate
compactor = ContextCompactor(
    compaction_model=gpt4_model,  # Optional LLM for summarization
)
```

## Observability Integration

Custom managers integrate with hooks and tracing:

```python
def my_manager():
    manager = MyCustomManager()
    manager.set_emit_fn(emit_fn)   # For hooks
    manager.set_tracer(tracer)      # For tracing
    return manager

# Hooks fired automatically:
# - context.prepare: when prepare() is called
# - context.compact: when compaction runs
# - context.threshold: when threshold triggers
```

## ContextSnapshot: Full Visibility

The default manager provides complete context snapshots:

```python
agent = Agent(model=model, context=Context(max_tokens=80000))

result = agent.run("Hello!")

# Full snapshot
snap = agent.context.snapshot()
print(f"Tokens: {snap.total_tokens}/{snap.max_tokens}")
print(f"Utilization: {snap.utilization_pct:.1f}%")
print(f"Context rot risk: {snap.context_rot_risk}")

# Message breakdown
for preview in snap.message_preview:
    print(f"{preview.role}: {preview.content_snippet[:50]}...")

# Why each segment was included
for reason in snap.why_included:
    print(f"  {reason}")
```

## What's Next?

- [Dependency Injection](/advanced/dependency-injection) — Inject dependencies into tools
- [Event Bus](/advanced/event-bus) — Domain events and handlers
- [Template Engine](/advanced/template-engine) — Structured generation
- [Testing](/advanced/testing) — Test custom context managers

## See Also

- [Context Overview](/core/context) — Default context management
- [Context Compaction](/core/context-compaction) — Compaction strategies
- [Token Counting](/core/context) — Token counting internals
