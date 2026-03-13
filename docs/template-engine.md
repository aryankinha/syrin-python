# Template Engine

Template-based generation constrains LLM output to filling predefined slots, reducing hallucination for structured documents (financial reports, legal filings, compliance forms). Use with `output_config` on Agent.

## Overview

- **Standalone:** `Template.render(**kwargs)` — render templates with explicit slot values
- **Agent integration:** `output_config=OutputConfig(format=..., template=...)` — structured output fills template slots and `response.content` is the rendered text; file generation produces `response.file` and `response.file_bytes`
- **Syntax:** Mustache-style — `{{variable}}`, `{{#section}}...{{/section}}`, `{{#list}}{{.}}{{/list}}` (use `{{.}}` for current element in iteration)

## Basic Usage

### Standalone

```python
from syrin import Template, SlotConfig

tpl = Template(
    name="capital",
    content="Authorized: {{amount}} at face value {{face_value}}",
    slots={
        "amount": SlotConfig("str", required=True),
        "face_value": SlotConfig("str", required=False, default="₹10"),
    },
)
print(tpl.render(amount="₹50,00,000"))
# Authorized: ₹50,00,000 at face value ₹10
```

### With Agent

```python
from pydantic import BaseModel
from syrin import Agent, Output, OutputConfig, OutputFormat, SlotConfig, Template
from syrin.model import Model

class CapitalData(BaseModel):
    amount: str
    face_value: str

tpl = Template(
    "capital",
    "Authorized: {{amount}}, Face value: {{face_value}}",
    slots={"amount": SlotConfig("str"), "face_value": SlotConfig("str")},
)

agent = Agent(
    model=Model.OpenAI("gpt-4o"),
    system_prompt="Extract capital data. Return JSON.",
    output=Output(CapitalData),
    output_config=OutputConfig(format=OutputFormat.TEXT, template=tpl),
)

response = agent.response("From the memo: Authorized capital ₹50L, face value ₹10")
print(response.content)       # Authorized: ₹50,00,000, Face value: ₹10
print(response.template_data) # {"amount": "₹50,00,000", "face_value": "₹10"}
print(response.file)          # Path to generated .txt file (when output_config format set)
```

**Note:** When using a template with Agent, you must set `output=Output(SomeModel)`. Structured output provides the slot values.

## Slot Configuration

| Type        | JSON Schema      | Example                             |
| ----------- | ---------------- | ----------------------------------- |
| `str`       | string           | `SlotConfig("str")`                 |
| `int`       | integer          | `SlotConfig("int", required=True)`  |
| `float`     | number           | `SlotConfig("float")`               |
| `bool`      | boolean          | `SlotConfig("bool", default=False)` |
| `list[str]` | array of strings | `SlotConfig("list[str]")`           |

Or use a dict:

```python
slots={
    "amount": {"type": "str", "required": True},
    "items": {"type": "list[str]", "required": False, "default": []},
}
```

## Conditionals and Iteration

- **Section (truthy):** `{{#show}}Visible{{/show}}` — renders when `show` is truthy
- **Section (falsy):** `{{^show}}Hidden{{/show}}` — renders when `show` is falsy (inverted)
- **List iteration:** `{{#items}}{{.}}, {{/items}}` — `{{.}}` is the current element

## Strict Mode

```python
Template("x", "{{a}}", slots={"a": SlotConfig("str", required=True)}, strict=True)
# render() raises ValueError if required slot "a" is missing
```

## Factory Methods

```python
# From file (name defaults to file stem)
tpl = Template.from_file("templates/capital.md", slots={...})

# From string
tpl = Template.from_string("Hi {{name}}", name="greet", slots={"name": SlotConfig("str")})
```

### YAML Frontmatter

Templates loaded from files can define slots via YAML frontmatter:

```yaml
# templates/capital.md
---
name:
  type: str
  required: true
amount:
  type: int
  required: false
  default: 0
---
Authorized capital: {{name}} = ₹{{amount}}
```

```python
tpl = Template.from_file("templates/capital.md")
# Slots are auto-parsed from frontmatter!
tpl.slots["name"].required  # True
tpl.render(name="Test", amount=50000)  # "Authorized capital: Test = ₹50000"
```

Explicit `slots` parameter overrides frontmatter slots:

## slot_schema()

Returns a JSON schema for slots (useful for prompting the LLM):

```python
schema = tpl.slot_schema()
# {"type": "object", "properties": {...}, "required": [...]}
```

## See Also

- [Agent: Structured Output](agent/structured-output.md) — `output=Output(MyModel)`
- [Agent: Response](agent/response.md) — `response.content`, `response.template_data`
