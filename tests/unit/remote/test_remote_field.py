"""Tests for RemoteField access control (P8-T1)."""

from __future__ import annotations

from syrin.enums import Hook
from syrin.remote._field import RemoteConfigAccess, RemoteField


class TestRemoteFieldEnum:
    def test_remote_field_is_strenum(self) -> None:
        from enum import StrEnum

        assert issubclass(RemoteField, StrEnum)

    def test_remote_field_has_required_values(self) -> None:
        assert RemoteField.MODEL == "model"
        assert RemoteField.BUDGET == "budget"
        assert RemoteField.MEMORY == "memory"
        assert RemoteField.SYSTEM_PROMPT == "system_prompt"
        assert RemoteField.GUARDRAILS == "guardrails"
        assert RemoteField.MAX_COST == "max_cost"
        assert RemoteField.CONTEXT == "context"

    def test_remote_field_model_matches_model_prefix(self) -> None:
        """RemoteField.MODEL should match paths starting with 'model.'."""
        path = "model.name"
        assert path.startswith(RemoteField.MODEL + ".")


class TestRemoteConfigAccessAllowList:
    def test_constructs_with_allow_list(self) -> None:
        access = RemoteConfigAccess(allow=[RemoteField.MODEL])
        assert access is not None

    def test_allow_model_permits_model_path(self) -> None:
        access = RemoteConfigAccess(allow=[RemoteField.MODEL])
        assert access.is_allowed("model.name") is True

    def test_allow_model_denies_budget_path(self) -> None:
        access = RemoteConfigAccess(allow=[RemoteField.MODEL])
        assert access.is_allowed("budget.max_cost") is False


class TestRemoteConfigAccessDenyList:
    def test_constructs_with_deny_list(self) -> None:
        access = RemoteConfigAccess(deny=[RemoteField.BUDGET])
        assert access is not None

    def test_deny_budget_denies_budget_path(self) -> None:
        access = RemoteConfigAccess(deny=[RemoteField.BUDGET])
        assert access.is_allowed("budget.max_cost") is False

    def test_deny_budget_permits_model_path(self) -> None:
        access = RemoteConfigAccess(deny=[RemoteField.BUDGET])
        assert access.is_allowed("model.name") is True


class TestRemoteConfigAccessDefault:
    def test_no_allow_deny_permits_all(self) -> None:
        access = RemoteConfigAccess()
        assert access.is_allowed("model.name") is True
        assert access.is_allowed("budget.max_cost") is True
        assert access.is_allowed("memory.top_k") is True


class TestRemoteConfigAccessCheckField:
    def test_check_field_fires_config_rejected_when_denied(self) -> None:
        fired: list[tuple[Hook, dict[str, object]]] = []

        def fn(hook: Hook, payload: dict[str, object]) -> None:
            fired.append((hook, payload))

        access = RemoteConfigAccess(allow=[RemoteField.MODEL])
        result = access.check_field(path="budget.max_cost", fire_fn=fn)
        assert result is False
        assert len(fired) == 1
        hook, payload = fired[0]
        assert hook == Hook.CONFIG_REJECTED
        assert payload["reason"] == "field_denied"
        assert payload["path"] == "budget.max_cost"

    def test_check_field_does_not_fire_when_allowed(self) -> None:
        fired: list[tuple[Hook, dict[str, object]]] = []

        def fn(hook: Hook, payload: dict[str, object]) -> None:
            fired.append((hook, payload))

        access = RemoteConfigAccess(allow=[RemoteField.MODEL])
        result = access.check_field(path="model.name", fire_fn=fn)
        assert result is True
        assert len(fired) == 0

    def test_check_field_without_fire_fn_returns_bool(self) -> None:
        access = RemoteConfigAccess(allow=[RemoteField.MODEL])
        assert access.check_field("model.name") is True
        assert access.check_field("budget.max_cost") is False


class TestRemoteConfigAccessIsolation:
    def test_two_instances_are_independent(self) -> None:
        access1 = RemoteConfigAccess(allow=[RemoteField.MODEL])
        access2 = RemoteConfigAccess(allow=[RemoteField.BUDGET])
        assert access1.is_allowed("model.name") is True
        assert access1.is_allowed("budget.max_cost") is False
        assert access2.is_allowed("model.name") is False
        assert access2.is_allowed("budget.max_cost") is True
