"""syrin.budget_wrap() — budget tracking and enforcement for any callable."""

from __future__ import annotations

import asyncio
import functools
import threading
from collections.abc import Callable

from syrin.budget import Budget
from syrin.exceptions import BudgetExceededError


def budget_wrap(  # type: ignore[explicit-any]
    fn: Callable[..., object] | None = None,
    *,
    budget: Budget | None = None,
    cost: float = 0.0,
    cost_fn: Callable[[object], float] | None = None,
) -> Callable[..., object]:
    """Wrap any callable with budget tracking and enforcement.

    Use as a decorator or inline wrapper to add budget protection to existing
    LLM callables without converting them into Agents.

    Args:
        fn: The function to wrap. When used as ``@budget_wrap()`` (with args), ``fn``
            is ``None`` and a decorator is returned. When used as
            ``budget_wrap(my_fn, ...)`` or ``@budget_wrap`` (no args), ``fn`` is the
            wrapped callable.
        budget: Budget config. When ``None``, no enforcement (pass-through). Default: ``None``.
        cost: Fixed cost in USD to record for each call. Checked against ``budget.max_cost``
            before the call executes. Default: ``0.0``.
        cost_fn: Callable that receives the function's return value and returns the
            cost in USD. Called after the wrapped function returns. Useful when cost
            depends on output (e.g. token count). Default: ``None``.

    Returns:
        Wrapped function (sync stays sync, async stays async).

    Raises:
        BudgetExceededError: When ``cost`` or ``cost_fn`` result exceeds ``budget.max_cost``.

    Example::

        import syrin
        from syrin.budget import Budget

        @syrin.budget_wrap(budget=Budget(max_cost=0.10), cost=0.01)
        def my_llm_call(prompt: str) -> str:
            import openai
            resp = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content

        # Inline usage
        wrapped = syrin.budget_wrap(my_fn, budget=Budget(max_cost=0.50))
    """

    def _decorator(f: Callable[..., object]) -> Callable[..., object]:  # type: ignore[explicit-any]
        _state: dict[str, float] = {"spent": 0.0}
        _lock = threading.Lock()

        def _pre_check(call_cost: float) -> None:
            if budget is None:
                return
            max_cost = getattr(budget, "max_cost", None)
            if max_cost is None:
                return
            with _lock:
                if _state["spent"] + call_cost > max_cost:
                    raise BudgetExceededError(
                        f"budget_wrap: budget exceeded — would spend "
                        f"${_state['spent'] + call_cost:.4f} but limit is ${max_cost:.4f}",
                        current_cost=_state["spent"] + call_cost,
                        limit=max_cost,
                    )

        def _post_record(actual_cost: float) -> None:
            with _lock:
                _state["spent"] += actual_cost

        if asyncio.iscoroutinefunction(f):

            @functools.wraps(f)
            async def _async_wrapper(*args: object, **kwargs: object) -> object:
                if cost > 0:
                    _pre_check(cost)
                result = await f(*args, **kwargs)
                actual = cost_fn(result) if cost_fn is not None else cost
                if actual > 0:
                    _post_record(actual)
                return result

            return _async_wrapper

        @functools.wraps(f)
        def _sync_wrapper(*args: object, **kwargs: object) -> object:
            if cost > 0:
                _pre_check(cost)
            result = f(*args, **kwargs)
            actual = cost_fn(result) if cost_fn is not None else cost
            if actual > 0:
                _post_record(actual)
            return result

        return _sync_wrapper

    if fn is not None:
        return _decorator(fn)
    return _decorator
