---
title: Tools & Structured Output
description: Define tools with TOON format and get typed responses
weight: 320
---

## Tools & Structured Output

Tools extend agent capabilities with custom functions. Structured output ensures agents return typed, validated data.

## Defining Tools

Use the `@tool` decorator to create agent tools.

```python
from syrin import Agent, Model, tool

@tool
def calculate(a: float, b: float, operation: str = "add") -> str:
    """Perform basic arithmetic operations.
    
    Args:
        a: First number
        b: Second number
        operation: One of add, subtract, multiply, divide
    """
    ops = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b if b else 0
    }
    return str(ops.get(operation, "Unknown"))

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    tools=[calculate],
    system_prompt="Use the calculate tool for math problems.",
)

result = agent.run("What is 25 times 4?")
print(result.content)  # "The result of 25 × 4 is 100."
```

**What just happened:**
1. Defined a tool with parameters and docstring
2. Registered it with the agent
3. The agent intelligently called `calculate(25, 4, "multiply")`
4. Got back a natural language response incorporating the result

## TOON Format: 40% Fewer Tokens

TOON (Token-Oriented Object Notation) generates compact tool schemas.

```python
from syrin import tool
from syrin.enums import DocFormat

@tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for information.
    
    Args:
        query: The search query
        max_results: Max results (1-10)
    """
    return f"Found {max_results} results"

# Compare JSON vs TOON
json_schema = search_web.to_format(DocFormat.JSON)
toon_schema = search_web.to_format(DocFormat.TOON)

print(f"JSON: {len(str(json_schema))} chars")
print(f"TOON: {len(str(toon_schema))} chars")
# TOON typically uses 40% fewer tokens
```

**What just happened:**
1. Generated both JSON and TOON schemas from the same tool
2. Saw that TOON is significantly more compact
3. This matters for API costs with many tools

## Structured Output with `@structured`

Get typed, validated responses from agents.

```python
from typing import Annotated
from syrin import Agent, Model, Output
from syrin.model import structured

@structured
class UserInfo:
    name: str
    email: str
    age: int
    city: str

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    output=Output(UserInfo, validation_retries=3),
)

result = agent.run("John Doe, 35, john@example.com, San Francisco")

# Access parsed data
if result.structured.is_valid:
    print(result.parsed.name)      # "John Doe"
    print(result.parsed.email)     # "john@example.com"
    print(result.parsed.age)      # 35
```

**What just happened:**
1. Defined a structured type with `@structured`
2. Set `validation_retries=3` for automatic correction
3. The agent output was parsed into a typed object
4. Checked `is_valid` and accessed `.parsed` data

## Nested Structured Types

Complex hierarchies with nested classes.

```python
from typing import Annotated
from syrin import Agent, Model, Output
from syrin.model import structured

@structured
class Shareholder:
    name: str
    percentage: float
    shares: int

@structured
class CapitalStructure:
    authorized_capital: Annotated[str, "Total authorized capital in Cr"]
    shareholders: list[Shareholder]
    missing_fields: Annotated[list[str], "Data not found"] = []

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    output=Output(CapitalStructure, validation_retries=3),
)

result = agent.run(
    "Authorized capital: 5 Cr. "
    "Promoter group: 62.5% (12.5L shares). "
    "Public: 37.5% (7.5L shares)."
)

if result.structured.is_valid:
    print(result.parsed.authorized_capital)  # "5 Cr"
    for sh in result.parsed.shareholders:
        print(f"{sh.name}: {sh.percentage}%")
```

**What just happened:**
1. Defined nested structured types with relationships
2. Used `Annotated` for field descriptions the LLM understands
3. Got back a complete typed hierarchy
4. Default values work for missing fields

## Pydantic Models as Output

Use Pydantic for advanced validation.

```python
from pydantic import BaseModel, field_validator
from syrin import Agent, Model, Output

class ProductInfo(BaseModel):
    name: str
    price: float
    in_stock: bool
    category: str

class RestrictedUser(BaseModel):
    name: str
    email: str
    role: str
    
    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        allowed = ["admin", "user", "guest"]
        if v.lower() not in allowed:
            raise ValueError(f"Role must be one of: {allowed}")
        return v.lower()

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    output=Output(ProductInfo, validation_retries=3),
)

result = agent.run("Product: Widget Pro, $299.99, in stock, electronics")
print(result.parsed)  # ProductInfo(name='Widget Pro', price=299.99, ...)
```

**What just happened:**
1. Used Pydantic for field validation
2. Got automatic type coercion (string "299.99" → float 299.99)
3. Custom validators ensure business rules

## Custom Validators

Implement `OutputValidator` for business logic validation.

```python
from syrin import Agent, Model, Output
from syrin.types.validation import (
    OutputValidator,
    ValidationAction,
    ValidationContext,
    ValidationResult,
)

class ReviewResult(BaseModel):
    rating: int
    sentiment: str
    summary: str

class RatingValidator(OutputValidator):
    max_retries = 3
    
    def validate(self, output: object, context: ValidationContext) -> ValidationResult:
        data = output if isinstance(output, dict) else output.model_dump()
        
        rating = data.get("rating", 0)
        if rating < 1 or rating > 5:
            return ValidationResult.invalid(
                message=f"Rating {rating} out of range 1-5",
                action=ValidationAction.RETRY,
            )
        
        sentiment = data.get("sentiment", "").lower()
        if sentiment not in ["positive", "negative", "neutral"]:
            return ValidationResult.invalid(
                message=f"Invalid sentiment: {sentiment}",
                action=ValidationAction.RETRY,
            )
        
        return ValidationResult.valid(output)

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    output=Output(ReviewResult, validator=RatingValidator()),
)

result = agent.run("Review: 'Amazing product!' rating 5, positive")
```

**What just happened:**
1. Created a custom validator checking business rules
2. Used `ValidationAction.RETRY` to request corrections
3. The agent gets feedback and retries automatically

## Validation Hooks

Monitor validation lifecycle with hooks.

```python
from syrin import Agent, Model, Output
from syrin.enums import Hook

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-api-key"),
    output=Output(SentimentResult, validation_retries=3),
)

def on_validation_start(ctx):
    print(f"Validating output type: {ctx.output_type}")

agent.events.on(Hook.OUTPUT_VALIDATION_START, on_validation_start)

def on_validation_success(ctx):
    print(f"Validation succeeded on attempt {ctx.attempt}")

agent.events.on(Hook.OUTPUT_VALIDATION_SUCCESS, on_validation_success)

def on_validation_failed(ctx):
    print(f"Validation failed: {ctx.reason}")

agent.events.on(Hook.OUTPUT_VALIDATION_FAILED, on_validation_failed)

result = agent.run("Analyze: 'This product is okay.'")
```

**What just happened:**
1. Hooked into validation lifecycle events
2. Tracked attempt count and failure reasons
3. Observed how retries work in practice

## Running the Examples

```bash
# Tool definition examples
PYTHONPATH=. python examples/05_tools/toon_format.py

# Structured output examples
PYTHONPATH=. python examples/05_tools/structured_output.py
```

## What's Next?

- Explore [multi-agent patterns](/agent-kit/examples/multi-agent-patterns) for collaboration
- Learn about [guardrails](/agent-kit/agent/guardrails) for safety
- Understand [loop strategies](/agent-kit/agent/running-agents) for control

## See Also

- [Tools documentation](/agent-kit/agent/tools)
- [Structured output](/agent-kit/agent/structured-output)
- [Guardrails documentation](/agent-kit/agent/guardrails)
