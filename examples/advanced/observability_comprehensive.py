"""
Comprehensive Observability Example

This example demonstrates ALL features of the Syrin observability system:

1. Debug Mode - Instant console visibility
2. Span-based Tracing - Hierarchical parent-child spans
3. Semantic Attributes - Standardized queryable keys
4. Session Tracking - Group multi-turn conversations
5. Manual Spans - Custom workflow instrumentation
6. Convenience Decorators - llm_span, tool_span, memory_span, etc.
7. Guardrail Tracing - Input/output validation with spans
8. Memory Tracing - remember/recall/forget operations
9. Metrics Aggregation - Cost, latency, tokens, errors
10. Sampling Strategies - Probabilistic, deterministic, rate-limiting
11. Exporters - Console, InMemory, custom
12. Hook Integration - Bridge Events with spans

Run: python -m examples.advanced.observability_comprehensive
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv

from syrin import Agent, Model
from syrin.guardrails import BlockedWordsGuardrail
from syrin.observability import (
    ConsoleExporter,
    InMemoryExporter,
    SemanticAttributes,
    SpanKind,
    agent_span,
    budget_span,
    current_span,
    get_tracer,
    guardrail_span,
    handoff_span,
    llm_span,
    memory_span,
    session,
    span,
    tool_span,
)
from syrin.observability.metrics import get_metrics
from syrin.observability.sampling import (
    AdaptiveSampler,
    DeterministicSampler,
    ProbabilisticSampler,
    RateLimitingSampler,
    SamplingPolicy,
    create_sampler,
)
from syrin.tool import tool

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_ID = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")


# =============================================================================
# Example 1: Debug Mode - The Easiest Way to See What's Happening
# =============================================================================


def example_debug_mode():
    """Debug mode gives instant visibility without any setup."""
    print("\n" + "=" * 70)
    print("Example 1: Debug Mode")
    print("=" * 70)
    print("Simply add debug=True to your agent!")
    print()

    @tool
    def calculator(expression: str) -> str:
        """Evaluate a math expression."""
        try:
            return str(eval(expression))
        except Exception as e:
            return f"Error: {e}"

    class DebugAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful math assistant."
        tools = [calculator]

    # Debug mode automatically:
    # - Creates spans for agent, LLM, and tool calls
    # - Outputs hierarchical trace to console
    # - Captures full context
    agent = DebugAgent(debug=True)

    print("Running agent with debug=True...")
    result = agent.response("What is 25 * 4 + 10?")
    print(f"\nResult: {result.content}")


# =============================================================================
# Example 2: Manual Span Creation - Full Control
# =============================================================================


def example_manual_spans():
    """Create spans manually for custom workflows."""
    print("\n" + "=" * 70)
    print("Example 2: Manual Spans")
    print("=" * 70)
    print("Create spans around any code block")
    print()

    # Clear previous traces
    tracer = get_tracer()
    tracer.clear()
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)

    @tool
    def search_db(query: str) -> str:
        """Search a database."""
        time.sleep(0.1)  # Simulate DB call
        return f"Found 3 results for: {query}"

    class DBAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a database assistant."
        tools = [search_db]

    agent = DBAgent()

    # Manual span with custom attributes
    with span(
        "custom_workflow.data_lookup",
        kind=SpanKind.WORKFLOW,
        user_id="user_123",
        feature="data_analysis",
    ) as workflow_span:
        workflow_span.set_attribute("workflow.id", "wf_456")

        # Nested span for LLM call
        with span("llm.query_generation", kind=SpanKind.LLM) as llm_span:
            llm_span.set_attribute(SemanticAttributes.LLM_MODEL, MODEL_ID)
            result = agent.response("Find all users who signed up this month")

        workflow_span.set_attribute("result_count", 3)
        workflow_span.set_attribute("cost", result.cost)

    # Analyze captured spans
    print("\nCaptured Spans:")
    for s in exporter.spans:
        print(f"  - {s.name} ({s.kind.value}): {s.duration_ms:.2f}ms")
        for key, value in s.attributes.items():
            if key.startswith(("workflow.", "llm.", "result", "cost")):
                print(f"      {key}: {value}")


# =============================================================================
# Example 3: Session Tracking - Multi-Turn Conversations
# =============================================================================


def example_sessions():
    """Group related spans into sessions."""
    print("\n" + "=" * 70)
    print("Example 3: Session Tracking")
    print("=" * 70)
    print("Group multiple agent calls into a session")
    print()

    tracer = get_tracer()
    tracer.clear()
    tracer.add_exporter(ConsoleExporter())

    class ChatAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."

    # Create a session - all spans within are linked
    with session("conversation_001", user="alice", topic="general") as sess:
        agent = ChatAgent()

        print(f"Session: {sess.id}")
        print("Messages:")

        messages = [
            "Hi, my name is Bob",
            "What's my name?",
            "What's 2+2?",
        ]

        for msg in messages:
            print(f"\nUser: {msg}")
            response = agent.response(msg)
            print(f"Agent: {response.content[:50]}...")

            # Add custom attributes to current span
            curr = current_span()
            if curr:
                curr.set_attribute("user.message", msg)


# =============================================================================
# Example 4: Convenience Decorators - Quick Spans
# =============================================================================


def example_decorators():
    """Use convenience decorators for common operations."""
    print("\n" + "=" * 70)
    print("Example 4: Convenience Decorators")
    print("=" * 70)
    print("Quick span creation for common operations")
    print()

    tracer = get_tracer()
    tracer.clear()
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)

    # LLM span - for LLM operations
    with llm_span("gpt-4o", prompt="Hello world") as s:
        s.set_attribute("completion", "Hi there!")
        time.sleep(0.05)

    # Tool span - for tool calls
    with tool_span("calculator", input={"expression": "2+2"}) as s:
        s.set_attribute("output", "4")
        time.sleep(0.02)

    # Memory span - for memory operations
    with memory_span("recall", memory_type="episodic", query="user preferences") as s:
        s.set_attribute("results_count", 5)
        time.sleep(0.01)

    # Budget span - for budget operations
    with budget_span("check", limit=10.0, used=5.0) as s:
        s.set_attribute("remaining", 5.0)
        time.sleep(0.01)

    # Guardrail span - for validation
    with guardrail_span("content_filter", stage="input") as s:
        s.set_attribute(SemanticAttributes.GUARDRAIL_PASSED, True)
        time.sleep(0.01)

    # Handoff span - for agent handoffs
    with handoff_span("triage_agent", "specialist_agent") as s:
        s.set_attribute("memories_transferred", 10)
        time.sleep(0.01)

    # Agent span - for agent operations
    with agent_span("research_agent") as s:
        s.set_attribute("iterations", 3)
        time.sleep(0.05)

    print("Captured spans with decorators:")
    for s in exporter.spans:
        print(f"  {s.name} ({s.kind.value})")
        print(f"    Attributes: {list(s.attributes.keys())[:5]}")


# =============================================================================
# Example 5: Guardrail Tracing - Input/Output Validation
# =============================================================================


def example_guardrails():
    """Demonstrate guardrail integration with tracing."""
    print("\n" + "=" * 70)
    print("Example 5: Guardrail Tracing")
    print("=" * 70)
    print("Input/output validation with full observability")
    print()

    tracer = get_tracer()
    tracer.clear()
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)

    # Create guardrails
    blocked = BlockedWordsGuardrail(blocked_words=["badword", "forbidden"], name="word_filter")

    class GuardedAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."
        guardrails = [blocked]

    agent = GuardedAgent(debug=False)  # Use manual exporter

    # Test blocked input
    print("Testing blocked input...")
    agent.response("Hello, say badword please")

    # Check guardrail spans
    print("\nGuardrail spans captured:")
    for s in exporter.spans:
        if s.kind == SpanKind.GUARDRAIL:
            print(f"  {s.name}: passed={s.attributes.get('guardrail.passed')}")
            if not s.attributes.get("guardrail.passed"):
                print(f"    Violation: {s.attributes.get('guardrail.violation')}")


# =============================================================================
# Example 6: Memory Tracing - Persistent Memory Operations
# =============================================================================


def example_memory_tracing():
    """Demonstrate memory operations with tracing."""
    print("\n" + "=" * 70)
    print("Example 6: Memory Tracing")
    print("=" * 70)
    print("Memory operations can be traced with convenience decorators")
    print()

    tracer = get_tracer()
    tracer.clear()
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)

    # Demonstrate memory span decorators
    # (Full persistent memory requires backend setup)

    # Memory recall
    print("Simulating memory recall...")
    with memory_span("recall", memory_type="episodic", query="user preferences") as s:
        s.set_attribute(SemanticAttributes.MEMORY_RESULTS_COUNT, 5)
        # Simulate recall operation
        time.sleep(0.01)

    # Memory store
    print("Simulating memory store...")
    with memory_span("store", memory_type="semantic", query="dark mode preference") as s:
        s.set_attribute("memory.id", "mem_123")
        time.sleep(0.01)

    # Memory forget
    print("Simulating memory forget...")
    with memory_span("forget", memory_type="all", query="old preference") as s:
        s.set_attribute("memory.deleted_count", 2)
        time.sleep(0.01)

    # Check memory spans
    print("\nMemory spans captured:")
    for s in exporter.spans:
        if s.kind == SpanKind.MEMORY:
            print(f"  {s.name}: {s.attributes.get('memory.operation')}")
            print(f"    Duration: {s.duration_ms:.2f}ms")
            print(f"    Attributes: {list(s.attributes.keys())}")


# =============================================================================
# Example 7: Metrics Aggregation - Cost, Latency, Tokens
# =============================================================================


def example_metrics():
    """Demonstrate metrics collection and aggregation."""
    print("\n" + "=" * 70)
    print("Example 7: Metrics Aggregation")
    print("=" * 70)
    print("Automatic metrics for cost, latency, tokens, errors")
    print()

    # Clear metrics
    metrics = get_metrics()
    metrics.clear()

    @tool
    def quick_tool(x: int) -> int:
        """A quick tool."""
        return x * 2

    class MetricAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a calculator."
        tools = [quick_tool]

    agent = MetricAgent(debug=False)
    tracer = get_tracer()
    tracer.clear()
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)
    tracer.set_collect_metrics(True)

    # Run a few requests
    print("Running requests to generate metrics...")
    agent.response("What is 5 + 3?")
    agent.response("What is 10 * 2?")
    agent.response("Hello!")

    # Extract metrics from spans
    for s in exporter.spans:
        metrics.from_span(s)

    # Get summary
    summary = metrics.get_summary()

    print("\nMetrics Summary:")
    print(f"  LLM Requests: {summary['llm']['requests']}")
    print(f"  Total Tokens: {summary['llm']['tokens_total']}")
    print(f"  Total Cost: ${summary['llm']['cost']:.4f}")
    print(f"  Avg Latency: {summary['llm']['latency_avg']:.2f}ms")
    print(f"  p95 Latency: {summary['llm']['latency_p95']:.2f}ms")
    print(f"  Agent Runs: {summary['agent']['runs']}")
    print(f"  Tool Calls: {summary['tool']['calls']}")


# =============================================================================
# Example 8: Sampling Strategies - Control What You Record
# =============================================================================


def example_sampling():
    """Demonstrate different sampling strategies."""
    print("\n" + "=" * 70)
    print("Example 8: Sampling Strategies")
    print("=" * 70)
    print("Control which traces are recorded")
    print()

    # Clear and setup
    tracer = get_tracer()
    tracer.clear()

    # 1. Probabilistic - random sampling
    print("\n1. Probabilistic Sampler (10% rate):")
    policy = SamplingPolicy(rate=0.1, sample_errors=True)
    prob_sampler = ProbabilisticSampler(policy)

    # Test sampling
    sampled = sum(1 for _ in range(100) if prob_sampler.should_sample())
    print(f"   Sampled {sampled}/100 spans (expected ~10)")

    # 2. Deterministic - based on trace ID
    print("\n2. Deterministic Sampler:")
    det_sampler = DeterministicSampler(SamplingPolicy(rate=0.5))

    # Create test spans
    tracer.add_exporter(InMemoryExporter())
    for i in range(5):
        with span(f"span_{i}", kind=SpanKind.INTERNAL) as s:
            s.set_attribute("index", i)
            should = det_sampler.should_sample(s)
            print(f"   span_{i}: sampled={should}")

    # 3. Rate Limiting - max samples per second
    print("\n3. Rate Limiting Sampler (5/sec):")
    rate_sampler = RateLimitingSampler(SamplingPolicy(), max_samples_per_second=5.0)

    # Burst test
    sampled = sum(1 for _ in range(10) if rate_sampler.should_sample())
    print(f"   First 10: sampled {sampled}/10")

    # 4. Adaptive - adjusts based on error rate
    print("\n4. Adaptive Sampler:")
    AdaptiveSampler(SamplingPolicy(), target_error_rate=0.1)


# =============================================================================
# Example 10: Hook Integration - Bridge Events and Spans
# =============================================================================


def example_hooks_integration():
    """Bridge the Events system with observability."""
    print("\n" + "=" * 70)
    print("Example 10: Hook Integration")
    print("=" * 70)
    print("Connect Events system with spans for unified observability")
    print()

    from syrin.observability.hooks import observe_hooks

    tracer = get_tracer()
    tracer.clear()
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)

    @tool
    def get_time() -> str:
        """Get the current time."""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")

    class HookAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a time assistant."
        tools = [get_time]

    agent = HookAgent(debug=False)

    # Attach observability to hooks
    observe_hooks(agent)

    # Register event handlers using correct API
    def on_start(ctx):
        print(f"  [Event] Start: {ctx.get('input', '')[:30]}...")

    def on_complete(ctx):
        print(f"  [Event] Complete: cost=${ctx.get('cost', 0):.4f}")

    agent.events.on("start", on_start)
    agent.events.on("complete", on_complete)

    print("Running agent with hook observers...")
    agent.response("What time is it?")

    print("\nSpans captured (includes event data):")
    for s in exporter.spans:
        if s.events:
            print(f"  {s.name}: {len(s.events)} events")
            for e in s.events[:2]:
                print(f"    - {e['name']}")


# =============================================================================
# Example 9: Custom Exporter - Build Your Own
# =============================================================================


def example_custom_exporter():
    """Create a custom exporter for your needs."""
    print("\n" + "=" * 70)
    print("Example 9: Custom Exporter")
    print("=" * 70)
    print("Build exporters for any backend")
    print()

    from syrin.observability import Span, SpanExporter

    class CustomExporter(SpanExporter):
        """Custom exporter that stores spans in a list."""

        def __init__(self):
            self.spans: list[Span] = []

        def export(self, span: Span) -> None:
            # Only store root spans
            if span.parent_span_id is None:
                self.spans.append(span)

    class MetricsExporter(SpanExporter):
        """Export that aggregates metrics."""

        def __init__(self):
            self.total_duration = 0.0
            self.span_count = 0

        def export(self, span: Span) -> None:
            self.total_duration += span.duration_ms
            self.span_count += 1

    # Use custom exporters
    tracer = get_tracer()
    tracer.clear()

    custom = CustomExporter()
    metrics_exp = MetricsExporter()

    tracer.add_exporter(custom)
    tracer.add_exporter(metrics_exp)

    @tool
    def echo(msg: str) -> str:
        return msg

    class CustomExpAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "Echo assistant."
        tools = [echo]

    agent = CustomExpAgent()
    agent.response("Say hello")

    print(f"Custom exporter captured: {len(custom.spans)} root spans")
    print(
        f"Metrics exporter: {metrics_exp.span_count} spans, {metrics_exp.total_duration:.2f}ms total"
    )


# =============================================================================
# Example 11: Semantic Attributes - Queryable Metadata
# =============================================================================


def example_semantic_attributes():
    """Use semantic attributes for structured analysis."""
    print("\n" + "=" * 70)
    print("Example 11: Semantic Attributes")
    print("=" * 70)
    print("Standardized keys for consistent querying")
    print()

    tracer = get_tracer()
    tracer.clear()
    exporter = InMemoryExporter()
    tracer.add_exporter(exporter)

    @tool
    def fetch_data(source: str) -> str:
        return f"Data from {source}"

    class AttrAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "Data assistant."
        tools = [fetch_data]

    agent = AttrAgent()
    agent.response("Fetch data from users table")

    # Analyze semantic attributes
    print("Semantic attributes used:")
    for s in exporter.spans:
        for key, value in s.attributes.items():
            if key in (
                SemanticAttributes.LLM_MODEL,
                SemanticAttributes.LLM_TOKENS_TOTAL,
                SemanticAttributes.LLM_COST,
                SemanticAttributes.TOOL_NAME,
                SemanticAttributes.TOOL_INPUT,
                SemanticAttributes.AGENT_NAME,
            ):
                print(f"  {key}: {value}")


# =============================================================================
# Example 12: Full Production Setup
# =============================================================================


def example_production_setup():
    """Complete production observability setup."""
    print("\n" + "=" * 70)
    print("Example 12: Production Setup")
    print("=" * 70)
    print("Complete observability for production")
    print()

    # 1. Configure tracer
    tracer = get_tracer()
    tracer.clear()

    # 2. Add exporters (console + in-memory for analysis)
    console_exp = ConsoleExporter(colors=True)
    memory_exp = InMemoryExporter()

    tracer.add_exporter(console_exp)
    tracer.add_exporter(memory_exp)

    # 3. Set up sampling (sample 10%, always sample errors)
    sampler = create_sampler(
        "probabilistic",
        rate=0.1,
        sample_errors=True,
        sample_slow_traces=True,
        slow_threshold_ms=5000,
    )
    tracer.set_sampler(sampler)

    # 4. Enable metrics collection
    tracer.set_collect_metrics(True)
    metrics = get_metrics()
    metrics.clear()

    # 5. Create agent with guardrails
    blocked = BlockedWordsGuardrail(blocked_words=["block", "forbidden"], name="content_filter")

    class ProdAgent(Agent):
        model = Model(MODEL_ID)
        system_prompt = "You are a helpful assistant."
        guardrails = [blocked]

    # 6. Run with session tracking
    with session("production_session_001", environment="prod", version="1.0") as sess:
        agent = ProdAgent()

        print(f"Running production session: {sess.id}")

        # Make requests
        responses = [
            "Hello, how are you?",
            "What's the weather?",
        ]

        for msg in responses:
            print(f"\nUser: {msg}")
            result = agent.response(msg)
            print(f"Agent: {result.content[:50]}...")

    # 7. Get final metrics
    print("\n" + "=" * 70)
    print("Production Metrics:")
    print("=" * 70)

    summary = metrics.get_summary()
    print(f"  Total Cost: ${summary['llm']['cost']:.4f}")
    print(f"  Total Tokens: {summary['llm']['tokens_total']}")
    print(f"  Avg Latency: {summary['llm']['latency_avg']:.2f}ms")
    print(f"  Error Rate: {summary['agent']['errors']}/{summary['agent']['runs']}")
    print(f"  Guardrails Passed: {summary['guardrail']['passed']}")
    print(f"  Guardrails Blocked: {summary['guardrail']['blocked']}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\n" + "#" * 70)
    print("# Syrin Observability - Comprehensive Examples")
    print("#" * 70)
    print()
    print("This file demonstrates ALL observability features:")
    print("  1. Debug Mode")
    print("  2. Manual Spans")
    print("  3. Session Tracking")
    print("  4. Convenience Decorators")
    print("  5. Guardrail Tracing")
    print("  6. Memory Tracing")
    print("  7. Metrics Aggregation")
    print("  8. Sampling Strategies")
    print("  9. Custom Exporters")
    print(" 10. Hook Integration")
    print(" 11. Semantic Attributes")
    print(" 12. Production Setup")
    print()

    examples = [
        ("Debug Mode", example_debug_mode),
        ("Manual Spans", example_manual_spans),
        ("Sessions", example_sessions),
        ("Decorators", example_decorators),
        ("Guardrails", example_guardrails),
        ("Memory", example_memory_tracing),
        ("Metrics", example_metrics),
        ("Sampling", example_sampling),
        ("Custom Exporter", example_custom_exporter),
        ("Hooks Integration", example_hooks_integration),
        ("Semantic Attributes", example_semantic_attributes),
        ("Production Setup", example_production_setup),
    ]

    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\nError in {name}: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "#" * 70)
    print("# All Examples Completed!")
    print("#" * 70)
    print()
    print("Key Takeaways:")
    print("  1. Debug mode (debug=True) = instant visibility")
    print("  2. Spans = hierarchical tracing")
    print("  3. Sessions = group multi-turn conversations")
    print("  4. Decorators = quick spans for common ops")
    print("  5. Guardrails = validated with tracing")
    print("  6. Memory = remember/recall/forget instrumented")
    print("  7. Metrics = cost, latency, tokens aggregated")
    print("  8. Sampling = control what you record")
    print("  9. Exporters = send to any backend")
    print(" 10. Hooks = bridge events with spans")
    print(" 11. Semantic = standardized queryable keys")
    print(" 12. Production = all features combined")
