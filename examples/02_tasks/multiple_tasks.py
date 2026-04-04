"""Multiple Tasks Example -- Agent with several plain methods as entry points.

Demonstrates:
- Defining multiple methods on a single agent
- Chaining methods: research first, then write
- Each method is an independent, reusable entry point

Run: python examples/02_tasks/multiple_tasks.py
"""

from __future__ import annotations

from syrin import Agent, Model
from syrin.debug import Pry

_PRY = Pry.from_debug_flag()


class Writer(Agent):
    """Agent with research and write methods."""

    name = "writer"
    description = "Writer with research(topic) and write(topic, style) methods"
    model = Model.mock()
    system_prompt = "You are a professional writer. Research thoroughly and write clearly."

    def research(self, topic: str) -> str:
        """Research a topic and return key points."""
        r = self.run(f"Research {topic}. List 3-5 key points.")
        return r.content or ""

    def write(self, topic: str, style: str = "professional") -> str:
        """Write about a topic in the given style."""
        r = self.run(f"Write a short paragraph about {topic} in a {style} style.")
        return r.content or ""


if __name__ == "__main__":
    use_debug_ui = _PRY is not None
    writer = Writer()

    if use_debug_ui:
        out: list[str] = ["", ""]

        def _research() -> None:
            out[0] = writer.research("artificial intelligence")

        def _write() -> None:
            out[1] = writer.write("artificial intelligence", style="casual")

        ui = _PRY or Pry()
        with ui:
            ui.attach(writer)
            ui.run(_research).join()
            ui.run(_write).join()
            ui.wait()

        research_result, write_result = out[0], out[1]
    else:
        research_result = writer.research("artificial intelligence")
        write_result = writer.write("artificial intelligence", style="casual")

    print("--- Research ---")
    print(research_result)
    print("\n--- Write ---")
    print(write_result)
