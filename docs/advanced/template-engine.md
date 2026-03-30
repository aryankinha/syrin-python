---
title: Template Engine
description: Structured generation with typed slots for reduced hallucination
weight: 250
---

## The Problem: Freeform Generation is Unpredictable

You need the LLM to output structured data — a JSON object, a specific report format, a ticket with defined fields. But:

- LLMs are creative, not precise
- JSON can be malformed
- Fields get mixed up
- Structured output mode works but has limitations

**The challenge:**
- You need machine-readable output
- LLMs generate natural text, not structured data
- Forcing JSON mode reduces quality
- You need flexibility, not just rigid schemas

**The solution:** Syrin's Template engine — Mustache-style templates with typed slots that constrain generation while keeping quality.

## Templates: Constrained Generation

Templates reduce hallucination by telling the LLM exactly what to fill in:

```python
from syrin.template import Template, SlotConfig

# Define template with slots
t = Template(
    name="weather_report",
    content="""
Weather Report for {{city}}:

Temperature: {{temperature}}°C
Condition: {{condition}}
Humidity: {{humidity}}%
Wind: {{wind_speed}} km/h

Generated on: {{date}}
""",
    slots={
        "city": SlotConfig("str", required=True),
        "temperature": SlotConfig("int", required=True),
        "condition": SlotConfig("str", required=True),
        "humidity": SlotConfig("int"),
        "wind_speed": SlotConfig("int"),
        "date": SlotConfig("str"),
    },
)

# Render with values
output = t.render(
    city="Tokyo",
    temperature=22,
    condition="Partly Cloudy",
    humidity=65,
    wind_speed=12,
    date="2024-01-15",
)
print(output)
```

**What just happened:**
1. You defined a template with named slots
2. Each slot has a type (str, int, float, bool)
3. Values are coerced to the correct type
4. The template is rendered with Mustache substitution

## How Templates Reduce Hallucination

Without a template:
```
User: What's the weather?
LLM: "Well, it's quite nice today in Tokyo. I'd say it's around 22 degrees with some clouds..." 
```

With a template:
```
User: Fill in this template for Tokyo weather
LLM: "Temperature: 22°C, Condition: Partly Cloudy, Humidity: 65%"
```

**Why it works:**
1. **Clear structure** — The LLM knows exactly what to produce
2. **Named fields** — No ambiguity about what data goes where
3. **Type constraints** — Numbers stay as numbers
4. **Slot boundaries** — Content is isolated per slot

## Mustache Syntax

Templates use Mustache-style syntax:

```python
# Variables
{{variable_name}}

# Sections (conditionals)
{{#has_items}}
Items: {{#items}}{{.}} {{/items}}
{{/has_items}}
{{^has_items}}
No items
{{/has_items}}

# Lists (iterate)
{{#users}}
- {{name}} ({{email}})
{{/users}}
```

### Variables

```python
t = Template(
    name="greeting",
    content="Hello, {{name}}! You have {{count}} messages.",
)

t.render(name="Alice", count=5)
# "Hello, Alice! You have 5 messages."
```

### Sections (Conditionals)

```python
t = Template(
    name="status",
    content="""
Status: {{status}}
{{#is_active}}
Active since: {{active_since}}
{{/is_active}}
{{^is_active}}
Inactive since: {{inactive_since}}
{{/is_active}}
""",
)

# With active
t.render(status="active", is_active=True, active_since="2024-01-01")
# Status: active
# Active since: 2024-01-01

# Without active
t.render(status="inactive", is_active=False, inactive_since="2024-02-01")
# Status: inactive
# Inactive since: 2024-02-01
```

### Lists

```python
t = Template(
    name="todo_list",
    content="""
Todo List:
{{#todos}}
{{#.}} - {{.}}
{{/.}}
{{/todos}}
""",
)

t.render(todos=["Buy milk", "Walk dog", "Call Mom"])
# Todo List:
# - Buy milk
# - Walk dog
# - Call Mom
```

## Slot Types

Define the expected type for each slot:

