"""
Master Dynamic Pipeline - Complex multi-agent system demonstration

This file demonstrates a complex market research pipeline with:
- 10 parallel specialized agents (different research domains)
- 5 tools for data gathering, analysis, and reporting
- Full observability with hooks at every stage
- Real-time debugging for developers

This is how developers would debug and monitor a production multi-agent system.
"""

import os
import time
from datetime import datetime

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent
from syrin.agent.multi_agent import DynamicPipeline
from syrin.enums import Hook
from syrin.tool import tool

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")


# =============================================================================
# TOOLS - 5 specialized tools for the agents
# =============================================================================


@tool(name="search_web", description="Search the web for information")
def search_web(query: str) -> str:
    """Search the web for information on any topic."""
    return f"[SIMULATED] Search results for: {query}\n\nFound 10 relevant articles and 3 industry reports."


@tool(name="analyze_data", description="Analyze numerical data and generate insights")
def analyze_data(data: str, analysis_type: str = "statistical") -> str:
    """Analyze provided data and return statistical insights."""
    _ = analysis_type  # Unused but kept for API consistency
    return f"[SIMULATED] Analysis of: {data}\n\nTrend: Upward 15%\nKey finding: Strong correlation between X and Y"


@tool(name="fetch_financial", description="Fetch financial data and metrics")
def fetch_financial(symbol: str) -> str:
    """Fetch financial metrics for a company/sector."""
    return f"[SIMULATED] Financial data for {symbol}:\n\nRevenue: $2.5B (+12% YoY)\nEBITDA: $450M\nP/E Ratio: 28.5"


@tool(name="generate_chart", description="Generate ASCII charts and visualizations")
def generate_chart(data: str, chart_type: str = "bar") -> str:
    """Generate ASCII chart visualization."""
    return f"[SIMULATED] {chart_type.upper()} Chart for: {data}\n\n████████████ 75%\n█████████    50%\n██████      25%\nX-Axis: Q1 Q2 Q3 Q4"


@tool(name="export_report", description="Export report to markdown format")
def export_report(title: str, content: str) -> str:
    """Export report in markdown format."""
    return f"[SIMULATED] Exported: {title}\n\n---\n{content}\n---\nSaved to reports/{title.replace(' ', '_')}.md"


# =============================================================================
# SPECIALIZED AGENTS - 10 parallel agents for different domains
# =============================================================================


class TechResearchAgent(Agent):
    """Research agent for technology sector."""

    _syrin_name = "tech_researcher"
    model = almock
    system_prompt = (
        "You research technology trends, innovations, and companies. Be thorough and data-driven."
    )
    tools = [search_web, analyze_data]


class FinanceResearchAgent(Agent):
    """Research agent for financial markets."""

    _syrin_name = "finance_researcher"
    model = almock
    system_prompt = "You research financial markets, stocks, and investment trends. Provide data-backed insights."
    tools = [fetch_financial, analyze_data]


class HealthcareResearchAgent(Agent):
    """Research agent for healthcare industry."""

    _syrin_name = "healthcare_researcher"
    model = almock
    system_prompt = "You research healthcare industry trends, pharma, biotech, and medical devices."
    tools = [search_web, analyze_data]


class EnergyResearchAgent(Agent):
    """Research agent for energy sector."""

    _syrin_name = "energy_researcher"
    model = almock
    system_prompt = "You research energy markets, renewables, and sustainability trends."
    tools = [search_web, fetch_financial]


class ConsumerResearchAgent(Agent):
    """Research agent for consumer behavior."""

    _syrin_name = "consumer_researcher"
    model = almock
    system_prompt = "You research consumer behavior, retail trends, and market preferences."
    tools = [search_web, analyze_data]


class AIResearchAgent(Agent):
    """Research agent for AI/ML sector."""

    _syrin_name = "ai_researcher"
    model = almock
    system_prompt = "You research artificial intelligence, machine learning, and automation trends."
    tools = [search_web, analyze_data, generate_chart]


