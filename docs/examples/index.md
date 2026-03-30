---
title: Overview
description: Learn by example with Syrin AI Agent library
weight: 300
---

## Learn by Example

The best way to learn Syrin is by exploring working examples. Each example demonstrates a specific capability, from basic agent creation to production-ready patterns.

## Quick Start

Start with the notebook:

```bash
# Open the interactive notebook
jupyter notebook examples/getting_started.ipynb
```

Or run examples directly:

```bash
# From project root
PYTHONPATH=. python examples/01_minimal/basic_agent.py

# Or as a module
PYTHONPATH=. python -m examples.01_minimal.basic_agent
```

## Example Categories

### Basic Patterns

| Category | Location | What You'll Learn |
| --- | --- | --- |
| Minimal | `01_minimal/` | Create agents, use builders, budgets, tools, and inspect responses |
| Tasks | `02_tasks/` | Task-based execution, structured output |
| Budget | `03_budget/` | Budget limits, cost tracking, thresholds |
| Memory | `04_memory/` | Buffer, episodic, semantic, procedural memory |

### Tools & Output

| Category | Location | What You'll Learn |
| --- | --- | --- |
| Tools | `05_tools/` | Define tools, TOON format, structured output |
| Loops | `06_loops/` | REACT, HITL, custom loop strategies |
| Guardrails | `09_guardrails/` | Content filtering, validation, PII detection |
| Prompts | `14_prompts/` | Prompt decorators, runtime variables, persona prompts |
| Templates | `20_template/` | Slot-based templates, rendered outputs, generated files |

### Multi-Agent & Production

| Category | Location | What You'll Learn |
| --- | --- | --- |
| Multi-Agent | `07_multi_agent/` | Pipeline, handoff, spawning, team collaboration |
| Streaming | `08_streaming/` | Token-by-token streaming responses |
| Observability | `10_observability/` | Hooks, tracing, audit logging |
| Debug Multi-Agent | `21_debug_multiagent/` | Pry across handoffs, spawns, and dynamic pipelines |
| Watch | `22_watch/` | Cron, webhook, queue, and pipeline-triggered execution |

### Advanced Features

| Category | Location | What You'll Learn |
| --- | --- | --- |
| Context | `11_context/` | Token limits, compaction, runtime injection |
| MCP | `11_mcp/` | Model Context Protocol client and server flows |
| Checkpoints | `12_checkpoints/` | State persistence, recovery |
| Remote Config | `12_remote_config/` | Runtime config overrides and config-serving flows |
| Models | `13_models/` | Provider configuration, model routing |
| Routing | `17_routing/` | Cost-optimized model selection |
| Serving | `16_serving/` | HTTP, CLI, STDIO, playground, and router serving |
| Multimodal | `18_multimodal/` | Image, video, voice generation |
| Knowledge | `19_knowledge/` | RAG, document loading, chunking, vector stores |

## Real-World Examples

### Chatbot with Full Features

A production-ready chatbot with memory, context, guardrails, and routing.

```bash
python -m examples.16_serving.chatbot
```

**Features demonstrated:**
- SQLite-backed memory with decay
- Context compaction at 75% token limit
- Content filtering guardrails
- Multi-model routing based on task type
- Image and video generation

### Knowledge Agent

RAG-powered agent for answering questions from your documents.

```bash
python -m examples.19_knowledge.knowledge_agent
```

**Features demonstrated:**
- Knowledge base creation from text sources
- Vector embeddings with OpenAI
- Agentic retrieval for complex queries
- Direct search for debugging

### Voice AI Agent

Phone-callable AI that represents your profile to recruiters.

```bash
cd examples/resume_agent && python agent.py
```

**Features demonstrated:**
- Syrin brain with Pipecat voice pipeline
- Knowledge from resume files (Markdown, YAML)
- Scheduling tools for calendar integration
- Text mode for testing, voice mode for production
- Twilio telephony integration

### IPO Drafting Agent

Drafts the Capital Structure section of DRHP from ROC filings.

```bash
python -m examples.ipo_drafting_agent.run
```

**Features demonstrated:**
- Agentic RAG with multi-query search
- Grounding with fact verification
- Structured output for legal compliance
- Guardrails for data validation
- Cost budgeting per run

### Agent Swarm with Observability

Dynamic multi-agent swarm with full lifecycle hooks and tracing.

```bash
python examples/07_multi_agent/dynamic_pipeline_full.py
```

**Features demonstrated:**
- DynamicPipeline with LLM-based agent selection
- Parallel agent execution
- Complete lifecycle hooks (spawn, complete, error)
- Cost aggregation per agent
- Execution timeline and metrics
- Playground UI with debug mode

## Environment Setup

Create a `.env` file in the `examples/` directory:

```bash
# Required for most examples
OPENAI_API_KEY=sk-...

# Optional: for specific providers
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
GEMINI_API_KEY=...

# Optional: model override
ANTHROPIC_MODEL_ID=anthropic/claude-3-7-sonnet-latest
```

## Setup from Project Root

```bash
# Activate virtual environment
source .venv/bin/activate

# Install with development dependencies
uv pip install -e ".[dev,anthropic]"

# Run an example
PYTHONPATH=. python examples/01_minimal/basic_agent.py
```

## What's Next?

- Start with the [getting started notebook](https://github.com/syrin-labs/syrin-python-python/blob/main/examples/getting_started.ipynb)
- Explore [minimal examples](/agent-kit/examples/basic-examples) for core concepts
- Learn [production chatbot](/agent-kit/examples/chatbot) for full-featured patterns
- Build an [agent swarm](/agent-kit/examples/agent-swarm) with observability

## See Also

- [Agents documentation](/agent-kit/agent/overview) for agent concepts
- [Multi-agent documentation](/agent-kit/multi-agent/overview) for collaboration patterns
- [Debugging documentation](/agent-kit/debugging/overview) for observability
- [Production documentation](/agent-kit/production/serving) for deployment
- [Voice AI Agent](/agent-kit/examples/voice-agent) for telephony integration
- [IPO Drafting Agent](/agent-kit/examples/ipo-drafting-agent) for enterprise RAG
- [Agent Swarm](/agent-kit/examples/agent-swarm) for dynamic multi-agent systems
