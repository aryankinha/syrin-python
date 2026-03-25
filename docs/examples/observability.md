---
title: Observability & Debugging
description: Hooks, tracing, and audit logging for production agents
weight: 340
---

## Observability & Debugging

Production agents need observability. Syrin provides hooks, tracing, and audit logging to understand what's happening inside your agents.

## Lifecycle Hooks

Monitor agent lifecycle events with hooks.

```python
from syrin import Agent, Model
from syrin.enums import Hook

model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")

class MonitoredAgent(Agent):
    model = model
    system_prompt = "You are helpful."

agent = MonitoredAgent()

# Track all responses
def on_response(ctx):
    print(f"Response: {ctx.get('content', '')[:50]}...")
    print(f"Cost: ${ctx.get('cost', 0):.6f}")

agent.events.on(Hook.AGENT_RUN_END, on_response)

# Track all tool calls
def on_tool_start(ctx):
    print(f"Tool: {ctx.tool_name}")

agent.events.on(Hook.TOOL_CALL_START, on_tool_start)

def on_tool_end(ctx):
    print(f"Tool done: {ctx.tool_name} -> {str(ctx.result)[:30]}...")

agent.events.on(Hook.TOOL_CALL_END, on_tool_end)

result = agent.run("What is 2 + 2? Use a calculator.")
```

**What just happened:**
1. Hooked into `RESPONSE_COMPLETE` for response tracking
2. Tracked `TOOL_START` and `TOOL_END` for tool execution
3. Each hook receives a context dictionary with event data
4. Saw the complete picture of agent execution

## Cost Tracking

Track spending across multiple requests.

```python
from syrin import Agent, Model

model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")

total_cost = {"value": 0.0}
request_count = {"count": 0}

class CostTrackingAgent(Agent):
    model = model
    system_prompt = "You are helpful."

agent = CostTrackingAgent()

def track_cost(ctx):
    total_cost["value"] += ctx.get("cost", 0)
    request_count["count"] += 1
    print(f"Request #{request_count['count']}: ${ctx.get('cost', 0):.6f}")

agent.events.on(Hook.AGENT_RUN_END, track_cost)

def final_summary(ctx):
    print(f"\nTotal requests: {request_count['count']}")
    print(f"Total cost: ${total_cost['value']:.6f}")

agent.events.on(Hook.AGENT_RUN_END, final_summary)

# Simulate a conversation
agent.run("Hello!")
agent.run("How are you?")
agent.run("What's the weather?")
```

**What just happened:**
1. Accumulated costs in a mutable container
2. Tracked request count separately
3. Hooked `RUN_COMPLETE` for final summary
4. Got complete cost attribution

## Tracing with Spans

Structured tracing for performance analysis.

```python
from syrin import Agent, Model
from syrin.tracing import trace, span

model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")

class TracedAgent(Agent):
    model = model
    system_prompt = "You are helpful."

agent = TracedAgent()

# Wrap operations in spans
with trace("agent_request"):
    with span("initial_response"):
        r1 = agent.run("Hello")
    
    with span("followup"):
        r2 = agent.run("Tell me more")
    
    with span("final"):
        r3 = agent.run("Summarize")

# Export traces
agent.tracer.export(format="json", path="traces.json")
```

**What just happened:**
1. Created a top-level trace for the request
2. Nested spans for each operation phase
3. Captured timing and relationships
4. Exported for analysis

## Comprehensive Tracing Setup

Full observability with multiple exporters.

```python
from syrin import Agent, Model
from syrin.tracing import (
    Tracer,
    ConsoleExporter,
    JaegerExporter,
    OTLPExporter,
)
from syrin.hooks import Hook

model = Model.OpenAI("gpt-4o-mini", api_key="your-api-key")

tracer = Tracer()
tracer.add_exporter(ConsoleExporter())
tracer.add_exporter(
    OTLPExporter(endpoint="http://localhost:4317")
)

class ObservedAgent(Agent):
    model = model
    tracer = tracer
    system_prompt = "You are helpful."

agent = ObservedAgent()

# Automatic span creation for all operations
def start_span(ctx):
    agent.tracer.start_span(
        "response",
        attributes={"model": ctx.model}
    )

agent.events.on(Hook.LLM_REQUEST_START, start_span)

def end_span(ctx):
    agent.tracer.end_span(
        attributes={"cost": ctx.get("cost", 0)}
    )

agent.events.on(Hook.AGENT_RUN_END, end_span)

agent.run("Hello!")
```

