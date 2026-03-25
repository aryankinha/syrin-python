---
title: Structured Output
description: Get typed, validated responses from your agents—not just text
weight: 81
---

## Structured Output: Getting Data, Not Just Text

You're building an AI-powered product. The agent extracts user information from emails. You need to save the name, email, and phone number to your database.

You call `agent.run()` and get back:

```
"Based on the email, the user's name is John Doe, their email is 
john@example.com, and their phone number is 555-123-4567."
```

Great. Now you need to parse that text to extract the fields. Regex? String splitting? GPT parsing?

What could go wrong?

**This is the structured output problem.** You want *data*, not prose. You want to save to a database, not parse strings.

## The Solution: Tell the Agent What Shape You Want

Syrin's structured output lets you define the exact data shape you need. The agent returns JSON that matches your schema, validated and parsed into Python objects.

```python
from pydantic import BaseModel
from syrin import Agent, Model, Output

class UserInfo(BaseModel):
    name: str
    email: str
    phone: str

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    output=Output(UserInfo, validation_retries=3),
)

result = agent.run(
    "Extract: John Doe, john@example.com, 555-123-4567"
)

# Direct access to typed data
print(result.parsed.name)    # "John Doe"
print(result.parsed.email)    # "john@example.com"
print(result.parsed.phone)    # "555-123-4567"
```

No parsing. No regex. Just data.

## Why This Matters

### The Problem with Text Responses

When you ask an agent for data, you get text:

```
"The user John Doe can be reached at john@example.com or by phone at 555-123-4567."
```

Parsing this is brittle:
- What if the order changes?
- What if there are multiple email mentions?
- What if the agent paraphrases?

Your code breaks. Users get errors. You debug parsing code forever.

### Structured Output: Contract-Based Responses

With structured output, you define a contract:

```python
class UserInfo(BaseModel):
    name: str
    email: str
    phone: str
```

The agent returns JSON that matches this shape. Syrin validates it. You get a Python object.

**If the validation fails**, Syrin retries automatically (up to your retry limit) and tells the agent what went wrong.

## Defining Output Schemas

### Using Pydantic Models (Recommended)

Pydantic gives you validation, type hints, and field descriptions:

```python
from pydantic import BaseModel, field_validator

class UserInfo(BaseModel):
    name: str
    email: str
    age: int
    
    @field_validator('age')
    @classmethod
    def age_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Age must be positive')
        return v

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    output=Output(UserInfo, validation_retries=3),
)
```

### Using the @structured Decorator

For simpler cases, use the `@structured` decorator:

```python
from syrin import Model, Agent, Output
from syrin.model import structured

@structured
class SentimentResult:
    sentiment: str  # "positive", "negative", "neutral"
    confidence: float  # 0.0 to 1.0
    explanation: str = ""  # Optional field

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    output=Output(SentimentResult, validation_retries=3),
)

result = agent.run("I absolutely love this product!")
print(result.parsed.sentiment)    # "positive"
print(result.parsed.confidence)   # 0.95
```

### Nested Types

For complex data, use nested structures:

```python
from syrin.model import structured
from typing import Annotated

@structured
class Address:
    street: str
    city: str
    country: str

@structured
class Person:
    name: str
    address: Address
    tags: list[str] = []

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    output=Output(Person),
)

result = agent.run(
    "John lives at 123 Main St in San Francisco, USA. Tags: VIP, enterprise"
)

print(result.parsed.name)              # "John"
print(result.parsed.address.city)      # "San Francisco"
print(result.parsed.tags)              # ["VIP", "enterprise"]
```

### Field Descriptions with Annotated

Use `Annotated` to add descriptions that help the LLM understand each field:

```python
from typing import Annotated
from syrin.model import structured

@structured
class ProductReview:
    rating: Annotated[int, "1-5 star rating"] = 0
    summary: Annotated[str, "Brief summary in 10 words"] = ""
    pros: Annotated[list[str], "List of pros"] = []
    cons: Annotated[list[str], "List of cons"] = []
```

## Validation and Retries

### How Validation Works

When you configure structured output:

1. **Agent generates JSON** matching your schema
2. **Syrin parses** the JSON from the response
3. **Syrin validates** against your Pydantic model
4. **If valid**: Returns the parsed object
5. **If invalid**: Retries with error feedback (up to `validation_retries` times)

### Configuring Retries

```python
from syrin import Agent, Model, Output

class UserInfo(BaseModel):
    name: str
    email: str

# Fewer retries = faster, less correction
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    output=Output(UserInfo, validation_retries=1),  # Fast but less robust
)

# More retries = slower, more correction
agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    output=Output(UserInfo, validation_retries=5),  # Slower but more robust
)
```

### Checking Validation Results

```python
result = agent.run("Extract info...")

# Did validation succeed?
if result.structured.is_valid:
    print(result.parsed.name)
else:
    # Debug: see what went wrong
    print(f"Failed: {result.structured.final_error}")
    for attempt in result.structured.validation_attempts:
        print(f"  Attempt {attempt.attempt}: {attempt.error}")
```

## Custom Validators

For business logic beyond Pydantic, use custom validators:

