---
title: Pry — Interactive Agent Debugger
description: Step through agent execution, inspect state at any point, and set breakpoints anywhere — like byebug, but for AI agents.
weight: 175
---

## What Is Pry?

Pry is Syrin's interactive debugger. It's inspired by Ruby's byebug — the idea that you should be able to stop your program mid-execution, look around, and then decide whether to continue. Except instead of Ruby objects, you're inspecting LLM calls, tool invocations, budget state, and memory snapshots.

It gives you a live two-panel terminal UI that streams every agent event in real time. You can navigate to any event for full detail, pause execution at any point, step through events one by one, and inspect the full agent state before deciding what to do next.

## Quickstart

```python
from syrin import Agent, Model
from syrin.debug import Pry

agent = Agent(model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"))
# model = Model.mock()  # no API key needed for testing

pry = Pry()
pry.attach(agent)
agent.run("What is the capital of France?")
# TUI stays open after the run — press q to exit
```

The context manager pattern keeps the TUI open until you press `q`:

```python
with Pry() as pry:
    pry.attach(agent)
    pry.run(agent.run, "Hello")   # Runs agent in a background thread
    pry.wait()                     # Hold TUI open — q to exit
```

Attach multiple agents — events from all of them stream into the same panel, tagged by agent name:

```python
with Pry() as pry:
    pry.attach(researcher).attach(writer)
    pry.run(researcher.run, "Find facts about the Eiffel Tower")
    pry.wait()
```

For scripts with a `--debug` flag, use `Pry.from_debug_flag()` to avoid creating multiple TUI sessions:

```python
from syrin.debug import Pry

pry = Pry.from_debug_flag()
if pry is not None:
    pry.attach(agent)
```

## Debug Points

Call `pry.debugpoint("label")` anywhere to hard-pause execution at that exact line. The calling thread blocks; the TUI stays fully interactive. Press `p` to resume or `n` to step one hook at a time.

```python
pry = Pry()
pry.attach(agent)

agent.run("Research phase")
pry.debugpoint("after research — inspect state before spawn")
# Execution stops here. Navigate the TUI. Press [p] to resume.

agent.spawn(WriterAgent, "write the report")
pry.debugpoint("spawn complete")
```

This is the equivalent of `binding.pry` in Ruby. The program stops right there and you inspect live state.

The most effective pattern for `debugpoint()` is around boundaries where control or context changes: before a spawn, before an expensive tool sequence, or at other delegation points. Drop a debugpoint, inspect the `[d]`, `[a]`, `[m]`, and `[e]` tabs, then press `p` to continue.

When you call `debugpoint()`, Pry snapshots every attached agent. The snapshot includes the model config, budget state (spent/limit/%), context token count, tools (name and description), memory (backend, top_k, types, item count), and rate limit config. Press Enter on the debugpoint event in the stream to see the full captured state.

## The TUI Layout

Two panels, independently navigatable with the left/right arrows.

The **left panel** is the event stream — every hook event in chronological order. Use up/down arrows to scroll. Press Enter on any event to open its full detail.

The **right panel** has seven tabs:

`[e]` event — Full detail of the currently selected stream event.

`[a]` agents — All runs, handoffs, and spawns with cost and iterations.

`[t]` tools — Every tool call with full arguments and result.

`[m]` memory — Memory, context, and knowledge state at the selected stream moment. Time-aware: it shows what the agent knew at that exact point in the stream.

`[g]` guardrails — Guardrail checks and last agent output.

`[d]` debug — Breakpoints and current execution position.

`[r]` errors — All errors and warnings.

Start on the left when you're tracing execution order. Move right when you want details for the selected event. The memory tab is especially useful for diagnosing why the agent said something unexpected — it shows what was in context at that moment.

## Keyboard Controls

`↑` / `↓` — Scroll the focused panel.

`←` / `→` — Switch focus between stream and right panel.

`↵` (Enter) — Drill into the selected event or item.

`ESC` — Go back or deselect.

`[e]` `[a]` `[t]` `[m]` `[g]` `[d]` `[r]` — Jump to tab.

`Tab` / `Shift+Tab` — Cycle through tabs.

`p` — Pause / resume agent execution.

`n` — Step one hook forward (while paused).

`q` — Quit.

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

## Non-TTY / CI Fallback

In environments without an interactive terminal (CI, Docker, piped output), Pry auto-detects and falls back to structured JSON lines on stdout:

```json
{"event": "agent.run.start", "model": "gpt-4o-mini", "input": "hello"}
{"event": "tool.call.start", "name": "search", "arguments": "{\"q\": \"capital of France\"}"}
{"event": "agent.run.end", "cost": "0.0012", "tokens": "342", "iterations": "2"}
```

Force JSON mode explicitly — useful for capturing traces in tests:

```python
captured: list[str] = []
pry = Pry(json_fallback=True, stream_override=captured)
pry.attach(agent)
agent.run("Hello")
# captured now contains JSON event lines
```

## Multi-Agent Debugging

Pry handles handoffs, parallel spawns, and dynamic pipelines in a single unified stream:

```python
pry = Pry()
pry.attach(researcher).attach(writer)

researcher.run("Research EVs")
pry.debugpoint("before spawn")
researcher.spawn(WriterAgent, "Write the report")

results = orchestrator.spawn_parallel([
    (AnalystA, "task A"),
    (AnalystB, "task B"),
])
pry.debugpoint("all parallel agents done")
```

In the agents tab, you see each `SPAWN_START` with source agent, target agent, and input. In the tools tab, you see tool calls from every spawned agent. The stream interleaves all events chronologically with the agent name on each row.

Example scripts to try:

`python examples/10_observability/debug_ui.py --debug` — Single-agent Pry walkthrough.

`python examples/21_debug_multiagent/spawn_debug.py --debug` — Spawn inspection.

`python examples/21_debug_multiagent/parallel_spawn_debug.py --debug` — Parallel spawn debugging.

## Context Snapshots

Whenever a `context.snapshot` event fires, Pry captures the full message list. Navigate to that event and press Enter — the detail view shows every message the model was seeing at that exact moment. This answers "what did the model actually have in its context at step N?"

## Integration with Tracing

Pry subscribes to the same hook events as the tracing system. Attaching Pry doesn't replace or disable tracing exporters — both run in parallel:

```python
from syrin.debug import Pry
from syrin.observability import JSONLExporter, get_tracer

get_tracer().add_exporter(JSONLExporter("traces.jsonl"))

with Pry() as pry:
    pry.attach(agent)
    pry.run(agent.run, "Explain distributed tracing")
    pry.wait()
```

## What's Next?

- [Pry Multi-Agent](/debugging/pry-multi-agent) — Advanced multi-agent TUI features
- [Pry Breakpoints](/debugging/pry-breakpoints) — Detailed breakpoint reference
- [Tracing](/debugging/tracing) — Persistent span-based tracing
- [Hooks Reference](/debugging/hooks-reference) — All 182 lifecycle hooks
