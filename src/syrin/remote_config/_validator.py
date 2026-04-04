"""RemoteConfigValidator — validation rules for remote config pushes."""

from __future__ import annotations


class ConfigValidationError(Exception):
    """Raised when a remote config push fails a validation rule.

    Attributes:
        message: Human-readable description of the violation.
        field: The config field or section that failed validation.
        value: The offending value that was rejected.
    """

    def __init__(self, message: str, field: str, value: object) -> None:
        """Create a ConfigValidationError.

        Args:
            message: Human-readable description of the violation.
            field: The config field or section that failed validation.
            value: The offending value that was rejected.
        """
        super().__init__(message)
        self.field = field
        self.value = value


class RemoteConfigValidator:
    """Validation rules applied before each remote config push.

    Instances are callable: ``validator(new_config, agent) -> None``.
    They raise :class:`ConfigValidationError` if the incoming config
    violates the rule.  Multiple validators can be chained by passing a list
    to :class:`~syrin.remote_config.RemoteConfig`.

    Use the factory class methods to create common validators:

    Example:
        >>> v = RemoteConfigValidator.max_budget(5.00)
        >>> v({"budget": 3.00}, agent)  # OK — no exception
        >>> v({"budget": 9.00}, agent)  # raises ConfigValidationError
    """

    def __init__(self, _rule: object = None) -> None:
        """Internal: do not instantiate directly — use the factory class methods."""
        self._rule: object = _rule

    # ------------------------------------------------------------------
    # Factory class methods
    # ------------------------------------------------------------------

    @classmethod
    def max_budget(cls, limit: float) -> RemoteConfigValidator:
        """Create a validator that rejects budget values exceeding *limit*.

        The validator inspects the ``"budget"`` key in the incoming config
        dict.  If the value is numeric and greater than *limit*, it raises
        :class:`ConfigValidationError`.

        Args:
            limit: Maximum permitted budget (inclusive).

        Returns:
            A configured :class:`RemoteConfigValidator` instance.

        Example:
            >>> v = RemoteConfigValidator.max_budget(10.00)
            >>> v({"budget": 10.00}, agent)   # OK
            >>> v({"budget": 10.01}, agent)   # raises ConfigValidationError
        """
        validator = cls()
        validator._rule = ("max_budget", limit)
        return validator

    @classmethod
    def require_guardrail(cls, name: str) -> RemoteConfigValidator:
        """Create a validator that rejects configs lacking a named guardrail.

        The validator checks that the incoming config dict either does not
        touch guardrails at all, or explicitly keeps *name* enabled.  It
        rejects configs that would disable or remove the required guardrail.

        Args:
            name: Name of the guardrail that must remain enabled.

        Returns:
            A configured :class:`RemoteConfigValidator` instance.

        Example:
            >>> v = RemoteConfigValidator.require_guardrail("PromptInjectionGuardrail")
            >>> v({"guardrails": {"PromptInjectionGuardrail": True}}, agent)  # OK
            >>> v({"guardrails": {"PromptInjectionGuardrail": False}}, agent)  # raises
        """
        validator = cls()
        validator._rule = ("require_guardrail", name)
        return validator

    # ------------------------------------------------------------------
    # Callable protocol
    # ------------------------------------------------------------------

    def __call__(self, new_config: dict[str, object], agent: object) -> None:
        """Validate *new_config* against this rule.

        Args:
            new_config: The incoming config changes as a flat or nested dict.
            agent: The agent instance the config would be applied to.

        Raises:
            ConfigValidationError: If the config violates this rule.
        """
        if not isinstance(self._rule, tuple):
            return

        rule_type = self._rule[0]

        if rule_type == "max_budget":
            limit = self._rule[1]
            budget_val = new_config.get("budget")
            if (
                budget_val is not None
                and isinstance(budget_val, (int, float))
                and float(budget_val) > float(limit)
            ):
                raise ConfigValidationError(
                    f"Budget {budget_val} exceeds maximum allowed {limit}",
                    field="budget",
                    value=budget_val,
                )

        elif rule_type == "require_guardrail":
            required_name: str = self._rule[1]
            guardrails_val = new_config.get("guardrails")
            if guardrails_val is not None and isinstance(guardrails_val, dict):
                # The config is touching guardrails — check the required one is not disabled
                enabled = guardrails_val.get(required_name)
                if enabled is False:
                    raise ConfigValidationError(
                        f"Guardrail '{required_name}' is required and cannot be disabled",
                        field="guardrails",
                        value=guardrails_val,
                    )
                if enabled is None and required_name not in guardrails_val:
                    raise ConfigValidationError(
                        f"Guardrail '{required_name}' is required but missing from config",
                        field="guardrails",
                        value=guardrails_val,
                    )