class GeopoliticsResearchAgent(Agent):
    """Research agent for geopolitical factors."""

    _syrin_name = "geopolitics_researcher"
    model = almock
    system_prompt = "You research geopolitical factors affecting markets and business."
    tools = [search_web]


class RegulatoryResearchAgent(Agent):
    """Research agent for regulatory landscape."""

    _syrin_name = "regulatory_researcher"
    model = almock
    system_prompt = "You research regulations, compliance, and policy changes affecting industries."
    tools = [search_web, export_report]


class CompetitorAnalysisAgent(Agent):
    """Research agent for competitive analysis."""

    _syrin_name = "competitor_researcher"
    model = almock
    system_prompt = "You analyze competitors, market positioning, and business strategies."
    tools = [search_web, fetch_financial, analyze_data]


class SummarizerAgent(Agent):
    """Agent that synthesizes all research into a coherent report."""

    _syrin_name = "summarizer"
    model = almock
    system_prompt = "You synthesize multiple research findings into a comprehensive, clear report."
    tools = [generate_chart, export_report]


# =============================================================================
# CUSTOM HOOK HANDLERS - How developers debug the system
# =============================================================================


class PipelineDebugger:
    """Debug handler that logs all pipeline events - how developers monitor."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.events_log = []

    def log(self, hook: Hook, ctx: dict):
        """Log an event with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        event = {
            "timestamp": timestamp,
            "hook": hook.value,
            "data": dict(ctx),
        }
        self.events_log.append(event)

        if self.verbose:
            self._print_event(timestamp, hook, ctx)

    def _print_event(self, timestamp: str, hook: Hook, ctx: dict):
        """Pretty print event for terminal debugging."""
        RESET = "\033[0m"
        GREEN = "\033[92m"
        BLUE = "\033[94m"
        YELLOW = "\033[93m"
        MAGENTA = "\033[95m"
        CYAN = "\033[96m"

        if "start" in hook.value:
            color = GREEN
            symbol = "▶"
        elif "complete" in hook.value or "end" in hook.value:
            color = BLUE
            symbol = "✓"
        elif "spawn" in hook.value:
            color = CYAN
            symbol = "→"
        elif "error" in hook.value:
            color = YELLOW
            symbol = "✗"
        elif "plan" in hook.value:
            color = MAGENTA
            symbol = "◉"
        else:
            color = RESET
            symbol = "•"

        print(f"{color}{timestamp} {symbol} {hook.value}{RESET}")

        if "task" in ctx:
            print(f"   Task: {ctx['task'][:60]}...")
        if "agent_type" in ctx:
            print(f"   Agent: {ctx['agent_type']}")
        if "plan_count" in ctx:
            print(f"   Plan: {ctx['plan_count']} agents")
        if "mode" in ctx:
            print(f"   Mode: {ctx['mode']}")
        if "cost" in ctx:
            print(f"   Cost: ${ctx['cost']:.4f}")
        if "total_cost" in ctx:
            print(f"   Total: ${ctx['total_cost']:.4f}")
        if "duration" in ctx:
            print(f"   Time: {ctx['duration']:.2f}s")
        if "error" in ctx:
            print(f"   Error: {ctx['error']}")
        print()

    def print_summary(self):
        """Print final summary - what developers see after run."""
        print("\n" + "=" * 70)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 70)

        event_counts = {}
        for event in self.events_log:
            hook = event["hook"]
            event_counts[hook] = event_counts.get(hook, 0) + 1

        print("\nEvents fired:")
        for hook, count in sorted(event_counts.items()):
            print(f"  {hook}: {count}")

        total_cost = sum(e["data"].get("cost", 0) for e in self.events_log if "cost" in e["data"])
        spawn_events = [e for e in self.events_log if "spawn" in e["hook"]]
        complete_events = [e for e in self.events_log if "complete" in e["hook"]]

        print(f"\nAgents spawned: {len(spawn_events)}")
        print(f"Agents completed: {len(complete_events)}")
        print(f"Total cost: ${total_cost:.4f}")
        print(f"Total events: {len(self.events_log)}")


