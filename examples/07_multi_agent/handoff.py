"""Agent delegation via spawn() — pass work from one agent to another.

One agent analyzes a topic, then spawns a second agent to present the results.

Run:
    python examples/07_multi_agent/handoff.py
"""

from syrin import Agent, Model

model = Model.mock(latency_min=0, latency_max=0)


class Analyzer(Agent):
    model = model
    system_prompt = "You are an analyzer. Analyze information and provide key findings."


class Presenter(Agent):
    model = model
    system_prompt = "You are a presenter. Present information clearly and concisely."


# Step 1: Analyzer processes the request
analyzer = Analyzer()
analysis = analyzer.run("Analyze the benefits of renewable energy")
print("=== Analyzer ===")
print(f"{analysis.content[:120]}...")
print(f"Cost: ${analysis.cost:.6f}")
print()

# Step 2: Spawn Presenter with the analysis as input
# spawn() creates a child agent, runs it, and returns the response.
presentation = analyzer.spawn(Presenter, task=f"Present this analysis: {analysis.content[:200]}")
print("=== Presenter (via spawn) ===")
print(f"{presentation.content[:120]}...")
print(f"Cost: ${presentation.cost:.6f}")

# --- Serve (uncomment to try playground) ---
# analyzer.serve(port=8000, enable_playground=True)
