---
title: Reflection Topology
description: Writer-critic loops that iteratively improve output quality
weight: 86
---

## The Edit-Until-Good Loop

One agent writes something. Another agent reviews it and gives a score. The first agent revises based on the feedback. Repeat until the score is high enough.

That's the REFLECTION topology. It's a producer-critic loop that keeps running until the output meets your quality bar or hits the maximum number of rounds. Think of it as automated editing — you don't need a human in the loop to enforce quality.

## Basic Reflection

```python
import asyncio
from syrin import Agent, Model
from syrin.enums import SwarmTopology
from syrin.swarm import Swarm, SwarmConfig
from syrin.swarm.topologies._reflection import ReflectionConfig

class WriterAgent(Agent):
    model = Model.mock()
    system_prompt = "You write high-quality blog posts about technology."

class EditorAgent(Agent):
    model = Model.mock()
    system_prompt = """You review blog posts.
    Return a score from 0.0 to 1.0 and specific feedback.
    Format: 'Score: 0.8. The introduction is strong but the conclusion is weak...'"""

async def main():
    swarm = Swarm(
        agents=[WriterAgent()],
        goal="Write a 300-word post about why AI agents are changing software development",
        config=SwarmConfig(topology=SwarmTopology.REFLECTION),
        reflection_config=ReflectionConfig(
            producer=WriterAgent,
            critic=EditorAgent,
            max_rounds=3,
            stop_when=lambda ro: ro.score >= 0.85,
        ),
    )
    result = await swarm.run()

    print(f"Final output: {result.content[:60]}")

    rr = result.reflection_result
    print(f"Rounds completed: {rr.rounds_completed}")
    print(f"Final round: {rr.final_round}")

    for round_output in rr.round_outputs:
        print(f"\nRound {round_output.round_index}:")
        print(f"  Score: {round_output.score}")
        print(f"  Producer: {round_output.producer_output[:40]}")
        print(f"  Critic: {round_output.critic_feedback[:40]}")

asyncio.run(main())
```

Output:

```
Final output: Lorem ipsum dolor sit amet, consectetur adipiscing
Rounds completed: 2
Final round: 1

Round 0:
  Score: 0.5
  Producer: Lorem ipsum dolor sit amet, consecte
  Critic: Lorem ipsum dolor sit amet, consecte

Round 1:
  Score: 0.5
  Producer: Lorem ipsum dolor sit amet, consecte
  Critic: Lorem ipsum dolor sit amet, consecte
```

With the mock model, scores are fixed at 0.5 (the mock doesn't extract real scores from lorem ipsum). With a real model, the editor would return parseable feedback and actual scores, and the loop would stop early when the score reaches `0.85`.

## The ReflectionConfig

**`producer`** — the agent class that creates content. Gets the original goal, then in subsequent rounds gets the previous output + the critic's feedback.

**`critic`** — the agent class that reviews content. Receives the producer's output and returns feedback plus a numeric score. The score is extracted from the critic's response text.

**`max_rounds`** — maximum number of producer-critic cycles. The loop always stops here even if the quality threshold isn't reached.

**`stop_when`** — a function that takes a `RoundOutput` and returns `True` if the loop should stop. The `RoundOutput` has a `.score` field. When this returns `True`, the loop exits early with the current best output.

## The ReflectionResult

After `swarm.run()`, inspect `result.reflection_result`:

- `rr.content` — the final output after all rounds
- `rr.rounds_completed` — how many rounds actually ran
- `rr.final_round` — the zero-based index of the last round
- `rr.round_outputs` — list of `RoundOutput` objects, one per round

Each `RoundOutput` has:
- `ro.round_index` — which round (0-based)
- `ro.producer_output` — what the writer produced
- `ro.critic_feedback` — what the editor said
- `ro.score` — the extracted quality score (0.0–1.0)
- `ro.stop_condition_met` — whether `stop_when` returned `True` on this round

## Making the Critic Effective

The critic's quality score is extracted from its text response. To make this work reliably with a real model, your critic's system prompt should instruct it to include a parseable score. Something like:

```python
class EditorAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key="your-key")
    system_prompt = """You are a professional editor. Review the content and provide:
    1. Specific, actionable feedback
    2. A quality score between 0.0 and 1.0

    Always end your response with: 'Quality score: X.XX'
    where X.XX is your score (e.g. 'Quality score: 0.78')."""
```

The reflection engine parses the numeric score out of the critic's response and uses it to evaluate the `stop_when` condition.

## When to Use Reflection

Use reflection when quality improves with feedback cycles. Common use cases:

- Long-form writing (articles, reports, documentation)
- Code generation where a reviewer checks for bugs or style
- Translation or rephrasing tasks where a second pass catches issues
- Any task where "good enough on the first try" is less likely than "great after revision"

The cost is more LLM calls — typically `max_rounds * 2` calls (one producer + one critic per round). Set a budget on the swarm to cap the total spend.

## What's Next

- [Consensus](/agent-kit/multi-agent/consensus) — Multi-agent voting for reliable answers
- [Swarm](/agent-kit/multi-agent/swarm) — All swarm topologies and shared budget
- [Pipeline](/agent-kit/multi-agent/pipeline) — Simpler sequential chaining without iteration
