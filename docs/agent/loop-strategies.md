# Loop Strategies

The **loop** controls how the agent iterates: one-shot LLM call vs multi-step tool use, approval flows, planning, or code execution.

## Built-in Strategies

### ReactLoop (Default)

Think → Act → Observe. Supports tool calls and multiple iterations.

**Use for:** General agents with tools.

```python
from syrin import Agent
from syrin.loop import ReactLoop

agent = Agent(
    model=model,
    tools=[search, calculate],
    loop=ReactLoop(max_iterations=10),
)
```

**Behavior:** LLM → tool calls (if any) → feed results back → repeat until no tools or max iterations.

---

### SingleShotLoop

Single LLM call, no tool loop.

**Use for:** Simple Q&A, no tools.

```python
from syrin.enums import LoopStrategy

agent = Agent(
    model=model,
    loop_strategy=LoopStrategy.SINGLE_SHOT,
)
```

---

### HumanInTheLoop

User approval before each tool execution.

**Use for:** High-safety or high-stakes tool use.

```python
from syrin.loop import HumanInTheLoop

async def approve(tool_name: str, arguments: dict) -> bool:
    print(f"Allow {tool_name}({arguments})? (y/n)")
    # In real app: prompt user, call API, etc.
    return True

agent = Agent(
    model=model,
    tools=[search],
    loop=HumanInTheLoop(approve=approve, max_iterations=10),
)
```

If approval returns `False`, the tool is not run and the model receives a refusal message.

---

### PlanExecuteLoop

First plans steps, then executes them.

**Use for:** Structured multi-step tasks.

```python
from syrin.loop import PlanExecuteLoop

agent = Agent(
    model=model,
    tools=[search, write],
    loop=PlanExecuteLoop(
        max_plan_iterations=5,
        max_execution_iterations=20,
    ),
)
```

---

### CodeActionLoop

Generates Python code, runs it, and uses the output for the final answer.

**Use for:** Math, data processing, code generation.

```python
from syrin.loop import CodeActionLoop

agent = Agent(
    model=model,
    loop=CodeActionLoop(max_iterations=10, timeout_seconds=60),
)
```

---

## Choosing a Loop

| loop_strategy | Use case |
|---------------|----------|
| `REACT` | General agents with tools |
| `SINGLE_SHOT` | Simple Q&A, no tools |
| `PLAN_EXECUTE` | Multi-step workflows |
| `CODE_ACTION` | Code execution, calculations |

## Via `loop_strategy`

```python
from syrin.enums import LoopStrategy

agent = Agent(
    model=model,
    loop_strategy=LoopStrategy.SINGLE_SHOT,
)
```

`loop_strategy` is used when `loop` is not passed.

## Via `loop`

```python
from syrin.loop import ReactLoop, HumanInTheLoop

agent = Agent(
    model=model,
    loop=ReactLoop(max_iterations=5),
)
```

## max_tool_iterations

`max_tool_iterations` (default `10`) limits the tool loop. It is passed into `ReactLoop`, `HumanInTheLoop`, and `CodeActionLoop`:

```python
agent = Agent(
    model=model,
    tools=[search],
    max_tool_iterations=5,
)
```

---

## Custom Loop

Implement a loop by subclassing `Loop` and defining `run()`:

```python
from syrin.loop import Loop, LoopResult

class MyCustomLoop(Loop):
    name = "my_loop"

    async def run(self, agent, user_input: str) -> LoopResult:
        messages = agent._build_messages(user_input)
        response = await agent.complete(messages)
        return LoopResult(
            content=response.content or "",
            stop_reason=response.stop_reason or "end_turn",
            iterations=1,
            cost_usd=calculate_cost(...),
            latency_ms=...,
            token_usage={"input": ..., "output": ..., "total": ...},
            tool_calls=[],
        )

agent = Agent(model=model, loop=MyCustomLoop())
```

### LoopResult

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Final text |
| `stop_reason` | `str` | Why the run stopped |
| `iterations` | `int` | Loop iterations |
| `tools_used` | `list[str]` | Tool names called |
| `cost_usd` | `float` | Total cost |
| `latency_ms` | `float` | Duration in ms |
| `token_usage` | `dict` | `{"input", "output", "total"}` |
| `tool_calls` | `list[dict]` | Tool call data |
| `raw_response` | `Any` | Raw provider response |

---

## LoopStrategyMapping

Use `LoopStrategyMapping` to create loops from strategy names:

```python
from syrin.loop import LoopStrategyMapping
from syrin.enums import LoopStrategy

loop = LoopStrategyMapping.create_loop(LoopStrategy.REACT, max_iterations=5)
```
