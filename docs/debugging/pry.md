---
title: Pry — Interactive Agent Debugger
description: Step through agent execution, inspect state at any point, and set breakpoints anywhere — like byebug, but for AI agents.
weight: 175
---

## Pry

Pry is syrin's interactive debugger, inspired by Ruby's byebug. It gives you a live two-panel TUI that streams every agent event in real time, lets you navigate to any event for full detail, and — critically — lets you **pause execution at any point** and inspect the full agent state before deciding to continue.

---

## Quickstart

```python
from syrin import Agent, Model
from syrin.debug import Pry

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="..."))

pry = Pry()
pry.attach(agent)
agent.run("What is the capital of France?")
# TUI stays open after the run — press q to exit
```

**Context manager** (recommended — keeps TUI open until you press `q`):

```python
with Pry() as pry:
    pry.attach(agent)
    pry.run(agent.run, "Hello")   # runs agent in a background thread
    pry.wait()                    # hold TUI open — q to exit
```

**Attach multiple agents** — events from all agents stream into the same panel, tagged by agent name:

```python
with Pry() as pry:
    pry.attach(researcher).attach(writer)
    pry.run(researcher.run, "Find facts about the Eiffel Tower")
    pry.wait()
```

---

## Debug Points

Call `pry.debugpoint("label")` anywhere — in scripts, tasks, or between agent calls — to hard-pause execution **immediately at that line**. The calling thread blocks right there; the TUI stays fully interactive so you can inspect every tab. Press **p** to resume or **n** to step one hook at a time.

```python
pry = Pry()
pry.attach(agent)

agent.run("Research phase")
pry.debugpoint("after research — inspect state before handoff")
# ↑ execution blocks here. Navigate the TUI.
# [d] tab shows captured agent state: model, budget, context, tools, memory.
# Press [p] to resume, [n] to step, [q] to quit.

agent.handoff(WriterAgent, "write the report")
pry.debugpoint("handoff complete")
```

This is the equivalent of `binding.pry` in Ruby — the program stops right there and you inspect live state.

### What gets captured at a debug point

When you call `pry.debugpoint()`, pry snapshots every attached agent:

| Field | Source |
|-------|--------|
| model | `agent.model_config` |
| budget | `agent.budget_state` (spent / limit / %) |
| context tokens | `agent.context_stats` |
| tools | `agent.tools` (name + description) |
| memory | `agent.memory` (backend, top_k, types, scope, item count) |
| rate limit | `agent.rate_limit` (rpm, tpm) |

Press **↵** on the debugpoint event in the stream to see the full captured state.

---

## The TUI

Two panels, independently navigatable with `←/→`:

**Left — Event Stream**
Every hook event in chronological order. Use `↑/↓` to scroll. Press `↵` on any event for full detail.

**Right — Focused Debug Tabs**

| Key | Tab | What it shows |
|-----|-----|---------------|
| `[e]` | event | Full detail of the stream-selected event |
| `[a]` | agents | All runs, handoffs, spawns with cost and iterations |
| `[t]` | tools | Every tool call with full args and result |
| `[m]` | memory | Memory + context + knowledge at the selected stream moment |
| `[g]` | guardrails | Guardrail checks + last agent output |
| `[d]` | debug | Breakpoints and current execution position |
| `[r]` | errors | All errors and warnings |

The **memory tab** is time-aware: it shows the memory/context/knowledge state as it was at the moment of the selected stream event, so you can answer "what did the agent know at this point?"

Press `↵` on any right-panel item for a full detail view. Press `ESC` to go back.

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| `↑` / `↓` | Scroll the focused panel |
| `←` / `→` | Switch focus between stream and right panel |
| `↵` | Drill into selected event / item |
| `ESC` | Back / deselect |
| `[e]` `[a]` `[t]` `[m]` `[g]` `[d]` `[r]` | Jump to tab |
| `Tab` / `Shift+Tab` | Cycle through tabs |
| `p` | Pause / resume agent execution |
| `n` | Step one hook forward (while paused) |
| `q` | Quit |

---

## Options

```python
Pry(
    json_fallback=False,     # Force JSON lines even in a TTY
    show_budget=True,        # Capture budget events
    show_memory=True,        # Capture memory events
    show_tools=True,         # Capture tool call events
    show_llm=True,           # Capture LLM request events
    max_rows=500,            # Scrollback buffer size
    redact_prompts=False,    # Replace prompt/arg content with [redacted]
    filter_mode="all",       # "all" | "errors" | "tools" | "memory"
)
```

---

## Non-TTY / CI Fallback

In environments without an interactive terminal (CI, Docker, piped output), Pry auto-detects and falls back to structured JSON lines on stdout:

```json
{"event": "agent.run.start", "model": "gpt-4o-mini", "input": "hello"}
{"event": "tool.call.start", "name": "search", "arguments": "{\"q\": \"capital of France\"}"}
{"event": "agent.run.end", "cost": "0.0012", "tokens": "342", "iterations": "2"}
```

Force JSON mode explicitly (useful for tests or log ingestion):

```python
captured: list[str] = []
pry = Pry(json_fallback=True, stream_override=captured)
pry.attach(agent)
agent.run("Hello")
# captured now contains JSON event lines
```

---

## Multi-Agent Debugging

Pry handles multi-agent systems — handoffs, parallel spawns, and dynamic pipelines — in a single unified stream.

```python
# Handoff with breakpoint
pry = Pry()
pry.attach(researcher).attach(writer)

researcher.run("Research EVs")
pry.debugpoint("before handoff")   # blocks — inspect both agents' state before passing context
researcher.handoff(WriterAgent, "Write the report")

# Parallel spawn
results = orchestrator.spawn_parallel([
    (AnalystA, "task A"),
    (AnalystB, "task B"),
])
pry.debugpoint("all parallel agents done")
```

In the **[a] agents tab** you see `HANDOFF_START` with `source_agent`, `target_agent`, and `user_input`. In the **[t] tools tab** you see tool calls from every spawned agent. The stream interleaves all events chronologically with the agent name tagged on each row.

---

## Context Snapshots

Whenever a `context.snapshot` event fires, Pry captures the full message list. Navigate to that event in the stream and press `↵` — the detail view shows every message in the context at that exact moment. This answers "what was the model actually seeing at step N?"

---

## Integration with Tracing

Pry subscribes to the same hook events as the tracing system. Attaching Pry does not replace or disable tracing exporters — both run in parallel.

```python
from syrin.debug import Pry
from syrin.observability import JSONLExporter, get_tracer

get_tracer().add_exporter(JSONLExporter("traces.jsonl"))

with Pry() as pry:
    pry.attach(agent)
    pry.run(agent.run, "Explain distributed tracing")
    pry.wait()
```

---

## What's Next?

- [Tracing](/agent-kit/debugging/tracing) — Persistent span-based tracing with OTLP exporters
- [Hooks](/agent-kit/debugging/hooks) — Subscribe to lifecycle events programmatically
- [Logging](/agent-kit/debugging/logging) — Structured log output for production systems
- [Debugging Techniques](/agent-kit/debugging/debugging-techniques) — Systematic strategies for diagnosing agent failures
