"""
Tool documentation — param_descriptions, returns, and docstring auto-parsing.

Shows all the ways to document tools so the LLM understands:
  - WHAT each parameter means (not just its type)
  - WHAT the tool returns (so the LLM can interpret the result)
  - HOW to call it (examples)

Run: python examples/05_tools/tool_documentation.py
"""

import json

from syrin import Agent, Model, tool

# =============================================================================
# 1. DOCSTRING — the zero-effort path
# =============================================================================
# Write a normal Google-style docstring. @tool parses it automatically.
# Your IDE, help(), and the LLM all see the same documentation.


@tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for current information on any topic.

    Args:
        query: The search query. Use natural language or keywords.
        max_results: Maximum number of results to return. Default: 5.

    Returns:
        JSON array of objects, each with keys: title, url, snippet.
    """
    return f'[{{"title": "Result 1", "url": "https://example.com", "snippet": "{query}"}}]'


# =============================================================================
# 2. EXPLICIT — no docstring needed
# =============================================================================
# Useful for generated code, short functions, or when you want the LLM-facing
# text to be different from what appears in your IDE hover.


@tool(
    description="Look up the current exchange rate between two currencies.",
    param_descriptions={
        "base": "The source currency code, e.g. 'USD' or 'EUR'",
        "target": "The target currency code, e.g. 'JPY' or 'GBP'",
    },
    returns="A float representing how many units of `target` equal 1 unit of `base`.",
    examples=[
        "exchange_rate('USD', 'EUR')",
        "exchange_rate('GBP', 'JPY')",
    ],
)
def exchange_rate(base: str, target: str) -> float:
    rates = {"USD/EUR": 0.92, "USD/JPY": 149.5, "GBP/JPY": 188.0}
    return rates.get(f"{base}/{target}", 1.0)


# =============================================================================
# 3. MIXED — docstring for the IDE, explicit override for the LLM
# =============================================================================
# Explicit kwargs always win over the docstring.
# Write a full docstring for your team; override just what the LLM needs.


@tool(
    param_descriptions={
        "lat": "Latitude in decimal degrees, e.g. 35.6762 for Tokyo",
        "lon": "Longitude in decimal degrees, e.g. 139.6503 for Tokyo",
    },
    returns="JSON object with keys: city, country, timezone, elevation_m.",
)
def reverse_geocode(lat: float, lon: float) -> str:
    """Reverse geocode a coordinate to a location name.

    This is the internal note about the implementation — the LLM does not
    see this paragraph, only the first line and the explicit overrides above.

    Args:
        lat: Internal note about latitude (overridden by param_descriptions=)
        lon: Internal note about longitude (overridden by param_descriptions=)

    Returns:
        Internal note about return format (overridden by returns=)
    """
    return '{"city": "Tokyo", "country": "Japan", "timezone": "Asia/Tokyo", "elevation_m": 40}'


# =============================================================================
# 4. INSPECT — what the LLM actually sees
# =============================================================================


def show_tool_schema(t) -> None:
    schema = t.to_format()["function"]
    props = t.parameters_schema.get("properties", {})

    print(f"\n{'=' * 50}")
    print(f"Tool: {t.name}")
    print(f"Description:\n  {schema.get('description', '').replace(chr(10), chr(10) + '  ')}")
    print("Parameters:")
    for name, prop in props.items():
        desc = prop.get("description", "(no description)")
        typ = prop.get("type", "?")
        print(f"  {name}: {typ} — {desc}")


def main() -> None:
    print("=== What the LLM sees for each tool ===")

    show_tool_schema(search_web)
    show_tool_schema(exchange_rate)
    show_tool_schema(reverse_geocode)

    # ==========================================================================
    # 5. AGENT WITH ALL THREE TOOLS
    # ==========================================================================
    print("\n\n=== Agent using documented tools ===\n")

    class ResearchAgent(Agent):
        model = Model.mock(latency_seconds=0.01, lorem_length=40)
        system_prompt = "You are a research assistant with web search, currency, and geo tools."
        tools = [search_web, exchange_rate, reverse_geocode]

    agent = ResearchAgent()
    print(f"Tools registered: {[t.name for t in agent.tools]}")

    response = agent.run("What is the USD to EUR exchange rate today?")
    print(f"Response: {response.content[:60]}")
    print(f"Cost:     ${response.cost:.6f}")

    # ==========================================================================
    # 6. TOON SAVINGS WITH PARAMETER DESCRIPTIONS
    # ==========================================================================
    print("\n\n=== Token savings with parameter descriptions ===\n")

    json_schema = json.dumps(search_web.parameters_schema, indent=2)
    toon_schema = search_web.schema_to_toon()
    savings = ((len(json_schema) - len(toon_schema)) / len(json_schema)) * 100

    print(f"JSON schema ({len(json_schema)} chars):")
    print(json_schema)
    print(f"\nTOON schema ({len(toon_schema)} chars):")
    print(toon_schema)
    print(f"\nSavings: {savings:.1f}%")


if __name__ == "__main__":
    main()
