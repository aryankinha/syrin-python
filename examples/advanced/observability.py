"""Observability Examples

Demonstrates the observability system with:
- Span-based tracing with parent-child relationships (agent → LLM → tool)
- Automatic spans: agent run, each LLM call (llm.iteration_N), each tool call (tool.<name>)
- Semantic attributes for LLM, tool, memory events
- Session tracking across multiple calls
- Debug mode for deep introspection (debug=True adds ConsoleExporter)
- Console, InMemory, and custom exporters

Run: python -m examples.advanced.observability
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

import syrin
from syrin import Agent, Model
from syrin.observability import (
    ConsoleExporter,
    InMemoryExporter,
    SpanKind,
    current_span,
    get_tracer,
    session,
    span,
)
from syrin.tool import tool

logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


# =============================================================================
# Example 1: Basic Debug Mode
# =============================================================================


def example_debug_mode():
    """Demonstrate debug mode - automatic tracing with console output."""
    print("\n" + "=" * 60)
    print("Example 1: Debug Mode")
    print("=" * 60)
    print("Debug mode automatically enables console tracing")
    print("You get detailed visibility without changing your code!")
    print()

    @tool
    def get_weather(location: str) -> str:
        """Get weather for a location."""
        return f"Sunny and 72°F in {location}"

    class WeatherAgent(Agent):
        model = Model(MODEL_ID, api_key=os.getenv("OPENAI_API_KEY"))
        system_prompt = "You are a helpful weather assistant."
        tools = [get_weather]

    # Enable debug mode to see all traces
    agent = WeatherAgent(debug=True)

    print("Running agent with debug=True...")
    result = agent.response("What's the weather in San Francisco?")
    print(f"\nFinal response: {result.content}")


# =============================================================================
# Example 2: Manual Span Creation
# =============================================================================


def example_manual_spans():
    """Demonstrate creating spans manually for custom workflows."""
    print("\n" + "=" * 60)
    print("Example 2: Manual Span Creation")
    print("=" * 60)

    # Add console exporter
    tracer = get_tracer()
    tracer.add_exporter(ConsoleExporter())

    @tool
    def calculate(expression: str) -> str:
        """Evaluate a mathematical expression."""
        try:
            return str(eval(expression))
        except Exception as e:
            return f"Error: {e}"

    class CalculatorAgent(Agent):
        model = Model(MODEL_ID, api_key=os.getenv("OPENAI_API_KEY"))
        system_prompt = "You are a helpful calculator. Use the calculate tool for math."
        tools = [calculate]

    agent = CalculatorAgent()

    # Wrap agent execution in a custom span
    with span(
        "my_workflow.calculate_sum", kind=SpanKind.WORKFLOW, user_id="user_123", feature="math_help"
    ) as workflow_span:
        print("Running calculation within custom workflow span...")
        result = agent.response("What is 234 + 567?")

        # Add custom attributes to the workflow span
        workflow_span.set_attribute("query", "What is 234 + 567?")
        workflow_span.set_attribute("result", result.content)
        workflow_span.set_attribute("cost", result.cost)

    print(f"\nFinal answer: {result.content}")


# =============================================================================
# Example 3: Session Tracking
# =============================================================================


def example_session_tracking():
    """Demonstrate session tracking for multi-turn conversations."""
    print("\n" + "=" * 60)
    print("Example 3: Session Tracking")
    print("=" * 60)

    tracer = get_tracer()
    tracer.add_exporter(ConsoleExporter())

    class ChatAgent(Agent):
        model = Model(MODEL_ID, api_key=os.getenv("OPENAI_API_KEY"))
        system_prompt = "You are a helpful assistant."

    # Create a session that groups all spans together
    with session("conversation_001", user="alice", feature="general_chat") as sess:
        agent = ChatAgent()

        print(f"Session started: {sess.id}")
        print()

        # All agent calls within this session are linked
        messages = [
            "Hello, my name is Alice",
            "What's my name?",
            "Tell me a short joke",
        ]

        for i, msg in enumerate(messages, 1):
            print(f"\n--- Turn {i}: {msg} ---")
            response = agent.response(msg)
            print(f"Response: {response.content}")

            # Access current span to add custom data
            curr_span = current_span()
            if curr_span:
                curr_span.set_attribute("turn", i)

        print(f"\nSession complete. Total spans: {sess.span_count}")


# =============================================================================
# Example 4: Semantic Attributes
# =============================================================================


def example_semantic_attributes():
    """Demonstrate semantic attributes for consistent observability."""
    print("\n" + "=" * 60)
    print("Example 4: Semantic Attributes")
    print("=" * 60)
    print("Semantic attributes enable structured querying and analysis")
    print()

    tracer = get_tracer()
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)

    @tool
    def search_docs(query: str) -> str:
        """Search documentation."""
        return f"Found 3 results for: {query}"

    class RAGAgent(Agent):
        model = Model(MODEL_ID, api_key=os.getenv("OPENAI_API_KEY"))
        system_prompt = "You are a helpful assistant with access to documentation."
        tools = [search_docs]

    agent = RAGAgent()
    result = agent.response("Search for: how to use agents")

    # Analyze the captured spans
    print("Captured spans analysis:")
    for span_obj in exporter.spans:
        print(f"\n  Span: {span_obj.name} ({span_obj.kind.value})")
        print(f"  Duration: {span_obj.duration_ms:.2f}ms")
        print("  Attributes:")

        # Show semantic attributes
        for key, value in span_obj.attributes.items():
            if key.startswith(("llm.", "tool.", "agent.", "budget.")):
                print(f"    - {key}: {value}")

    print(f"\nFinal response: {result.content}")


# =============================================================================
# Example 5: Nested Spans and Parent-Child Relationships
# =============================================================================


def example_nested_spans():
    """Demonstrate hierarchical span structure."""
    print("\n" + "=" * 60)
    print("Example 5: Nested Spans (Hierarchical Traces)")
    print("=" * 60)

    tracer = get_tracer()
    tracer.add_exporter(ConsoleExporter())

    @tool
    def fetch_data(source: str) -> str:
        """Fetch data from a source."""
        return f"Data from {source}"

    @tool
    def process_data(data: str) -> str:
        """Process fetched data."""
        return f"Processed: {data}"

    class DataAgent(Agent):
        model = Model(MODEL_ID, api_key=os.getenv("OPENAI_API_KEY"))
        system_prompt = "You are a data processing assistant."
        tools = [fetch_data, process_data]

    agent = DataAgent()

    # Create a parent span representing a complex workflow
    with span("data_pipeline.analyze", kind=SpanKind.WORKFLOW) as pipeline:
        pipeline.set_attribute("pipeline.name", "customer_analysis")
        pipeline.set_attribute("pipeline.steps", ["fetch", "process", "analyze"])

        print("Running data pipeline with nested operations...")

        # Each agent call creates child spans automatically
        result = agent.response("Fetch data from 'customers' and process it")

        pipeline.set_attribute("pipeline.result", result.content[:100])

    print(f"\nPipeline result: {result.content}")


# =============================================================================
# Example 6: Error Tracking and Debugging
# =============================================================================


def example_error_tracking():
    """Demonstrate error tracking and debugging with spans."""
    print("\n" + "=" * 60)
    print("Example 6: Error Tracking")
    print("=" * 60)

    tracer = get_tracer()
    tracer.add_exporter(ConsoleExporter())

    @tool
    def risky_operation(should_fail: bool) -> str:
        """An operation that might fail."""
        if should_fail:
            raise ValueError("Intentional failure for demonstration")
        return "Success!"

    class ErrorAgent(Agent):
        model = Model(MODEL_ID, api_key=os.getenv("OPENAI_API_KEY"))
        system_prompt = "You are a testing agent. Use the risky_operation tool."
        tools = [risky_operation]

    agent = ErrorAgent()

    print("Running agent that will encounter an error...")
    print()

    try:
        agent.response("Call risky_operation with should_fail=true")
    except Exception as e:
        print(f"Error caught: {e}")
        print()
        print("The trace above shows exactly where the error occurred!")
        print("Look for the span with status=ERROR and the exception event.")


# =============================================================================
# Example 7: Cost Attribution with Spans
# =============================================================================


def example_cost_attribution():
    """Demonstrate cost tracking with business context."""
    print("\n" + "=" * 60)
    print("Example 7: Cost Attribution by Feature")
    print("=" * 60)

    tracer = get_tracer()
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)

    class CostAgent(Agent):
        model = Model(MODEL_ID, api_key=os.getenv("OPENAI_API_KEY"))
        system_prompt = "You are a helpful assistant."

    # Simulate different features using the agent
    features = [
        ("summarization", "Summarize this: Python is a programming language"),
        ("qa", "What is Python?"),
        ("generation", "Write a hello world in Python"),
    ]

    costs_by_feature = {}

    for feature, query in features:
        with span(f"feature.{feature}", kind=SpanKind.WORKFLOW) as feature_span:
            feature_span.set_attribute("feature.name", feature)
            feature_span.set_attribute("feature.tier", "premium")

            agent = CostAgent()
            result = agent.response(query)

            feature_span.set_attribute("feature.cost", result.cost)
            costs_by_feature[feature] = result.cost

    print("Cost breakdown by feature:")
    total = 0
    for feature, cost in costs_by_feature.items():
        print(f"  {feature}: ${cost:.6f}")
        total += cost
    print(f"  Total: ${total:.6f}")


# =============================================================================
# Example 8: Integration with Global Config
# =============================================================================


def example_global_config():
    """Demonstrate configuring observability globally."""
    print("\n" + "=" * 60)
    print("Example 8: Global Configuration")
    print("=" * 60)
    print("Configure tracing globally for all agents")
    print()

    # Configure globally
    syrin.configure(trace=True)

    class ConfigAgent(Agent):
        model = Model(MODEL_ID, api_key=os.getenv("OPENAI_API_KEY"))
        system_prompt = "You are a helpful assistant."

    # All agents now have tracing enabled by default
    agent = ConfigAgent(debug=True)

    print("Agent created with global tracing enabled")
    result = agent.response("Say 'hello' and nothing else")
    print(f"Response: {result.content}")


# =============================================================================
# Example 9: Custom Exporters
# =============================================================================


def example_custom_exporter():
    """Demonstrate creating a custom exporter."""
    print("\n" + "=" * 60)
    print("Example 9: Custom Exporter")
    print("=" * 60)
    print("Create your own exporter for custom backends")
    print()

    from syrin.observability import Span, SpanExporter

    class CustomExporter(SpanExporter):
        """Custom exporter that logs to a simple list."""

        def __init__(self):
            self.logs = []

        def export(self, span: Span) -> None:
            if span.parent_span_id is None:
                # Only log root spans
                self.logs.append(
                    {
                        "name": span.name,
                        "duration_ms": span.duration_ms,
                        "attributes_count": len(span.attributes),
                    }
                )
                print(f"Custom exporter captured: {span.name}")

    tracer = get_tracer()
    custom_exporter = CustomExporter()
    tracer.add_exporter(custom_exporter)

    class CustomAgent(Agent):
        model = Model(MODEL_ID, api_key=os.getenv("OPENAI_API_KEY"))
        system_prompt = "You are a helpful assistant."

    agent = CustomAgent()
    agent.response("Hello!")

    print(f"\nCustom exporter captured {len(custom_exporter.logs)} root spans")
    for log in custom_exporter.logs:
        print(f"  - {log['name']}: {log['duration_ms']:.2f}ms")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    # Run all examples
    examples = [
        example_debug_mode,
        example_manual_spans,
        example_session_tracking,
        example_semantic_attributes,
        example_nested_spans,
        example_error_tracking,
        example_cost_attribution,
        example_global_config,
        example_custom_exporter,
    ]

    print("\n" + "#" * 60)
    print("# Syrin Observability Examples")
    print("#" * 60)
    print()
    print("These examples demonstrate the new observability system:")
    print("- Span-based tracing with parent-child relationships")
    print("- Semantic attributes for structured data")
    print("- Session tracking for conversations")
    print("- Debug mode for deep introspection")
    print("- Custom exporters for any backend")
    print()

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "#" * 60)
    print("# All examples completed!")
    print("#" * 60)
    print()
    print("Key takeaways:")
    print("1. Debug mode (debug=True) gives instant visibility")
    print("2. Manual spans let you track custom workflows")
    print("3. Sessions group related traces together")
    print("4. Semantic attributes enable powerful querying")
    print("5. Errors are automatically captured with full context")
    print("6. Cost attribution helps optimize by feature/user")
    print()