```python
from pydantic import BaseModel
from syrin import Agent, Model, Output
from syrin.types.validation import (
    OutputValidator,
    ValidationAction,
    ValidationContext,
    ValidationResult,
)

class ReviewResult(BaseModel):
    rating: int
    summary: str

class RatingValidator(OutputValidator):
    max_retries = 3

    def validate(self, output: object, context: ValidationContext) -> ValidationResult:
        data = output.model_dump() if hasattr(output, "model_dump") else {}
        
        rating = data.get("rating", 0)
        if rating < 1 or rating > 5:
            return ValidationResult.invalid(
                message=f"Rating {rating} out of range 1-5",
                action=ValidationAction.RETRY,
            )
        
        return ValidationResult.valid(output)

    def on_retry(self, error: str, attempt: int) -> str:
        return f"Error: {error}. Please fix and retry."

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    output=Output(ReviewResult, validator=RatingValidator()),
)
```

## Observability: Validation Hooks

Track validation in real-time with hooks:

```python
from syrin import Agent, Model, Hook

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    output=Output(UserInfo, validation_retries=3),
)

def on_validation_start(ctx: dict) -> None:
    print(f"Validating output for: {ctx['output_type']}")

def on_validation_success(ctx: dict) -> None:
    print(f"Validation succeeded at attempt {ctx['attempt']}")

def on_validation_failed(ctx: dict) -> None:
    print(f"Validation failed: {ctx['error']}")
    print(f"Reason: {ctx['reason']}")

agent.events.on(Hook.OUTPUT_VALIDATION_START, on_validation_start)
agent.events.on(Hook.OUTPUT_VALIDATION_SUCCESS, on_validation_success)
agent.events.on(Hook.OUTPUT_VALIDATION_FAILED, on_validation_failed)
```

## Complete Example: Data Extraction Pipeline

```python
from pydantic import BaseModel
from syrin import Agent, Model, Output

class ExtractedContact(BaseModel):
    name: str
    email: str
    company: str | None = None
    role: str | None = None

class InvoiceData(BaseModel):
    invoice_number: str
    amount: float
    currency: str
    date: str
    line_items: list[dict]

class DocumentResult(BaseModel):
    contact: ExtractedContact
    invoice: InvoiceData
    summary: str

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    output=Output(DocumentResult, validation_retries=3),
)

# Extract structured data from a document
result = agent.run(
    "Extract from the attached document: contact info, invoice details, "
    "and a brief summary."
)

# Direct access to nested data
print(f"Contact: {result.parsed.contact.name}")
print(f"Invoice: {result.parsed.invoice.amount} {result.parsed.invoice.currency}")
print(f"Summary: {result.parsed.summary}")

# Save to database
db.save_contact(result.parsed.contact)
db.save_invoice(result.parsed.invoice)
```

## Common Patterns

### Pattern 1: List of Items

```python
from pydantic import BaseModel

class TodoItem(BaseModel):
    task: str
    priority: str  # "high", "medium", "low"
    done: bool

class TodoList(BaseModel):
    items: list[TodoItem]

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    output=Output(TodoList),
)

result = agent.run(
    "Convert to todos: Buy groceries (high), Call mom (medium), "
    "Finish report (high), Watch movie (low)"
)

for item in result.parsed.items:
    print(f"[{'x' if item.done else ' '}] {item.task} ({item.priority})")
```

### Pattern 2: Classification

```python
from pydantic import BaseModel
from enum import Enum

class Category(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    QUESTION = "question"

class TicketClassification(BaseModel):
    category: Category
    priority: str  # "urgent", "normal", "low"
    suggested_department: str

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    output=Output(TicketClassification),
)

result = agent.run(
    "Classify this: 'The login button doesn't work on mobile devices'"
)

print(result.parsed.category)              # Category.BUG
print(result.parsed.priority)            # "urgent"
print(result.parsed.suggested_department) # "mobile-team"
```

### Pattern 3: Formatted Output

```python
from pydantic import BaseModel

class CodeReview(BaseModel):
    rating: int  # 1-10
    issues: list[str]
    suggestions: list[str]
    approved: bool

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    output=Output(CodeReview, validation_retries=2),
)

result = agent.run(
    "Review this code and rate it 1-10, list issues and suggestions, "
    "and say if it should be approved."
)

if result.parsed.approved:
    print("Code approved!")
else:
    print("Issues to fix:")
    for issue in result.parsed.issues:
        print(f"  - {issue}")
```

## Troubleshooting

### Validation keeps failing

1. **Check your schema** — Are required fields clearly defined?
2. **Add field descriptions** — Help the LLM understand what you want
3. **Increase retries** — More attempts = better corrections
4. **Simplify the schema** — Complex nested schemas are harder

```python
# Good: Clear descriptions
class UserInfo(BaseModel):
    name: str  # Full name as it appears in the text
    email: str  # Valid email address
```

### Type mismatch errors

Make sure your Python types match what the agent can generate:

```python
# Good: Simple types
name: str
count: int
active: bool

# Careful: Lists need clear item types
items: list[str]  # List of strings
```

## What's Next?

- [Streaming](/agent/streaming) — Real-time responses for chat UIs
- [Tools](/agent/tools) — Extend agent capabilities
- [Guardrails](/agent/guardrails) — Validate input/output content

## See Also

- [Response Object](/agent/response-object) — Full Response breakdown
- [Agent Configuration](/agent/agent-configuration) — All configuration options
- [Hooks Reference](/debugging/hooks-reference) — Validation hooks
