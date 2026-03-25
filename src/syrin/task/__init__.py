"""Task decorator for agent tasks."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import get_type_hints

from syrin.types import TaskSpec


def task(  # type: ignore[explicit-any]
    func: Callable[..., object] | None = None,
    *,
    name: str | None = None,
) -> TaskSpec | Callable[..., TaskSpec]:
    """Decorator that marks a method as an agent task.

    Invoke like agent.task_name(args). Parameter types and return type
    are inferred from type hints.

    Args:
        func: Function to decorate. If None, returns a decorator.
        name: Override task name. Default: function name.

    Returns:
        TaskSpec when used as @task; callable decorator when used as @task(name="...").

    Example:
        >>> class MyAgent(Agent):
        ...     @task
        ...     def summarize(self, text: str) -> str:
        ...         return self.response(f"Summarize: {text}").content
    """

    def decorator(f: Callable[..., object]) -> TaskSpec:  # type: ignore[explicit-any]
        task_name = name or f.__name__
        hints = get_type_hints(f) if hasattr(f, "__annotations__") else {}
        sig = inspect.signature(f)
        parameters: dict[str, object] = {}
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            parameters[param_name] = str(hints.get(param_name, param.annotation))
        return_type = hints.get("return", None)
        return TaskSpec(
            name=task_name,
            parameters=parameters,
            return_type=return_type,
            func=f,
        )

    if func is not None:
        return decorator(func)
    return decorator
