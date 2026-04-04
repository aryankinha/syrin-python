---
title: Pry — Multi-Agent TUI
description: Debug Workflows, Swarms, and Pipelines with the multi-agent Pry debugger — agent graph, budget tree, A2A timeline, HandoffContext inspector, and state export.
weight: 176
---

## Pry on Multi-Agent Primitives

Every multi-agent primitive accepts `pry=True` to activate the multi-agent Pry TUI for that execution. Pry intercepts every lifecycle hook — workflow steps, agent handoffs, A2A messages, LLM calls — and streams them into a unified live dashboard.

### Workflow

```python
from syrin import Workflow

wf = Workflow("research-pipeline", pry=True)
wf.step("research", ResearchAgent)
wf.step("write", WriterAgent)
wf.run("AI adoption in healthcare")
```

### Swarm

```python
from syrin.swarm import Swarm

swarm = Swarm(
    agents=[Researcher(), Analyst(), Writer()],
    goal="Q1 market analysis",
    pry=True,
)
await swarm.run()
```

### Pipeline

```python
from syrin import Pipeline

pipeline = Pipeline(
    agents=[Researcher(), Analyst(), Writer()],
    pry=True,
)
pipeline.run("Summarise the attached report")
```

### Single Agent

Pass `pry=True` directly on an agent instance to open a Pry session for that agent alone:

```python
from syrin import Agent, Model
from syrin.debug import Pry

class MyAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")
    # Use Model.mock() above for testing without an API key
    system_prompt = "You are a research assistant."

agent = MyAgent(pry=True)
agent.run("What are the 3 biggest risks in AI?")
```

---

## PryConfig

`PryConfig` fine-tunes which breakpoints pause execution and which panels are visible. Pass it via the `pry_config` parameter:

```python
from syrin import Workflow
from syrin.debug._pry_swarm import PryConfig
from syrin.enums import DebugPoint

wf = Workflow(
    "pipeline",
    pry=True,
    pry_config=PryConfig(
        breakpoints=[DebugPoint.ON_SPAWN, DebugPoint.ON_ERROR],
        pause_on_agent_failure=True,
        focus_agent="ResearchAgent",
        show_budget_tree=True,
        show_a2a_timeline=True,
    ),
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `breakpoints` | `list[DebugPoint]` | `[]` | Execution moments that pause and open the debugger |
| `pause_on_agent_failure` | `bool` | `False` | Pause instead of triggering the configured `FallbackStrategy` when an agent fails — lets you inspect failure state before proceeding |
| `focus_agent` | `str \| None` | `None` | Pre-select a specific agent in the TUI at start; `None` auto-selects |
| `show_budget_tree` | `bool` | `True` | Show the hierarchical budget allocation panel |
| `show_a2a_timeline` | `bool` | `False` | Show the A2A message timeline panel |

---

## What the TUI Shows

The multi-agent TUI is a four-panel dashboard built on top of the single-agent Pry stream.

### Agent Graph Panel

The left-side graph shows a live view of all agents in the current run — their class names, current `AgentStatus` (IDLE, RUNNING, PAUSED, FAILED, STOPPED, KILLED), and the edges between them (step dependencies, handoff arcs, spawn relationships). The selected node is highlighted; pressing `↵` opens the agent state detail.

### Budget Tree Panel

When `show_budget_tree=True` (the default), a collapsible tree shows the full budget hierarchy: the swarm/workflow total at the root, per-agent allocations as children, and spent vs. limit as a coloured bar. This is the fastest way to spot which agent is consuming budget disproportionately.

### A2A Timeline Panel

When `show_a2a_timeline=True`, a chronological list of every agent-to-agent message is shown — sender, recipient, message type, timestamp. Press `↵` on any message to inspect the full payload including any attached `HandoffContext`.

### Breakpoint Info Panel

The `[d]` debug tab shows all configured `DebugPoint` values, whether each is currently armed, and the last breakpoint hit — including the agent name, execution step number, and the reason the pause fired.

---

## Keyboard Controls

The TUI keyboard controls follow a consistent pattern. `↑` / `↓` scrolls the focused panel. `←` / `→` switches focus between the stream and the right panel. `↵` drills into the selected item to show its detail. `ESC` goes back or deselects.

For execution control: `c` continues — resuming all paused agents. `s` steps — advancing one hook and pausing again. `q` quits and terminates the session.

For tab navigation, the bracketed keys jump directly to tabs: `[e]` for events, `[a]` for agents, `[t]` for tools, `[m]` for memory, `[g]` for graph, `[d]` for debug, `[r]` for replay. Finally, `x` exports the full session state to JSON.

`c` maps to `PryResumeMode.CONTINUE`, `s` maps to `PryResumeMode.STEP`.

---

## SpawnContext Inspector

When execution pauses on `DebugPoint.ON_SPAWN`, navigate to the `[a]` agents tab and press `↵` on the `SPAWN_START` event. The detail view shows the full `SpawnContext` passed to the next agent:

```
SPAWN_START
  source_agent:  ResearchAgent
  target_agent:  WriterAgent
  user_input:    "AI adoption in healthcare"
  context_keys:  ["research_findings", "sources", "budget_remaining"]
  context:
    research_findings: "Key finding: 68% of hospitals..."
    sources: ["pubmed:34821...", "who.int/..."]
    budget_remaining: $0.47
```

This is the primary tool for diagnosing "wrong context passed to next agent" bugs.

---

## Lambda Preview

For `.dynamic()` workflow steps (steps defined by a callable), Pry shows a **lambda preview** in the `[d]` debug tab when execution pauses before that step runs. The preview displays the callable's `__qualname__`, the input `HandoffContext` that will be passed to it, and the inferred output agent type (if resolvable statically).

This lets you verify the dynamic routing decision before allowing it to proceed.

---

## State Export

Press `x` at any time to export the full session state to a timestamped JSON file. This calls `StateExporter.export_snapshot()` internally and writes an `ExportSnapshot` to disk.

### ExportSnapshot fields

- `agent_contexts` — dict keyed by `agent_id`; each value is the agent's full state dict (status, model, budget, context token counts)
- `memory` — list of all memory entries captured during the session
- `costs` — dict of per-agent cumulative cost in USD, keyed by `agent_id`
- `a2a_log` — ordered list of all A2A message records sent during the session
- `metadata` — dict of session metadata: timestamp, syrin version, session duration

You can also export programmatically via `PrySession.export_state(path)`:

```python
from syrin.debug._pry_swarm import PryConfig, PrySession

session = PrySession(config=PryConfig())
session.export_state("/tmp/debug_snapshot.json")
```

Or build and export a snapshot directly:

```python
from syrin.debug._state_export import StateExporter

exporter = StateExporter()
snapshot = StateExporter.build_snapshot(
    agent_contexts={"agent-1": {"status": "STOPPED", "cost": 0.03}},
    memory=[{"id": "m1", "content": "key finding"}],
    costs={"agent-1": 0.03},
    a2a_log=[{"from": "agent-1", "to": "agent-2", "msg": "done"}],
)
exporter.export_snapshot(snapshot, "/tmp/debug.json")
```

---

## What's Next?

- [Pry Breakpoints](/debugging/pry-breakpoints) — all `DebugPoint` values and `PryResumeMode` options
- [Pry (single-agent)](/debugging/pry) — single-agent TUI reference
- [Swarm](/multi-agent/swarm) — Swarm topologies and configuration
- [Workflow](/multi-agent/workflow) — Workflow steps, branching, and dynamic steps
