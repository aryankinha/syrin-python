"""Tests for RemoteConfigValidator."""

from __future__ import annotations

import pytest

from syrin.remote_config import ConfigValidationError, RemoteConfigValidator


class TestMaxBudgetValidator:
    """Tests for RemoteConfigValidator.max_budget()."""

    def test_rejects_budget_exceeding_limit(self) -> None:
        v = RemoteConfigValidator.max_budget(10.00)
        with pytest.raises(ConfigValidationError) as exc_info:
            v({"budget": 10.01}, object())
        assert exc_info.value.field == "budget"
        assert exc_info.value.value == 10.01

    def test_accepts_budget_equal_to_limit(self) -> None:
        v = RemoteConfigValidator.max_budget(10.00)
        # Should not raise
        v({"budget": 10.00}, object())

    def test_accepts_budget_below_limit(self) -> None:
        v = RemoteConfigValidator.max_budget(10.00)
        v({"budget": 0.50}, object())

    def test_accepts_budget_zero(self) -> None:
        v = RemoteConfigValidator.max_budget(10.00)
        v({"budget": 0.0}, object())

    def test_no_budget_key_is_accepted(self) -> None:
        v = RemoteConfigValidator.max_budget(10.00)
        v({"model": "gpt-4o"}, object())

    def test_non_numeric_budget_is_ignored(self) -> None:
        v = RemoteConfigValidator.max_budget(10.00)
        # Non-numeric budget value should not raise — no comparison possible
        v({"budget": "unlimited"}, object())


class TestRequireGuardrailValidator:
    """Tests for RemoteConfigValidator.require_guardrail()."""

    def test_accepts_config_with_required_guardrail_enabled(self) -> None:
        v = RemoteConfigValidator.require_guardrail("PromptInjectionGuardrail")
        v({"guardrails": {"PromptInjectionGuardrail": True}}, object())

    def test_rejects_config_with_required_guardrail_disabled(self) -> None:
        v = RemoteConfigValidator.require_guardrail("PromptInjectionGuardrail")
        with pytest.raises(ConfigValidationError) as exc_info:
            v({"guardrails": {"PromptInjectionGuardrail": False}}, object())
        assert exc_info.value.field == "guardrails"

    def test_rejects_config_with_guardrails_section_missing_required_name(self) -> None:
        v = RemoteConfigValidator.require_guardrail("PromptInjectionGuardrail")
        with pytest.raises(ConfigValidationError):
            # Guardrails key present but required guardrail missing
            v({"guardrails": {"OtherGuardrail": True}}, object())

    def test_accepts_config_not_touching_guardrails(self) -> None:
        v = RemoteConfigValidator.require_guardrail("PromptInjectionGuardrail")
        # No "guardrails" key → validator doesn't care
        v({"model": "gpt-4o"}, object())

    def test_accepts_config_with_guardrails_none_value(self) -> None:
        v = RemoteConfigValidator.require_guardrail("PromptInjectionGuardrail")
        # No "guardrails" key → passthrough
        v({}, object())


class TestMultipleValidators:
    """Tests that all validators must pass."""

    def test_all_validators_pass_for_valid_config(self) -> None:
        validators = [
            RemoteConfigValidator.max_budget(10.00),
            RemoteConfigValidator.require_guardrail("GuardA"),
        ]
        config = {"budget": 5.0, "guardrails": {"GuardA": True}}
        for v in validators:
            v(config, object())

    def test_first_failing_validator_raises(self) -> None:
        validators = [
            RemoteConfigValidator.max_budget(10.00),
            RemoteConfigValidator.require_guardrail("GuardA"),
        ]
        config = {"budget": 99.0, "guardrails": {"GuardA": True}}
        with pytest.raises(ConfigValidationError):
            for v in validators:
                v(config, object())

    def test_second_failing_validator_raises(self) -> None:
        validators = [
            RemoteConfigValidator.max_budget(10.00),
            RemoteConfigValidator.require_guardrail("GuardA"),
        ]
        # Budget is fine but guardrail is disabled
        config = {"budget": 5.0, "guardrails": {"GuardA": False}}
        with pytest.raises(ConfigValidationError):
            for v in validators:
                v(config, object())
