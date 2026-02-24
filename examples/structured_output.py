"""
Structured Output Validation - Complete Example

This example demonstrates the complete structured output validation system in Syrin,
including configuration, validation, hooks, and error handling.

Run with:
    export OPENAI_API_KEY=your_key
    python examples/structured_output.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Check for API key
load_dotenv(Path(__file__).resolve().parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

from syrin import Agent, Model, Output
from syrin.enums import Hook
from syrin.model import structured
from syrin.types.validation import (
    OutputValidator,
    ValidationAction,
    ValidationContext,
    ValidationResult,
)

# =============================================================================
# EXAMPLE 1: Real LLM Call with Structured Output
# =============================================================================
print("\n" + "=" * 70)
print("EXAMPLE 1: Real LLM Call with Structured Output")
print("=" * 70)


# Define your expected output schema using @structured
@structured
class UserInfo:
    """User information schema."""

    name: str
    email: str
    age: int
    city: str


# Create agent with output validation
agent = Agent(
    model=Model.OpenAI(MODEL_ID),
    output=Output(UserInfo, validation_retries=3),
)

# Make actual LLM call
print("\n📤 Calling LLM to extract user info...")

try:
    result = agent.response(
        "Extract user info: John Doe is 35 years old, email john.doe@example.com, lives in San Francisco"
    )

    print("\n✅ Response received!")
    print("\n📋 Structured Output:")
    print(f"   is_valid: {result.structured.is_valid}")
    print(f"   raw: {result.structured.raw[:100]}...")

    if result.structured.parsed:
        print("\n📊 Parsed Data:")
        print(f"   name: {result.structured.parsed.name}")
        print(f"   email: {result.structured.parsed.email}")
        print(f"   age: {result.structured.parsed.age}")
        print(f"   city: {result.structured.parsed.city}")

    if result.structured.validation_attempts:
        print("\n🔄 Validation Attempts:")
        for attempt in result.structured.validation_attempts:
            status = "✅" if not attempt.error else "❌"
            print(f"   {status} Attempt {attempt.attempt}: {attempt.error or 'Success'}")

except Exception as e:
    print(f"\n❌ Error: {e}")


# =============================================================================
# EXAMPLE 2: Validation with Invalid Data (triggers retry)
# =============================================================================
print("\n" + "=" * 70)
print("EXAMPLE 2: Validation with Invalid Data (triggers retry)")
print("=" * 70)


@structured
class ProductInfo:
    """Product information schema."""

    name: str
    price: float
    in_stock: bool
    category: str


agent = Agent(
    model=Model.OpenAI(MODEL_ID),
    output=Output(ProductInfo, validation_retries=3),
    debug=True,
)

print("\n📤 Calling LLM with prompt that might produce invalid data...")

try:
    # Prompt designed to potentially produce invalid data
    result = agent.response("""
        Product: Super Widget
        Price: $29.99
        In Stock: yes
        Category: electronics

        Return the product info as JSON.
        IMPORTANT: For in_stock, use "yes" or "no" (not true/false)
    """)

    print("\n✅ Response received!")
    print(f"   is_valid: {result.structured.is_valid}")

    if result.structured.parsed:
        print("\n📊 Parsed Data:")
        print(f"   name: {result.structured.parsed.name}")
        print(f"   price: {result.structured.parsed.price}")
        print(f"   in_stock: {result.structured.parsed.in_stock}")
        print(f"   category: {result.structured.parsed.category}")

    if result.structured.final_error:
        print(f"\n❌ Final Error: {result.structured.final_error}")

    if result.structured.validation_attempts:
        print("\n🔄 Validation Attempts:")
        for attempt in result.structured.validation_attempts:
            status = "✅" if not attempt.error else "❌"
            print(
                f"   {status} Attempt {attempt.attempt}: {attempt.error[:80] if attempt.error else 'Success'}..."
            )

except Exception as e:
    print(f"\n❌ Error: {e}")


# =============================================================================
# EXAMPLE 3: With Hooks (Observability)
# =============================================================================
print("\n" + "=" * 70)
print("EXAMPLE 3: With Hooks (Observability)")
print("=" * 70)


@structured
class SentimentResult:
    """Sentiment analysis result."""

    sentiment: str  # positive, negative, neutral
    confidence: float  # 0.0 to 1.0
    explanation: str


agent = Agent(
    model=Model.OpenAI(MODEL_ID),
    output=Output(SentimentResult, validation_retries=3),
)


# Register hooks to see validation lifecycle
def on_start(ctx):
    print(f"\n📥 VALIDATION START: {ctx.output_type} (max_retries={ctx.max_retries})")


def on_attempt(ctx):
    print(f"🔄 Attempt {ctx.attempt}")


def on_retry(ctx):
    print(f"⚠️  RETRY #{ctx.attempt}: {ctx.reason}")
    print(f"   Error: {ctx.error[:60]}...")


def on_success(ctx):
    print(f"✅ SUCCESS at attempt {ctx.attempt}")


def on_failed(ctx):
    print(f"❌ FAILED: {ctx.reason}")
    print(f"   Error: {ctx.error[:60]}...")


agent.events.on(Hook.OUTPUT_VALIDATION_START, on_start)
agent.events.on(Hook.OUTPUT_VALIDATION_ATTEMPT, on_attempt)
agent.events.on(Hook.OUTPUT_VALIDATION_RETRY, on_retry)
agent.events.on(Hook.OUTPUT_VALIDATION_SUCCESS, on_success)
agent.events.on(Hook.OUTPUT_VALIDATION_FAILED, on_failed)

print("\n📤 Calling LLM with hooks...")

try:
    result = agent.response("""
        Analyze the sentiment of this review:
        "This product is amazing! I love it so much."

        Return as JSON with sentiment (positive/negative/neutral),
        confidence (0-1), and explanation.
    """)

    print("\n✅ Response received!")
    print(f"   is_valid: {result.structured.is_valid}")

    if result.structured.parsed:
        print("\n📊 Parsed Data:")
        print(f"   sentiment: {result.structured.parsed.sentiment}")
        print(f"   confidence: {result.structured.parsed.confidence}")
        print(f"   explanation: {result.structured.parsed.explanation}")

except Exception as e:
    print(f"\n❌ Error: {e}")


# =============================================================================
# EXAMPLE 4: With Custom Validator
# =============================================================================
print("\n" + "=" * 70)
print("EXAMPLE 4: With Custom Validator")
print("=" * 70)

from pydantic import BaseModel


class ReviewResult(BaseModel):
    rating: int  # 1-5
    sentiment: str
    summary: str


class RatingValidator(OutputValidator):
    """Custom validator for review ratings."""

    max_retries = 3

    def validate(self, output, context: ValidationContext) -> ValidationResult:
        data = (
            output
            if isinstance(output, dict)
            else output.model_dump()
            if hasattr(output, "model_dump")
            else {}
        )

        rating = data.get("rating", 0)
        if rating < 1 or rating > 5:
            return ValidationResult.invalid(
                message=f"Rating {rating} out of range 1-5",
                action=ValidationAction.RETRY,
                hint="Rating must be between 1 and 5",
            )

        sentiment = data.get("sentiment", "").lower()
        if sentiment not in ["positive", "negative", "neutral"]:
            return ValidationResult.invalid(
                message=f"Invalid sentiment: {sentiment}",
                action=ValidationAction.RETRY,
                hint="Sentiment must be positive, negative, or neutral",
            )

        return ValidationResult.valid(output)

    def on_retry(self, error, attempt):
        return f"Error: {error}. Please fix and retry."


agent = Agent(
    model=Model.OpenAI(MODEL_ID),
    output=Output(
        type=ReviewResult,
        validator=RatingValidator(),
        validation_retries=3,
    ),
)

print("\n📤 Calling LLM with custom validator...")

try:
    result = agent.response("""
        Review: "This product is terrible. Worst purchase ever."

        Return as JSON with rating (1-5), sentiment, and summary.
    """)

    print("\n✅ Response received!")
    print(f"   is_valid: {result.structured.is_valid}")

    if result.structured.parsed:
        print("\n📊 Parsed Data:")
        print(f"   rating: {result.structured.parsed.rating}")
        print(f"   sentiment: {result.structured.parsed.sentiment}")
        print(f"   summary: {result.structured.parsed.summary}")

except Exception as e:
    print(f"\n❌ Error: {e}")


# =============================================================================
# EXAMPLE 5: With Validation Context
# =============================================================================
print("\n" + "=" * 70)
print("EXAMPLE 5: With Validation Context")
print("=" * 70)

from pydantic import BaseModel, field_validator


class RestrictedUser(BaseModel):
    name: str
    email: str
    role: str

    @field_validator("email")
    @classmethod
    def email_must_be_allowed(cls, v: str, info) -> str:
        context = getattr(info, "context", None)
        allowed = context.get("allowed_domains", []) if context else []
        if allowed and not any(v.endswith(f"@{d}") for d in allowed):
            raise ValueError(f"Email must be from: {', '.join(allowed)}")
        return v

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        allowed = ["admin", "user", "guest"]
        if v.lower() not in allowed:
            raise ValueError(f"Role must be one of: {allowed}")
        return v.lower()


agent = Agent(
    model=Model.OpenAI(MODEL_ID),
    output=Output(
        type=RestrictedUser,
        validation_retries=3,
        context={"allowed_domains": ["company.com", "acme.com"]},
    ),
)

print("\n📤 Calling LLM with restricted domains...")

try:
    result = agent.response("""
        Create a user: John Smith, email john@company.com, role admin
        Return as JSON.
    """)

    print("\n✅ Response received!")
    print(f"   is_valid: {result.structured.is_valid}")

    if result.structured.parsed:
        print("\n📊 Parsed Data:")
        print(f"   name: {result.structured.parsed.name}")
        print(f"   email: {result.structured.parsed.email}")
        print(f"   role: {result.structured.parsed.role}")

except Exception as e:
    print(f"\n❌ Error: {e}")


# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print("""
Key Features Demonstrated:

1. @structured - Define output schemas
2. Output config - Group validation options
3. validation_retries - Automatic retry on failure
4. validation_context - Dynamic data for validators
5. Custom validators - Business logic validation
6. Hooks - Full observability

API:
    @structured
    class UserInfo:
        name: str
        email: str

    agent = Agent(
        model=Model.OpenAI(MODEL_ID),
        output=Output(UserInfo, validation_retries=3),
    )

    result = agent.response("Extract info")
    result.structured.parsed.name
""")

print("=" * 70)
print("EXAMPLES COMPLETE")
print("=" * 70 + "\n")