```python
from syrin.template import SlotConfig

slots = {
    # String (default)
    "name": SlotConfig("str", required=True),
    
    # Integer
    "age": SlotConfig("int"),
    "count": SlotConfig("int", default=0),
    
    # Float
    "price": SlotConfig("float"),
    "rating": SlotConfig("float", default=0.0),
    
    # Boolean
    "is_active": SlotConfig("bool"),
    "verified": SlotConfig("bool", default=False),
    
    # List of strings
    "tags": SlotConfig("list[str]"),
    
    # With defaults
    "priority": SlotConfig("str", default="normal"),
}
```

### Type Coercion

Values are automatically coerced:

```python
t.render(age="42")           # "42" → 42
t.render(price="19.99")      # "19.99" → 19.99
t.render(is_active="yes")     # "yes" → True
t.render(is_active="false")   # "false" → False
t.render(tags='["a", "b"]')   # JSON → ["a", "b"]
```

## Strict Mode

Enable strict mode to validate required slots:

```python
t = Template(
    name="invoice",
    content="Invoice #{{invoice_num}} for {{amount}}",
    slots={
        "invoice_num": SlotConfig("str", required=True),
        "amount": SlotConfig("float", required=True),
    },
    strict=True,  # Raise on missing required slots
)

# This raises ValueError
try:
    t.render(invoice_num="INV-001")  # Missing amount
except ValueError as e:
    print(f"Error: {e}")  # "Required slot 'amount' is missing"
```

## Loading Templates from Files

Store templates in files with YAML frontmatter:

```markdown
---
slots:
  user_name:
    type: str
    required: true
  email:
    type: str
    required: true
  age:
    type: int
  preferences:
    type: list[str]
---

User Registration Form:

Name: {{user_name}}
Email: {{email}}
Age: {{age}}

{{#preferences}}
Preference: {{.}}
{{/preferences}}
```

```python
from syrin.template import Template

# Load from file
t = Template.from_file("templates/user_form.md")

# Render
output = t.render(
    user_name="Alice",
    email="alice@example.com",
    age=30,
    preferences=["email", "sms"],
)
```

## Template Composition

Build complex templates from simple ones:

```python
from syrin.template import Template

# Base template
header = Template(
    name="header",
    content="{{title}}\n{{'=' * 40}}",
)

# Section template
section = Template(
    name="section",
    content="\n{{heading}}\n{{content}}",
)

# Combine in a layout
layout = Template(
    name="layout",
    content="{{header}}\n\n{{body}}\n\n{{footer}}",
)

# Build specific output
output = layout.render(
    header="User Report",
    body=section.render(heading="Profile", content="Alice, 30"),
    footer="Generated 2024-01-15",
)
```

## JSON Schema Generation

Templates generate JSON Schema for LLM extraction:

```python
t = Template(
    name="product",
    content="Product: {{name}}, Price: {{price}}",
    slots={
        "name": SlotConfig("str", required=True),
        "price": SlotConfig("float", required=True),
    },
)

# Get schema for structured output
schema = t.slot_schema()
print(schema)
# {
#     "type": "object",
#     "properties": {
#         "name": {"type": "string", "description": "Slot: name"},
#         "price": {"type": "number", "description": "Slot: price"},
#     },
#     "required": ["name", "price"],
# }
```

### Use with Agent

```python
from pydantic import BaseModel

class Product(BaseModel):
    name: str
    price: float

# Use schema for structured output
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="..."),
    system_prompt=f"""Extract product info into this format:
{t.render()}""",
)

# Or use Pydantic directly
agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="...").with_output(Product),
)
```

## Common Patterns

### 1. Report Generation

