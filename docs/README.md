# Syrin Documentation

Welcome to the **Syrin** library! Build powerful AI agents with budgets, memory, and more.

## 📚 Start Here

**New to Syrin?** Start with [Getting Started](getting-started.md) - a beginner-friendly guide.

**Want to run your agent?** Serving is built-in. Serve via **HTTP** (`agent.serve(port=8000)`), **CLI** (`agent.serve(protocol=ServeProtocol.CLI)`), or the **playground** (`enable_playground=True`). See traces with `debug=True` or `--trace`. → [Serving](serving.md) · [Playground](playground.md)

**Group tools in MCP?** Define an MCP server with `@tool` methods and add it to your agent: `tools=[ProductMCP()]`. MCP tools become agent tools. → [MCP](mcp.md)

## 🎯 Use Case Guides

Learn by doing! Pick a use case that matches what you want to build:

1. **[Use Case 1: Simple Q&A Agent](simple-qa-agent.md)** ⭐ Start here
   - Ask questions and get answers
   - Customize personality
   - Interactive chat
   - **Perfect for:** Chatbots, Q&A systems

2. **[Use Case 2: Research Agent with Tools](research-agent-with-tools.md)**
   - Give agents special abilities
   - Search, calculate, look up data
   - Build custom tools
   - **Perfect for:** Automation, data processing

3. **[Use Case 3: Agent with Memory](agent-with-memory.md)**
   - Make agents remember conversations
   - Learn user preferences
   - Multi-turn conversations
   - **Perfect for:** Personal assistants, customer support

4. **[Use Case 4: Budget Control & Cost Management](budget-control.md)**
   - Keep AI spending under control
   - Set spending limits
   - Monitor costs
   - **Perfect for:** Production apps, cost-conscious teams

5. **[Use Case 5: Multi-Agent Orchestration](multi-agent.md)**
   - Create teams of specialized agents
   - Sequential and parallel processing
   - Agent delegation
   - **Perfect for:** Complex workflows, specialization

6. **[Use Case 6: Streaming & Real-time Updates](streaming.md)**
   - Get responses in real-time
   - Stream long content
   - ChatGPT-like experience
   - **Perfect for:** Web apps, live chat

## 📖 Reference

**[Architecture](ARCHITECTURE.md)** - Package layout, dependency direction, extension points, and §6 consistent patterns (naming, typing, config vs runtime).

**[Code quality](code-quality.md)** - mypy strict, ruff, public API typing, test coverage, and consistent patterns.

**[Models Guide](models.md)** - Complete guide to models

**[Routing](routing.md)** - Task classification and model routing
- PromptClassifier, ModelRouter, RoutingConfig
- Agent with model list + model_router
- OpenRouter, get_default_profiles, ROUTING_DECISION hook (includes routing_latency_ms)

**[Multimodal](multimodal.md)** - Images, files, and generation
- Multimodal input: content parts, `file_to_message`, playground paste/attach
- Image/video generation: standalone API, Agent `output_media` or `image_generation` / `video_generation`
- Hooks, StrEnums, custom providers

**[Concept Map](concept-map.md)** — Budget vs TokenLimits vs Memory (quick reference)

**[Decision Guide](guides/decision-guide.md)** — Memory (True vs Memory() vs None), Budget vs TokenLimits, loop strategies, formation mode

**[Context Types](guides/context-types.md)** — RunContext (tools) vs PromptContext (dynamic prompts)

**[Extension Points](extension-points.md)** — How to implement Model, Provider, Loop, Guardrail, etc.

**[Feature Reference Guide](reference.md)** - Complete API reference
- All components
- Common patterns
- Troubleshooting
- Performance tips

**[Advanced Topics](advanced-topics.md)** - Deep dives into production features
- [Dependency Injection](dependency-injection.md) — Tools receive ctx: RunContext[Deps] for testable, multi-tenant agents
- Lifecycle hooks
- [Event Bus](event-bus.md) — Typed domain events for metrics and observability
- Observability & tracing
- Checkpointing & state persistence
- Guardrails
- Loop strategies (REACT, HITL, custom)

**[FAQ](faq.md)** - Common questions answered
- Getting started
- Tools & memory
- Budget & costs
- Troubleshooting
- 30+ questions answered

## 🚀 Quick Start

Copy and run this to test your setup:

```python
from syrin import Agent, Model

# Recommended: Builder or presets
agent = Agent.builder(Model.Almock()).with_system_prompt("You are helpful.").build()
# Or: agent = Agent.basic(Model.Almock())
response = agent.response("Hello! How are you?")
print(response.content)
```

**Try it in the playground:** `agent.serve(port=8000, enable_playground=True)` → visit http://localhost:8000/playground  
**See traces:** Add `debug=True` to your agent, or run `python my_agent.py --trace`

## 💡 Key Concepts

### Agent
A program that can talk to AI, remember things, and do tasks.

### Tools
Special functions your agent can call (search, calculate, etc.)

### Memory
Agents can remember past conversations and learn preferences.

### Budget
Control how much money your agent can spend on AI API calls.

### Streaming
Get responses in real-time instead of waiting.

### Hooks
Execute code at specific moments during agent execution.

### Observability
Trace and debug agent execution with spans and sessions. Use `debug=True` or `--trace` to see LLM calls, tool calls, and costs in the console.

