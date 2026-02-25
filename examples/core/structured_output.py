"""Structured Output Example.

Demonstrates:
- Using @structured decorator to define output schemas
- Using @output shorthand
- Getting parsed data from responses
- Working with Pydantic models

Run: python -m examples.core.structured_output
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent
from syrin.model import structured

logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@structured
class SentimentResult:
    """Sentiment analysis result."""

    sentiment: str  # positive, negative, neutral
    confidence: float  # 0.0 to 1.0
    explanation: str = ""


@structured
class PersonInfo:
    """Person information extracted from text."""

    name: str
    age: int | None = None
    occupation: str = "unknown"
    hobbies: list[str] = []


@structured
class WeatherData:
    """Weather information schema."""

    city: str
    temperature: float
    unit: str = "celsius"
    conditions: str = "clear"
    humidity: int | None = None


def example_basic_structured_output() -> None:
    """Basic structured output with @structured decorator."""
    print("\n" + "=" * 50)
    print("Basic Structured Output")
    print("=" * 50)

    class SentimentAgent(Agent):
        model = almock
        system_prompt = "Analyze the sentiment of the text. Respond with sentiment (positive/negative/neutral), confidence (0-1), and explanation."

    agent = SentimentAgent()

    result = agent.response("I absolutely love this product! It's amazing!")

    print("Input: 'I absolutely love this product! It's amazing!'")
    print(f"Raw response: {result.content}")
    print(f"Structured data: {result.data}")

    # Access structured data
    if result.data:
        print(f"Sentiment: {result.data.get('sentiment')}")
        print(f"Confidence: {result.data.get('confidence')}")


def example_person_extraction() -> None:
    """Extract structured data from text."""
    print("\n" + "=" * 50)
    print("Person Extraction")
    print("=" * 50)

    class ExtractionAgent(Agent):
        model = almock
        system_prompt = """Extract person information from the text.
Return JSON with: name, age (if mentioned), occupation, and hobbies (list)."""

    agent = ExtractionAgent()

    result = agent.response("John is a 35-year-old software engineer who loves hiking and reading.")

    print("Input: 'John is a 35-year-old software engineer...'")
    print(f"Extracted data: {result.data}")


def example_with_type_hints() -> None:
    """Using structured output with type hints."""
    print("\n" + "=" * 50)
    print("Type Hints with Structured Output")
    print("=" * 50)

    from syrin.model import output

    @output
    class TodoItem:
        title: str
        priority: str  # high, medium, low
        due_days: int | None = None
        tags: list[str] = []

    class TodoAgent(Agent):
        model = almock
        system_prompt = "Parse the todo item. Return JSON with title, priority, due_days (if mentioned), and tags."

    agent = TodoAgent()

    result = agent.response(
        "Finish the quarterly report - high priority, due in 3 days, tags: work, urgent"
    )

    print("Input: Todo item description")
    print(f"Parsed result: {result.data}")


def example_list_of_objects() -> None:
    """Working with lists in structured output."""
    print("\n" + "=" * 50)
    print("List of Objects")
    print("=" * 50)

    @structured
    class Meeting:
        title: str
        time: str
        participants: list[str] = []

    class MeetingAgent(Agent):
        model = almock
        system_prompt = (
            "Extract meeting details. Return JSON with title, time, and participants list."
        )

    agent = MeetingAgent()

    result = agent.response("Team standup at 10am with Alice, Bob, and Charlie")

    print("Input: 'Team standup at 10am with Alice, Bob, and Charlie'")
    print(f"Meeting details: {result.data}")


def example_response_object() -> None:
    """Accessing full response object with structured data."""
    print("\n" + "=" * 50)
    print("Response Object Properties")
    print("=" * 50)

    class WeatherAgent(Agent):
        model = almock
        system_prompt = "Extract weather data as JSON with city, temperature, unit, conditions."

    agent = WeatherAgent()

    result = agent.response("What's the weather in Tokyo today?")

    print(f"Content: {result.content}")
    print(f"Data: {result.data}")
    print(f"Cost: ${result.cost:.6f}")
    print(f"Tokens: {result.tokens.total_tokens}")
    print(f"Model: {result.model}")


if __name__ == "__main__":
    example_basic_structured_output()
    example_person_extraction()
    example_with_type_hints()
    example_list_of_objects()
    example_response_object()
