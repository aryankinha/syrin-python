# Structured Output

> **Full guide:** For Output config, validation retries, custom validators, and Model-level usage, see [Structured Output](../structured-output.md).

Return validated, typed outputs (e.g. Pydantic models) instead of plain text.

## Basic Usage

```python
from pydantic import BaseModel
from syrin import Agent
from syrin.output import Output

class UserInfo(BaseModel):
    name: str
    age: int
    email: str

agent = Agent(
    model=model,
    output=Output(type=UserInfo),
)

response = agent.response("Extract: John, 30, john@example.com")
print(response.structured.parsed)  # UserInfo(name="John", age=30, email="john@example.com")
print(response.data)               # {"name": "John", "age": 30, "email": "john@example.com"}
```

## Output Configuration

```python
Output(
    type=MyModel,              # Pydantic model
    validation_retries=3,      # Retries on validation failure
    context={},                # Extra context for validators
    validator=my_validator,    # Custom validator
    strict=False,              # Strict validation mode
)
```

### Shorthand

```python
agent = Agent(model=model, output=Output(UserInfo))
```

## Response Access

| Attribute | Description |
|-----------|-------------|
| `response.parsed` | Convenience: parsed instance (same as `structured.parsed`) |
| `response.structured.parsed` | Parsed Pydantic model |
| `response.structured.raw` | Raw JSON string |
| `response.structured._data` | Parsed dict |
| `response.data` | Alias for `structured._data` |
| `response.structured.is_valid` | Validation succeeded |
| `response.structured.final_error` | Last validation error |
| `response.structured.validation_attempts` | All attempts |

## Validation and Retries

If validation fails, the agent retries up to `validation_retries` times. After retries, `parsed` may be `None` and `final_error` is set.

```python
if response.structured.is_valid:
    user = response.structured.parsed
else:
    print(response.structured.final_error)
```

## Custom Validator

```python
from syrin.types.validation import OutputValidator

class MyValidator:
    def validate(self, output, context):
        if not meets_requirements(output):
            return ValidationResult.invalid(message="...", action=ValidationAction.RETRY)
        return ValidationResult.valid(output)

agent = Agent(
    model=model,
    output=Output(type=UserInfo, validator=MyValidator()),
)
```

## Using @structured

For schema generation with nested types and Annotated descriptions:

```python
from typing import Annotated

from syrin import Agent, Output
from syrin.model import structured

@structured
class Shareholder:
    name: str
    category: str
    shares: int
    percentage: float

@structured
class CapitalStructure:
    authorized_capital: Annotated[str, "Total authorized capital in ₹"]
    shareholders: list[Shareholder]
    missing_fields: Annotated[list[str], "Data not found in source documents"] = []

agent = Agent(model=model, output=Output(CapitalStructure))
response = agent.response("Extract capital structure")
print(response.parsed)  # CapitalStructure instance
```

- **Nested types:** `list[Shareholder]` produces proper JSON schema with `$defs`
- **Annotated:** `Annotated[T, "description"]` adds field descriptions for the LLM
- **Optional fields:** `Optional[T] = None` or default values make fields optional

## Report

Output validation is reflected in `response.report.output`:

- `validated` — Validation was attempted
- `attempts` — Number of attempts
- `is_valid` — Validation succeeded
- `final_error` — Error message if failed

## Template Integration

Combine structured output with templates for slot-based document generation:

```python
from syrin import OutputConfig, OutputFormat, Template, SlotConfig

tpl = Template("cap", "Amount: {{amount}}", slots={"amount": SlotConfig("str")})
agent = Agent(
    model=model,
    output=Output(CapitalData),
    output_config=OutputConfig(format=OutputFormat.TEXT, template=tpl),
)
response = agent.response("...")
# response.content = rendered template
# response.template_data = {"amount": "..."}
# response.file, response.file_bytes when output_config format produces file
```

Requires `output=Output(MyModel)`. See [Template Engine](../template-engine.md).

## See Also

- [Structured Output](../structured-output.md) — Full guide, validators, Model-level config
- [Template Engine](../template-engine.md) — Slot-based generation
