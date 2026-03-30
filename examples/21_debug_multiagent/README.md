# 21_debug_multiagent — Pry for multi-agent systems

- **handoff_debug.py** — Inspect a handoff boundary with interactive breakpoints.
- **parallel_spawn_debug.py** — Watch multiple spawned agents in one Pry session.
- **dynamic_pipeline_debug.py** — Debug dynamic orchestration and agent selection live.

Run these examples with `--debug` to open Pry:

```bash
python examples/21_debug_multiagent/parallel_spawn_debug.py --debug
```

They are useful when you need to understand handoffs, parallel work, event ordering, or context state across multiple agents.
