---
title: Examples
description: Working Syrin code organized by topic — from first agent to production multi-agent swarms
weight: 300
---

## Learn by Building

Every example here was written to be run. All examples that use `Model.mock()` work without an API key. Examples that use real models like `Model.OpenAI()` are clearly marked and require the corresponding API key.

The examples in the GitHub repository live at [`examples/`](https://github.com/syrin-labs/syrin-python/tree/main/examples) and are organized into numbered folders matching this page.

## Getting Started Examples

These are the first things to run when you are new to Syrin. No API key needed.

**Basic agent, response object, budget:**
[`examples/01_minimal/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/01_minimal)

- `basic_agent.py` — Minimal agent with `Model.mock()`, shows the response object
- `agent_with_budget.py` — Budget with warn and raise behaviors
- `agent_with_tools.py` — Tools registered on an agent
- `response_object.py` — Every field on the Response object

**Tasks:**
[`examples/02_tasks/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/02_tasks)

- `single_task.py` — Agent method calling `self.run()`
- `multiple_tasks.py` — Multiple methods on one agent
- `task_with_output_type.py` — Typed output from an agent method

## Budget Examples

[`examples/03_budget/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/03_budget)

- `basic_budget.py` — Max cost with warn and raise behaviors
- `thresholds.py` — Fire callbacks at 50%, 80%, 95% spent
- `rate_limits.py` — Hourly, daily, weekly spending caps
- `shared_budget.py` — Shared pool for multi-agent systems
- `budget_forecasting.py` — Abort if on track to exceed budget
- `budget_anomaly.py` — Detect unexpected spending spikes
- `enterprise_budget.py` — All budget features combined

## Memory Examples

[`examples/04_memory/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/04_memory)

- `basic_memory.py` — remember, recall, forget with all four types
- `recall.py` — Filtering and querying memories
- `memory_types_and_decay.py` — Decay curves per memory type
- `async_memory.py` — Async memory operations
- `chroma_memory.py` — Chroma vector database backend
- `qdrant_memory.py` — Qdrant backend
- `postgres_memory.py` — PostgreSQL backend
- `redis_memory.py` — Redis backend

## Tool Examples

[`examples/05_tools/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/05_tools)

- `toon_format.py` — TOON vs JSON schema size comparison
- `structured_output.py` — `@structured` and `Output()` (requires real model)

## Loop Strategy Examples

[`examples/06_loops/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/06_loops)

- `all_loop_strategies.py` — REACT vs SINGLE_SHOT

## Multi-Agent Examples

[`examples/07_multi_agent/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/07_multi_agent)

- `pipeline.py` — Sequential pipeline (no API key)
- `swarm_orchestrator.py` — Orchestrator topology (requires OpenAI)
- `swarm_parallel.py` — Parallel swarm (requires API key)
- `swarm_consensus.py` — Consensus voting (requires API key)
- `swarm_reflection.py` — Reflection/critique loop (requires API key)
- `swarm_a2a.py` — Agent-to-agent typed messaging (requires API key)
- `agent_router.py` — LLM-driven dynamic orchestration (requires API key)
- `spawn.py` — Agent task delegation (spawn)
- `hierarchical_swarm.py` — Nested agent hierarchy
- `monitor_loop.py` — Quality supervision with MonitorLoop
- `workflow_sequential.py` — Sequential workflow (requires API key)
- `workflow_parallel.py` — Parallel steps in a workflow (requires API key)
- `workflow_conditional.py` — Conditional branching (requires API key)

## Streaming

[`examples/08_streaming/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/08_streaming)

- `stream_sync.py` — Sync streaming with `agent.stream()`
- `stream_async.py` — Async streaming with `agent.astream()`

## Guardrails and Security

[`examples/09_guardrails/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/09_guardrails)
[`examples/09_security/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/09_security)

- PII detection and redaction
- Content filtering
- Prompt injection detection
- Agent identity and signing

## Observability

[`examples/10_observability/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/10_observability)

- `comprehensive_tracing.py` — Full trace export
- `audit_logging.py` — Audit log recording

## Context Management

[`examples/11_context/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/11_context)

- `context_management.py` — Context config and thresholds
- `context_snapshot_demo.py` — Inspect context contents
- `context_thresholds_compaction_demo.py` — Automatic compaction

## Checkpointing

[`examples/12_checkpoints/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/12_checkpoints)

- `long_running_agent.py` — Save and restore state across restarts

## Models

[`examples/13_models/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/13_models)

- Model configuration, custom providers, model routing

## Serving

[`examples/16_serving/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/16_serving)

- `http_serve.py` — HTTP serving with playground
- `cli_serve.py` — CLI interactive mode
- `chatbot.py` — Chat agent with persistent memory
- `mount_on_existing_app.py` — Mount on FastAPI

## Real-World Agents

**IPO Drafting Agent:**
[`examples/ipo_drafting_agent/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/ipo_drafting_agent)

A complete agent that drafts DRHP sections from financial filings. Uses RAG (Knowledge), structured output, and multi-source document loading.

**Voice AI Agent:**
[`examples/resume_agent/`](https://github.com/syrin-labs/syrin-python/tree/main/examples/resume_agent)

A voice-powered recruiter agent using Syrin + Pipecat for real phone call handling.

## The Getting Started Notebook

If you want everything in one place — docs, code, and runnable output — open the notebook:

```bash
jupyter notebook examples/getting_started.ipynb
```

It covers every major topic with runnable cells using `Model.mock()`, so no API key is needed.

## What's Next

- [Introduction](/agent-kit/introduction) — Start from the beginning
- [Quick Start](/agent-kit/quick-start) — Build your first agent in 10 minutes
- [Agent Overview](/agent-kit/agent/overview) — Understand the Agent class fully