def create_debug_pipeline():
    """Create pipeline with full debugging hooks."""

    orchestrator_model = almock

    all_agents = [
        TechResearchAgent,
        FinanceResearchAgent,
        HealthcareResearchAgent,
        EnergyResearchAgent,
        ConsumerResearchAgent,
        AIResearchAgent,
        GeopoliticsResearchAgent,
        RegulatoryResearchAgent,
        CompetitorAnalysisAgent,
        SummarizerAgent,
    ]

    pipeline = DynamicPipeline(
        agents=all_agents,
        model=orchestrator_model,
        max_parallel=10,
    )

    debugger = PipelineDebugger(verbose=True)

    # Register all hooks
    pipeline.events.on(
        Hook.DYNAMIC_PIPELINE_START, lambda ctx: debugger.log(Hook.DYNAMIC_PIPELINE_START, ctx)
    )
    pipeline.events.on(
        Hook.DYNAMIC_PIPELINE_PLAN, lambda ctx: debugger.log(Hook.DYNAMIC_PIPELINE_PLAN, ctx)
    )
    pipeline.events.on(
        Hook.DYNAMIC_PIPELINE_EXECUTE, lambda ctx: debugger.log(Hook.DYNAMIC_PIPELINE_EXECUTE, ctx)
    )
    pipeline.events.on(
        Hook.DYNAMIC_PIPELINE_AGENT_SPAWN,
        lambda ctx: debugger.log(Hook.DYNAMIC_PIPELINE_AGENT_SPAWN, ctx),
    )
    pipeline.events.on(
        Hook.DYNAMIC_PIPELINE_AGENT_COMPLETE,
        lambda ctx: debugger.log(Hook.DYNAMIC_PIPELINE_AGENT_COMPLETE, ctx),
    )
    pipeline.events.on(
        Hook.DYNAMIC_PIPELINE_END, lambda ctx: debugger.log(Hook.DYNAMIC_PIPELINE_END, ctx)
    )
    pipeline.events.on(
        Hook.DYNAMIC_PIPELINE_ERROR, lambda ctx: debugger.log(Hook.DYNAMIC_PIPELINE_ERROR, ctx)
    )

    # Developer can intercept and modify at any point
    pipeline.events.before(
        Hook.DYNAMIC_PIPELINE_AGENT_SPAWN,
        lambda ctx: print(
            f"\n   >>> DEBUG BEFORE: About to spawn {ctx.get('agent_type', 'unknown')}\n"
        ),
    )

    pipeline.events.after(
        Hook.DYNAMIC_PIPELINE_AGENT_COMPLETE,
        lambda ctx: print(
            f"\n   >>> DEBUG AFTER: Agent {ctx.get('agent_type', 'unknown')} finished with cost ${ctx.get('cost', 0):.4f}\n"
        ),
    )

    return pipeline, debugger


def run_market_research():
    """Run complex market research with full debugging."""

    print("\n" + "=" * 70)
    print("MASTER DYNAMIC PIPELINE - Market Research Demo")
    print("=" * 70)
    print(f"Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")

    pipeline, debugger = create_debug_pipeline()

    task = """
    Conduct comprehensive market research on AI in Healthcare for a VC firm.

    Research should cover:
    1. Technology trends and innovations
    2. Financial metrics and funding landscape
    3. Healthcare industry adoption
    4. Energy/sustainability impact
    5. Consumer/digital health trends
    6. Competitive landscape
    7. Regulatory environment
    8. Geopolitical factors

    Provide a consolidated report with charts and financial analysis.
    """

    start_time = time.time()

    try:
        result = pipeline.run(task, mode="parallel")

        elapsed = time.time() - start_time

        debugger.print_summary()

        print("\n" + "=" * 70)
        print("FINAL RESULT")
        print("=" * 70)
        print(f"\nExecution time: {elapsed:.2f}s")
        print(f"Total cost: ${result.cost:.4f}")
        print(f"Total tokens: {result.tokens.total_tokens}")
        print("\nReport preview (first 500 chars):")
        print("-" * 40)
        print(result.content[:500])
        print("...")

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        debugger.print_summary()
        raise


if __name__ == "__main__":
    run_market_research()
