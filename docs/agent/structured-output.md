---
title: Structured Output
description: Get typed Python objects back from your agent instead of free-form text
weight: 81
---

## The Problem with Text

Your agent is extracting contact information from customer emails. You call `agent.run()` and get:

```
"The customer's name appears to be John Doe. Their email address is john@example.com."
```

Great. Now parse that. What if the model phrases it differently next time? What if the name appears twice? What if it says "email:" vs "email address:"?

You end up writing fragile string parsers that break the moment the model changes its wording. This is a solved problem. It's called structured output.

## The Solution: Define a Schema

Tell the agent what shape you want back, and it returns a validated Python object instead of free text.

```python
from syrin import Agent, Model, Output
from pydantic import BaseModel

class ContactInfo(BaseModel):
    name: str
    email: str
    phone: str

# NOTE: Model.mock() cannot return structured output — it returns lorem ipsum, not JSON.
# The examples below use response_mode='custom' to simulate a real model.
# In production, use Model.OpenAI(), Model.Anthropic(), etc.
import json
mock_response = json.dumps({
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "555-123-4567"
})

agent = Agent(
    model=Model.mock(response_mode='custom', custom_response=mock_response),
    system_prompt="Extract contact information from the text.",
    output=Output(ContactInfo),
)

response = agent.run("Hi, I'm John Doe, reach me at john@example.com or 555-123-4567")

print(response.output.name)   # John Doe
print(response.output.email)  # john@example.com
print(response.output.phone)  # 555-123-4567
```

Output:

```
John Doe
john@example.com
555-123-4567
```

`response.output` is a fully validated `ContactInfo` instance. Not a dict, not a string — a real Python object with type checking, IDE autocomplete, and everything. This is the canonical way to access structured output.

## Two Ways to Define a Schema

### Option 1: Pydantic Models (Recommended)

Pydantic is the standard for data validation in Python. Define your schema as a `BaseModel` subclass, and you get field validation, type coercion, and field descriptions for free:

```python
from pydantic import BaseModel, field_validator
from syrin import Agent, Model, Output
import json

class ProductReview(BaseModel):
    rating: int      # 1–5 stars
    summary: str     # One-sentence summary
    pros: list[str]  # What's good
    cons: list[str]  # What's not

    @field_validator('rating')
    @classmethod
    def rating_in_range(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError(f'Rating must be 1-5, got {v}')
        return v

mock = json.dumps({
    "rating": 5,
    "summary": "Outstanding build quality and performance",
    "pros": ["Fast", "Quiet", "Beautiful design"],
    "cons": ["Expensive", "Limited ports"]
})

agent = Agent(
    model=Model.mock(response_mode='custom', custom_response=mock),
    system_prompt="Analyze product reviews and extract structured feedback.",
    output=Output(ProductReview, validation_retries=3),
)

response = agent.run("This laptop is incredible. Fast, quiet, gorgeous. A bit pricey but worth it.")

review = response.output
print(f"Rating: {review.rating}/5")
print(f"Summary: {review.summary}")
print(f"Pros: {', '.join(review.pros)}")
```

Output:

```
Rating: 5/5
Summary: Outstanding build quality and performance
Pros: Fast, Quiet, Beautiful design
```

### Option 2: @structured Decorator

For simpler cases, import `structured` from `syrin.model` and decorate a plain Python class. No Pydantic required:

```python
from syrin.model import structured
from syrin import Agent, Model, Output
import json

@structured
class SentimentResult:
    sentiment: str   # "positive", "negative", or "neutral"
    confidence: float  # 0.0 to 1.0
    reason: str = ""   # Optional explanation

mock = json.dumps({
    "sentiment": "positive",
    "confidence": 0.95,
    "reason": "Strong positive language throughout"
})

agent = Agent(
    model=Model.mock(response_mode='custom', custom_response=mock),
    system_prompt="Analyze the sentiment of the text.",
    output=Output(SentimentResult),
)

response = agent.run("I absolutely love this product! Best purchase I've ever made!")

print(f"Sentiment: {response.output.sentiment}")
print(f"Confidence: {response.output.confidence}")
print(f"Reason: {response.output.reason}")
```

Output:

```
Sentiment: positive
Confidence: 0.95
Reason: Strong positive language throughout
```

The `@structured` decorator is syntactic sugar for common use cases. For anything with custom validators or complex field types, use Pydantic.

## The Output Object

`Output(schema, validation_retries=3)` wraps your schema with settings:

```python
from syrin import Output
from pydantic import BaseModel

class UserInfo(BaseModel):
    name: str
    email: str

# Default: 3 retries
output = Output(UserInfo)

# More retries for unreliable models
output = Output(UserInfo, validation_retries=5)

# Strict mode: no extra fields allowed
output = Output(UserInfo, strict=True)
```

`validation_retries` is how many times Syrin will ask the model to fix its output if the JSON doesn't match your schema. More retries means more reliable output at the cost of extra LLM calls.

## How Validation Works

When you run an agent with structured output, Syrin does this:

