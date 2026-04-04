"""Single Task Example -- Defining named entry points as plain methods.

Demonstrates:
- A Researcher agent with a research(topic) method
- Invoking the method and printing the result

Run: python examples/02_tasks/single_task.py
"""

from __future__ import annotations

from syrin import Agent, Model


class Researcher(Agent):
    """Agent that researches topics."""

    name = "researcher"
    description = "Research assistant with a research(topic) method"
    model = Model.mock()
    system_prompt = "You are a research assistant. Provide concise, factual summaries."

    def research(self, topic: str) -> str:
        """Research a topic and return a summary."""
        response = self.run(f"Research the following topic and summarize: {topic}")
        return response.content or ""


if __name__ == "__main__":
    researcher = Researcher()

    result = researcher.research("quantum computing")
    print("Research result:")
    print(result)
