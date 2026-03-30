"""Public agent package facade.

This package exposes the end-user agent API while keeping implementation details in
private modules. Import from ``syrin.agent`` when you need the main agent class, and
import from submodules only when you are intentionally working with lower-level,
internal Syrin building blocks.

Why this package exists:
    - It gives application code one stable import path for the main agent type.
    - It avoids placing operational logic inside ``__init__.py``, which keeps package
      import behavior predictable and easier to maintain.
    - It lets internal implementation move between private modules without forcing
      users to rewrite their imports.

Typical usage:
    >>> from syrin.agent import Agent
    >>> from syrin.model import Model
    >>> agent = Agent(
    ...     model=Model.OpenAI("gpt-4o-mini"),
    ...     system_prompt="You are concise and helpful.",
    ... )
    >>> result = agent.run("Summarize this document.")

What is exported here:
    Agent:
        The primary class for building and running AI agents with models, tools,
        guardrails, memory, budgets, serving adapters, and debugging support.
"""

from syrin.agent._core import Agent

__all__ = ["Agent"]