```python
report = Template(
    name="sales_report",
    content="""
Sales Report: {{period}}

Summary:
- Total Revenue: ${{total_revenue}}
- Orders: {{order_count}}
- Average Order: ${{avg_order}}

Top Products:
{{#top_products}}
{{#.}} {{name}} - {{revenue}} ({{count}} sold)
{{/.}}
{{/top_products}}

Generated: {{date}}
""",
    slots={
        "period": SlotConfig("str"),
        "total_revenue": SlotConfig("float"),
        "order_count": SlotConfig("int"),
        "avg_order": SlotConfig("float"),
        "top_products": SlotConfig("list[str]"),
        "date": SlotConfig("str"),
    },
)

# Extract data from database, render report
report.render(
    period="January 2024",
    total_revenue=125000.50,
    order_count=450,
    avg_order=277.78,
    top_products=[
        {"name": "Widget A", "revenue": 25000, "count": 100},
        {"name": "Widget B", "revenue": 18000, "count": 90},
    ],
    date="2024-02-01",
)
```

### 2. Ticket Creation

```python
ticket = Template(
    name="ticket",
    content="""
[Ticket #{{ticket_id}}]

Title: {{title}}
Priority: {{priority}}
Status: {{status}}

Description:
{{description}}

Reporter: {{reporter}}
Created: {{created_date}}
""",
    slots={
        "ticket_id": SlotConfig("str"),
        "title": SlotConfig("str", required=True),
        "priority": SlotConfig("str", default="medium"),
        "status": SlotConfig("str", default="open"),
        "description": SlotConfig("str"),
        "reporter": SlotConfig("str"),
        "created_date": SlotConfig("str"),
    },
)
```

### 3. API Response

```python
api_response = Template(
    name="api_response",
    content="""
{
    "success": {{success}},
    {{#data}}
    "data": {
        {{#name}}"name": "{{name}}",{{/name}}
        {{#email}}"email": "{{email}}"{{/email}}
    },
    {{/data}}
    {{#error}}
    "error": "{{error}}",
    {{/error}}
    "timestamp": "{{timestamp}}"
}
""",
    slots={
        "success": SlotConfig("bool"),
        "data": SlotConfig("bool"),  # Present if True
        "name": SlotConfig("str"),
        "email": SlotConfig("str"),
        "error": SlotConfig("str"),
        "timestamp": SlotConfig("str"),
    },
)
```

## Template Caching

For frequently used templates:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_template(name: str) -> Template:
    return Template.from_file(f"templates/{name}.md")


# First call loads and caches
t1 = get_template("user_form")

# Subsequent calls return cached
t2 = get_template("user_form")
assert t1 is t2
```

## Validation

Validate slot values before rendering:

```python
from typing import Any


def validate_template_data(template: Template, data: dict[str, Any]) -> list[str]:
    """Validate data against template slots."""
    errors = []
    
    for name, config in template.slots.items():
        if name not in data:
            if config.required:
                errors.append(f"Missing required slot: {name}")
            continue
        
        value = data[name]
        
        # Type validation
        if config.slot_type == "int" and not isinstance(value, int):
            if not isinstance(value, str):
                errors.append(f"Slot {name} must be int, got {type(value)}")
        elif config.slot_type == "float" and not isinstance(value, (int, float)):
            errors.append(f"Slot {name} must be numeric, got {type(value)}")
    
    return errors


# Usage
errors = validate_template_data(my_template, {"name": "Alice"})
if errors:
    print(f"Validation errors: {errors}")
else:
    output = my_template.render(...)
```

## Output Formatting Helpers

When you move from templates to file/output generation, the public output-format package also exposes `OutputConfig`, `OutputFormatter`, `CitationStyle`, `apply_citation_to_content()`, `get_formatter()`, `save_as()`, `save_as_pdf()`, and `save_as_docx()`.

## What's Next?

- [Structured Output](/agent-kit/agent/structured-output) — Pydantic-based output
- [Custom Model](/agent-kit/advanced/custom-model) — Custom LLM integration
- [Testing](/agent-kit/advanced/testing) — Test templates

## See Also

- [Prompts Overview](/agent-kit/core/prompts) — Prompt writing
- [Structured Output](/agent-kit/agent/structured-output) — JSON/Pydantic responses
- [Template Engine](/agent-kit/core/prompts-templates) — Basic templates