1. The LLM generates a JSON response matching your schema
2. Syrin parses the JSON
3. Syrin validates it against your Pydantic model
4. If it passes: `response.output` contains your object
5. If it fails: Syrin sends the error back to the LLM and asks it to fix the output
6. This repeats up to `validation_retries` times
7. If it still fails after all retries: `OutputValidationError` is raised

This means that with a high enough retry count and a capable model, you almost never get a validation failure in production.

## Nested Schemas

For complex data, nest schemas inside each other:

```python
from pydantic import BaseModel
from syrin import Agent, Model, Output
import json

class Address(BaseModel):
    street: str
    city: str
    country: str

class Person(BaseModel):
    name: str
    age: int
    address: Address
    skills: list[str]

mock = json.dumps({
    "name": "Alice Chen",
    "age": 32,
    "address": {
        "street": "123 Main St",
        "city": "San Francisco",
        "country": "USA"
    },
    "skills": ["Python", "Machine Learning", "Systems Design"]
})

agent = Agent(
    model=Model.mock(response_mode='custom', custom_response=mock),
    system_prompt="Extract person details from the bio.",
    output=Output(Person),
)

response = agent.run("Alice Chen, 32, SF-based ML engineer...")

person = response.output
print(f"Name: {person.name}")
print(f"City: {person.address.city}")
print(f"Skills: {', '.join(person.skills)}")
```

Output:

```
Name: Alice Chen
City: San Francisco
Skills: Python, Machine Learning, Systems Design
```

## Important: Mock Model and Structured Output

The `Model.mock()` mock model returns lorem ipsum text, not JSON. Running structured output with a plain `Model.mock()` will raise `OutputValidationError` after exhausting all retries:

```python
from syrin import Agent, Model, Output
from syrin.exceptions import OutputValidationError
from pydantic import BaseModel

class UserInfo(BaseModel):
    name: str
    email: str

agent = Agent(
    model=Model.mock(),  # Returns lorem ipsum — NOT valid JSON
    system_prompt="Extract user info.",
    output=Output(UserInfo, validation_retries=2),
)

try:
    response = agent.run("John Doe, john@example.com")
except OutputValidationError:
    print("OutputValidationError raised — Model.mock() can't produce structured output")
```

Output:

```
OutputValidationError raised — Model.mock() can't produce structured output
```

For testing structured output logic without a real API key, use `response_mode='custom'` with a JSON string as shown in the examples above. For real usage, use `Model.OpenAI()`, `Model.Anthropic()`, or any provider that returns actual completions.

## Common Patterns

### Classify Incoming Requests

```python
from pydantic import BaseModel
from syrin import Agent, Model, Output

class TicketClassification(BaseModel):
    category: str    # "bug", "feature", "billing", "general"
    priority: str    # "urgent", "normal", "low"
    department: str  # Which team should handle this
    summary: str     # One-line summary for the queue

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-key"),
    system_prompt="Classify support tickets. Be precise with categories.",
    output=Output(TicketClassification, validation_retries=3),
)

response = agent.run("The checkout button is broken on mobile, customers can't pay!")
print(f"Category: {response.output.category}")
print(f"Priority: {response.output.priority}")
```

### Extract Lists of Items

```python
from pydantic import BaseModel
from syrin import Agent, Model, Output

class Task(BaseModel):
    title: str
    priority: str
    done: bool = False

class TaskList(BaseModel):
    tasks: list[Task]

agent = Agent(
    model=Model.OpenAI("gpt-4o-mini", api_key="your-key"),
    system_prompt="Convert meeting notes into a structured task list.",
    output=Output(TaskList),
)

response = agent.run(
    "Meeting notes: Need to fix the login bug (urgent), update docs (normal), "
    "call vendor about contract (low priority)"
)

for task in response.output.tasks:
    status = "done" if task.done else "todo"
    print(f"[{status}] {task.title} ({task.priority})")
```

### Build a Data Extraction Pipeline

```python
from pydantic import BaseModel
from syrin import Agent, Model, Output

class InvoiceData(BaseModel):
    invoice_number: str
    vendor: str
    amount: float
    currency: str
    due_date: str
    line_items: list[str]

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-key"),
    system_prompt="Extract invoice data from documents. Return all amounts as numbers.",
    output=Output(InvoiceData, validation_retries=3),
)

response = agent.run("Invoice #INV-2024-001 from Acme Corp, due March 15...")
invoice = response.output

print(f"Invoice: {invoice.invoice_number}")
print(f"Amount: {invoice.amount} {invoice.currency}")
print(f"Due: {invoice.due_date}")
```

## Troubleshooting

**Validation keeps failing:** The most common cause is an overly complex schema. Simplify nested types, add field descriptions as comments in the class, and increase `validation_retries`.

**Type mismatch errors:** Make sure your Python types match what a language model can reasonably produce. `str`, `int`, `float`, `bool`, `list[str]` are safe. Very complex types with custom serialization can confuse the model.

**OutputValidationError in production:** Either increase `validation_retries`, simplify your schema, or use a more capable model.

## What's Next

- [Streaming](/agent-kit/agent/streaming) — Stream partial responses as the model generates them
- [Tools](/agent-kit/agent/tools) — Let the agent call external functions
- [Response Object](/agent-kit/agent/response-object) — All the fields on the Response
