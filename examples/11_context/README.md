# Context management examples

Syrin gives you **full visibility and control** over the context window: what goes in, why, and how much.

## Run the examples

```bash
# Tour: basics, snapshot, manual compaction, thresholds, custom manager
python -m examples.11_context.context_management

# Best example: full snapshot & breakdown (capacity, components, provenance, rot risk, export)
python -m examples.11_context.context_snapshot_demo

# Best example: thresholds and compaction (react when context fills up)
python -m examples.11_context.context_thresholds_compaction_demo
```

## What each example shows

| Example | What you see |
|--------|----------------|
| **context_management** | Short tour: `Context(max_tokens=, thresholds=)`, stats after `response()`, snapshot breakdown, manual `MiddleOutTruncator` / `ContextCompactor`, threshold actions, custom `ContextManager`. |
| **context_snapshot_demo** | Full **context snapshot**: capacity (tokens used/max/utilization), **breakdown** (system, tools, memory, messages), **why_included**, **message_preview** (role, snippet, tokens, source), **provenance**, **context_rot_risk**, and **to_dict()** for dashboards. |
| **context_thresholds_compaction_demo** | Small context window + threshold at 50% that runs **compaction**; **context.threshold** and **context.compact** events; **stats.compacted** and **compact_method** in snapshot. |

## Key APIs

- **`agent.context_stats`** — Total tokens, utilization, **breakdown** (after prepare), compacted, compact_method.
- **`agent.context.snapshot()`** — Full view: breakdown, message_preview, provenance, why_included, context_rot_risk; **`snapshot.to_dict()`** for export.
- **`Context(max_tokens=, reserve=, thresholds=[...])`** — Window size and actions at utilization %.
- **`ContextThreshold(at=N, action=lambda evt: evt.compact())`** — Run compaction when usage hits N%.
