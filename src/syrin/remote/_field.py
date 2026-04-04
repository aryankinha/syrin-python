"""RemoteField and RemoteConfigAccess — field-level access control for remote config pushes."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from syrin.enums import Hook


class RemoteField(StrEnum):
    """Configurable field categories for remote config access control.

    Each value is a dotted-path prefix. A path like ``"model.name"`` matches
    ``RemoteField.MODEL`` because it starts with ``"model."``.

    Attributes:
        MODEL: Model name, provider, and generation settings.
        BUDGET: Cost limits, rate limits, per-agent caps.
        MEMORY: Memory backend, decay, top_k.
        SYSTEM_PROMPT: Agent system prompt text.
        GUARDRAILS: Guardrail enable/disable.
        MAX_COST: Budget max_cost field specifically.
        CONTEXT: Context window settings.
    """

    MODEL = "model"
    BUDGET = "budget"
    MEMORY = "memory"
    SYSTEM_PROMPT = "system_prompt"
    GUARDRAILS = "guardrails"
    MAX_COST = "max_cost"
    CONTEXT = "context"


class RemoteConfigAccess:
    """Field-level access control for remote config pushes.

    Use ``allow=`` to whitelist specific field categories, or ``deny=`` to
    blacklist them. When ``allow`` is set, only listed fields are accepted.
    When ``deny`` is set, all fields except listed are accepted. When neither
    is set, all fields are accepted.

    Internally, allow/deny lists are stored as immutable ``frozenset`` values
    to prevent accidental mutation after construction.

    Example:
        >>> access = RemoteConfigAccess(allow=[RemoteField.MODEL])
        >>> access.is_allowed("model.name")
        True
        >>> access.is_allowed("budget.max_cost")
        False
    """

    def __init__(
        self,
        allow: list[RemoteField] | None = None,
        deny: list[RemoteField] | None = None,
    ) -> None:
        """Initialise access control with optional allow and deny lists.

        Args:
            allow: If set, only paths matching these field categories are allowed.
            deny: If set, paths matching these field categories are denied.
        """
        self._allow: frozenset[RemoteField] = frozenset(allow) if allow else frozenset()
        self._deny: frozenset[RemoteField] = frozenset(deny) if deny else frozenset()

    def is_allowed(self, path: str) -> bool:
        """Check whether a dotted config path is allowed.

        A path matches a ``RemoteField`` if it starts with ``field.value + "."``.

        Args:
            path: Dotted config path, e.g. ``"model.name"`` or ``"budget.max_cost"``.

        Returns:
            ``True`` if the path is permitted by the current access policy.
        """
        matched_field = self._match_field(path)

        if self._allow:
            return matched_field in self._allow

        if self._deny:
            return matched_field not in self._deny

        # No allow/deny: permit everything
        return True

    def check_field(
        self,
        path: str,
        fire_fn: Callable[[Hook, dict[str, object]], None] | None = None,
    ) -> bool:
        """Check a path and optionally fire ``Hook.CONFIG_REJECTED`` if denied.

        Args:
            path: Dotted config path to check.
            fire_fn: Optional hook-firing callback. Receives ``(Hook, dict)`` when
                the path is denied.

        Returns:
            ``True`` if the path is allowed, ``False`` otherwise.
        """
        allowed = self.is_allowed(path)
        if not allowed and fire_fn is not None:
            from syrin.enums import Hook

            fire_fn(
                Hook.CONFIG_REJECTED,
                {"reason": "field_denied", "path": path},
            )
        return allowed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _match_field(self, path: str) -> RemoteField | None:
        """Return the ``RemoteField`` whose prefix matches *path*, or ``None``."""
        for field in RemoteField:
            if path.startswith(field.value + ".") or path == field.value:
                return field
        return None
