---
title: Visualization
description: Static and live visualization for Workflow and Pipeline — Rich trees, Mermaid diagrams, and the /graph HTTP endpoint
weight: 71
---

## Three Ways to See Your Workflow

Before you run a complex pipeline, it helps to see it. Syrin gives you three visualization options: a terminal tree for quick inspection, a Mermaid diagram for docs and dashboards, and a live status table that updates as each step runs.

## wf.visualize() — Terminal Tree

Prints a color-coded tree to stdout. Works before and after running:

```python
from syrin import Agent, Model
from syrin.workflow import Workflow

class PlannerAgent(Agent):
    model = Model.mock()

class ResearchAgent(Agent):
    model = Model.mock()

class WriterAgent(Agent):
    model = Model.mock()

class EditorAgent(Agent):
    model = Model.mock()

wf = (
    Workflow("demo")
    .step(PlannerAgent)
    .parallel([ResearchAgent, WriterAgent])
    .branch(lambda ctx: len(ctx.content) > 500, if_true=EditorAgent, if_false=WriterAgent)
)
wf.visualize()
```

Output:

```
demo
├── 0: PlannerAgent
├── 1: parallel
│   ├── ResearchAgent
│   └── WriterAgent
└── 2: ◇ branch
    ├── EditorAgent (if true)
    └── WriterAgent (if false)
```

When a `Workflow` is nested inside another as a step, use `expand_nested=True` to see its internal steps inline:

```python
inner = Workflow("inner").step(ResearchAgent).step(WriterAgent)
outer = Workflow("outer").step(PlannerAgent).step(inner)

outer.visualize(expand_nested=True)
# outer
# ├── 0: PlannerAgent
# └── 1: ⊞ inner (sub-workflow)
#     ├── 0: ResearchAgent
#     └── 1: WriterAgent
```

Without `expand_nested=True`, nested workflows render as `⊞ [inner-name]` — a single collapsed node.

## wf.to_mermaid() — Embed in Docs

Returns a Mermaid `graph` block as a string. Paste into GitHub READMEs, Notion, or any Mermaid-compatible renderer:

```python
print(wf.to_mermaid())
```

The default direction is top-down (`"TD"`). Switch to left-right for wide workflows:

```python
print(wf.to_mermaid(direction="LR"))
```

Example output for a sequential → parallel → branch workflow:

```
graph TD
    step_0[PlannerAgent]
    step_1_par{parallel}
    step_0 --> step_1_par
    step_1_merge([merge])
    step_1_ResearchAgent[ResearchAgent]
    step_1_par --> step_1_ResearchAgent
    step_1_ResearchAgent --> step_1_merge
    step_1_WriterAgent[WriterAgent]
    step_1_par --> step_1_WriterAgent
    step_1_WriterAgent --> step_1_merge
    step_2_branch{{branch}}
    step_1_merge --> step_2_branch
    step_2_true[EditorAgent]
    step_2_false[WriterAgent]
    step_2_merge([merge])
    step_2_branch -->|true| step_2_true
    step_2_branch -->|false| step_2_false
    step_2_true --> step_2_merge
    step_2_false --> step_2_merge
```

Different step types use different Mermaid node shapes. Sequential steps use rectangles `[label]`. Parallel fan-outs use diamonds `{label}`. Parallel merge nodes use stadiums `([label])`. Branch nodes use hexagons `{{label}}`. Dynamic steps use parallelograms `[/label/]`.

## wf.to_dict() — Custom Rendering

Returns a plain `dict` with `"nodes"` and `"edges"` lists for custom rendering in a web dashboard or notebook:

```python
graph = wf.to_dict()
for node in graph["nodes"]:
    print(node["id"], node["label"], node["step_type"])
```

Node `step_type` values: `"sequential"`, `"workflow"`, `"parallel"`, `"parallel_child"`, `"branch"`, `"branch_true"`, `"branch_false"`, `"dynamic"`.

## show_graph=True — Live Status During Execution

Pass `show_graph=True` to `wf.run()` to see a live status table as each step runs:

```python
result = await wf.run("Research AI trends", show_graph=True)
```

The table shows each step's status, cost, and elapsed time. Status values and their meaning:

`PENDING` (dim grey) — Not yet started.

`RUNNING` (yellow) — Currently executing.

`COMPLETE` (green) — Finished successfully.

`FAILED` (red) — Raised an unhandled exception.

`SKIPPED` (dim grey) — Was not reached because a prior step failed.

The table renders once at the end. Requires `rich` — if `rich` isn't installed, execution proceeds without the table.

`arun()` is an alias for `run()` and also accepts `show_graph=True`.

## /graph HTTP Endpoint

When a workflow is served with `wf.serve()`, the `/graph` endpoint returns the Mermaid diagram as JSON. Use it to drive a live diagram in a web dashboard without redeploying:

```python
wf.serve(port=8080)
# GET http://localhost:8080/graph
# → {"graph": "graph TD\n    step_0[PlannerAgent]\n    ..."}
```

## See Also

- [Workflow](/multi-agent/workflow) — Step types and builder pattern
- [Lifecycle Controls](/multi-agent/lifecycle) — pause, resume, cancel
