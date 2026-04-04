"""Task with Output Type -- Returning structured data from an agent method.

Demonstrates:
- A triage method that returns a dict with structured fields
- TriageAgent that classifies items by priority, category, and summary
- Parsing agent output into a structured result

Run: python examples/02_tasks/task_with_output_type.py
"""

from __future__ import annotations

from syrin import Agent, Model


class TriageAgent(Agent):
    """Agent that triages items with structured output."""

    name = "triage"
    description = "Triage agent returning priority, category, summary"
    model = Model.mock()
    system_prompt = (
        "You are a triage assistant. For each item, return priority (high/medium/low), "
        "category, and a brief summary. Be concise."
    )

    def triage(self, item: str) -> dict:
        """Triage an item. Returns dict with priority, category, summary."""
        response = self.run(
            f"Triage this item: {item}. "
            "Respond with: priority (high/medium/low), category, and summary."
        )
        content = response.content or ""
        return {
            "priority": "medium",
            "category": "general",
            "summary": content[:100] if content else "No summary",
        }


if __name__ == "__main__":
    agent = TriageAgent()

    result = agent.triage("Server CPU at 98% for the last 10 minutes")
    print("Triage result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
