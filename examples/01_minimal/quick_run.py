"""Quick Run — Fastest way to use Syrin.

Three ways to get started, from simplest to most flexible.

Run:
    python examples/01_minimal/quick_run.py
"""

from syrin import Agent, Budget, Model, warn_on_exceeded

model = Model.Almock()  # No API key needed

# --- Way 1: Builder (recommended) ---
agent = (
    Agent.builder(model)
    .with_system_prompt("Explain like I'm five years old.")
    .with_budget(Budget(max_cost=0.50))
    .build()
)
response = agent.run("What is gravity?")
print(f"Builder: {response.content[:80]}...")
print()

# --- Way 2: Preset (one-liner) ---
agent2 = Agent.basic(model, system_prompt="You are a helpful assistant.")
response2 = agent2.run("What is 2 + 2?")
print(f"Preset:  {response2.content}")
print()


# --- Way 3: Class-based (best for reuse) ---
class MyAgent(Agent):
    model = model
    system_prompt = "You are helpful and concise."
    budget = Budget(max_cost=1.00, on_exceeded=warn_on_exceeded)


agent3 = MyAgent()
response3 = agent3.run("Hello!")
print(f"Class:   {response3.content}")
