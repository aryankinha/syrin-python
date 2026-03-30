"""Multiple Tasks Example -- Agent with several @task methods.

Demonstrates:
- Defining multiple tasks on a single agent
- Chaining tasks: research first, then write
- Each task is an independent named entry point

Run: python examples/02_tasks/multiple_tasks.py
"""

from __future__ import annotations

from syrin import Agent, Model, task
from syrin.debug import Pry

_PRY = Pry.from_debug_flag()

# --- Define the agent with two tasks ---


class Writer(Agent):
    """Agent with research and write tasks."""

    _agent_name = "writer"
    _agent_description = "Writer with research(topic) and write(topic, style) tasks"
    model = Model.Almock()
    system_prompt = "You are a professional writer. Research thoroughly and write clearly."

    @task
    def research(self, topic: str) -> str:
        """Research a topic and return key points."""
        r = self.run(f"Research {topic}. List 3-5 key points.")
        return r.content or ""

    @task
    def write(self, topic: str, style: str = "professional") -> str:
        """Write about a topic in the given style."""
        r = self.run(f"Write a short paragraph about {topic} in a {style} style.")
        return r.content or ""


# --- Run it ---

if __name__ == "__main__":
    use_debug_ui = _PRY is not None
    writer = Writer()

    if use_debug_ui:
        # Use ui.run() to execute tasks in a background thread so the TUI key
        # loop (↑↓ navigate stream, Tab/Shift+Tab switch right panel, Enter detail,
        # ESC back, p pause/resume, q quit) stays fully responsive during execution.
        out: list[str] = ["", ""]

        def _research() -> None:
            out[0] = writer.research("artificial intelligence")

        def _write() -> None:
            out[1] = writer.write("artificial intelligence", style="casual")

        ui = _PRY or Pry()
        with ui:
            ui.attach(writer)
            ui.run(_research).join()  # run in bg thread; join before next task
            ui.run(_write).join()
            ui.wait()  # hold TUI open — press q to exit

        research_result, write_result = out[0], out[1]
    else:
        research_result = writer.research("artificial intelligence")
        write_result = writer.write("artificial intelligence", style="casual")

    # Printed after TUI exits (normal terminal restored)
    print("--- Research Task ---")
    print(research_result)
    print("\n--- Write Task ---")
    print(write_result)

    # Optional: serve with playground UI
    # writer.serve(port=8000, enable_playground=True, debug=True)
