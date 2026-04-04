"""PromptClassifier with Agent — embedding-based task detection, no task_override.

Requires: uv pip install 'syrin[classifier-embeddings]'

Uses PromptClassifier to auto-detect task type from prompt. No need to pass
task_type in response() for production use.
"""

from __future__ import annotations

from syrin import Agent
from syrin.model import Model
from syrin.router import (
    ModelRouter,
    PromptClassifier,
    RoutingConfig,
    RoutingMode,
    TaskType,
)


def main() -> None:
    general_m = Model.mock(
        latency_min=0,
        latency_max=0,
        profile_name="general",
        strengths=[TaskType.GENERAL, TaskType.CREATIVE],
        priority=90,
    )
    code_m = Model.mock(
        latency_min=0,
        latency_max=0,
        profile_name="code",
        strengths=[TaskType.CODE, TaskType.REASONING],
        priority=100,
    )

    models_list = [general_m, code_m]
    classifier = PromptClassifier(
        min_confidence=0.6,
        low_confidence_fallback=TaskType.GENERAL,
        examples={
            TaskType.CODE: ["implement", "function", "debug", "fix the bug"],
            TaskType.GENERAL: ["hello", "what is", "explain"],
        },
    )
    router = ModelRouter(
        models=models_list,
        routing_mode=RoutingMode.AUTO,
        classifier=classifier,
    )

    agent = Agent(
        model=models_list,
        model_router=RoutingConfig(router=router),
        system_prompt="You are helpful.",
    )

    # No task_type passed; classifier detects from prompt
    prompts = [
        "Write a Python function to reverse a string",
        "Hello! How are you?",
        "Fix this: def foo(): return None",
    ]
    for p in prompts:
        r = agent.run(p)
        tt = r.routing_reason.task_type if r.routing_reason else "N/A"
        sel = r.routing_reason.selected_model if r.routing_reason else "N/A"
        print(f"  {p[:50]!r} -> {tt} -> {sel}")


if __name__ == "__main__":
    main()