**What just happened:**
1. Configured multiple exporters (console + OTLP)
2. Connected tracer to agent
3. Hooks create spans automatically
4. Traces flow to Jaeger/otel collectors

## Audit Logging

Record all agent operations for compliance.

```python
from syrin import Agent, Model
from syrin.audit import AuditLog, AuditBackend

class ComplianceAuditLog(AuditLog):
    def __init__(self):
        super().__init__(backend=AuditBackend.POSTGRES)
    
    def record(self, event: dict) -> None:
        # Add compliance fields
        event["compliance_timestamp"] = datetime.utcnow().isoformat()
        event["data_classification"] = self.classify(event)
        super().record(event)
    
    def classify(self, event: dict) -> str:
        content = event.get("content", "")
        if any(kw in content.lower() for kw in ["pii", "ssn", "password"]):
            return "sensitive"
        return "standard"

audit = ComplianceAuditLog()

class AuditedAgent(Agent):
    model = model
    system_prompt = "You are helpful."

agent = AuditedAgent()

# All operations logged automatically
agent.run("Process a loan application for John Doe")
```

**What just happened:**
1. Extended AuditLog for compliance requirements
2. Added classification for sensitive data
3. Timestamps for audit trail
4. Automatic recording of all operations

## Validation Hooks

Monitor structured output validation.

```python
from syrin import Agent, Model, Output
from syrin.model import structured
from syrin.enums import Hook
from syrin.types.validation import ValidationResult

@structured
class SentimentResult:
    sentiment: str
    confidence: float

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    output=Output(SentimentResult, validation_retries=3),
)

def on_start(ctx):
    print(f"Validating output type: {ctx.output_type}")

agent.events.on(Hook.OUTPUT_VALIDATION_START, on_start)

def on_success(ctx):
    print(f"Success on attempt {ctx.attempt}")

agent.events.on(Hook.OUTPUT_VALIDATION_SUCCESS, on_success)

def on_failure(ctx):
    print(f"Failed: {ctx.reason}")
    print(f"Hint: {ctx.hint}")

agent.events.on(Hook.OUTPUT_VALIDATION_FAILED, on_failure)

result = agent.run("Analyze: 'This is amazing!'")
```

**What just happened:**
1. Hooked validation lifecycle events
2. Tracked attempt count through retries
3. Captured failure reasons and hints
4. Observed how agent self-corrects

## Debug Mode

Verbose output for development.

```python
from syrin import Agent, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    system_prompt="You are helpful.",
)

# Enable debug mode for detailed logging
result = agent.run(
    "What is 2 + 2?",
    debug=True  # Logs all LLM calls, tokens, timing
)

# Or serve with debug UI
agent.serve(port=8000, enable_playground=True, debug=True)
# Visit: http://localhost:8000/playground
```

**What just happened:**
1. Enabled verbose debug output
2. Saw all LLM interactions with timing
3. Can serve playground for interactive debugging

## Running the Examples

```bash
# Hooks example
PYTHONPATH=. python examples/10_observability/hooks.py

# Comprehensive tracing
PYTHONPATH=. python examples/10_observability/comprehensive_tracing.py

# Audit logging
PYTHONPATH=. python examples/10_observability/audit_logging.py
```

## What's Next?

- Learn about [context management](/core/context)
- Explore [guardrails](/agent/guardrails) for safety
- Understand [streaming](/agent/streaming) for real-time output

## See Also

- [Debugging overview](/debugging/overview)
- [Hooks reference](/debugging/hooks-reference)
- [Tracing documentation](/debugging/tracing)