## 🎓 Learning Path

1. Read [Getting Started](getting-started.md) (5 min)
2. **Run your agent:** `agent.serve(port=8000, enable_playground=True)` → visit http://localhost:8000/playground. Use `debug=True` or `--trace` to see traces. → [Serving](serving.md) · [Playground](playground.md)
3. Try [Use Case 1: Simple Q&A](simple-qa-agent.md) (15 min)
4. Try [Use Case 2: With Tools](research-agent-with-tools.md) (20 min)
5. Try [Use Case 3: With Memory](agent-with-memory.md) (15 min)
6. Add budget with [Use Case 4](budget-control.md) (10 min)
7. Explore other use cases as needed

**Want more?** 
- [Advanced Topics](advanced-topics.md) - Hooks, observability, checkpointing, guardrails
- [FAQ](faq.md) - Common questions answered

**Total time: ~1 hour to learn the basics!**

## ⚡ Quick Links

### By Use Case
- 🚀 **Serving** → [Serving](serving.md) — serve via HTTP, CLI, or playground
- 🔌 **MCP** → [MCP](mcp.md) — group tools in MCP, use MCP inside agent tools
- 📝 **Writing** → [Use Case 1: Simple Q&A](simple-qa-agent.md)
- 🔍 **Research** → [Use Case 2: With Tools](research-agent-with-tools.md)
- 👤 **Personal Assistant** → [Use Case 3: With Memory](agent-with-memory.md)
- 💰 **Production Apps** → [Use Case 4: Budget Control](budget-control.md)
- 🏢 **Complex Workflows** → [Use Case 5: Multi-Agent](multi-agent.md)
- 🌐 **Web Apps** → [Use Case 6: Streaming](streaming.md)

### By Feature
- **Serving** → [Serving](serving.md) — HTTP, CLI, STDIO; `agent.serve()` in one line
- **Playground** → [Playground](playground.md) — web UI for chat, cost, traces
- **Observability & Traces** → [Observability](observability.md) — use `debug=True` or `--trace` to see execution
- **Agents** → [Agent Documentation](agent/README.md) — complete agent reference
- **Models** → [Models Guide](models.md) — built-in, custom, inheritance
- **Routing** → [Routing](routing.md) — model list, task classification, OpenRouter
- **Multimodal** → [Multimodal](multimodal.md) — images in/out, file_to_message, image/video generation
- **Tools** → [Use Case 2](research-agent-with-tools.md)
- **Memory** → [Use Case 3](agent-with-memory.md)
- **Budget** → [Use Case 4](budget-control.md)
- **Streaming** → [Use Case 6](streaming.md)
- **Hooks & Observability** → [Advanced Topics](advanced-topics.md)
- **API Reference** → [Feature Reference](reference.md)

### By Component Type
- **[Architecture](ARCHITECTURE.md)** — Agent-only vs standalone components
- **Agent-only** — [Agent docs](agent/README.md), loops, hooks, handoff, checkpoint API
- **Standalone** — [Models](models.md), [Guardrails](guardrails.md), [Observability](observability.md), [BudgetStore](budget-control.md)
- **Shared** — Budget, Memory, Guardrails, Checkpoint, Structured output, Rate limit (see [ARCHITECTURE](ARCHITECTURE.md) for doc mapping)

## 📋 Recent Changes

**[Changelog](../CHANGELOG.md)** — Release history, added/changed/fixed/deprecated/removed.

---

## 🆘 Help & Support

**Common Issues?**
- See [FAQ](faq.md) - 30+ common questions answered
- See [Troubleshooting in Getting Started](getting-started.md#troubleshooting)
- See [Feature Reference FAQ](reference.md)

**Found a bug?**
- Report on [GitHub Issues](https://github.com/syrin-labs/syrin-python/issues)

**Want to contribute?**
- Fork on [GitHub](https://github.com/syrin-labs/syrin-python)

## 📚 Code Examples

All examples are copy-paste ready! Each guide includes complete working code.

```bash
# Find example code in:
ls examples/

# Run a specific example:
python examples/01_simple_qa_agent.py
```

## 🎁 What Makes Syrin Special

✨ **Budget Management** - Built-in cost control (not an afterthought)

🚀 **Easy Serving** - One line to serve: `agent.serve(port=8000, enable_playground=True)`. Web playground, CLI REPL, or HTTP API. No extra wiring.

🧠 **Memory System** - Agents remember conversations (4 types of memory)

🛠️ **Tools** - Give agents special abilities easily

💰 **Cost Tracking** - Know exactly what you're spending

🚀 **Async & Streaming** - Real-time responses

👥 **Multi-Agent** - Build teams of specialized agents

🎨 **Flexible Models** - Use OpenAI, Claude, Google, or local models

🔌 **Hooks & Events** - Execute code at any point in agent lifecycle

📊 **Observability** - Use `debug=True` or `--trace` to see LLM calls, tool calls, and costs. Full tracing built-in.

## 🔄 Version Info

- **Current Version**: 0.1.0 (Early Release)
- **Python**: >= 3.10
- **Status**: Active Development

## 📞 Contact

- **Questions**: See docs and examples
- **Issues**: GitHub Issues
- **Feedback**: GitHub Discussions

---

**Ready to build?** ➡️ Start with [Getting Started](getting-started.md)
