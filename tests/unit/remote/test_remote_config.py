"""Tests for RemoteConfig — control plane core (versioning, apply, rollback, history)."""

from __future__ import annotations

import pytest

from syrin.enums import RemoteField
from syrin.remote_config import (
    ConfigRejectedError,
    ConfigValidationError,
    ConfigVersion,
    RemoteConfig,
    RemoteConfigValidator,
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_remote(**kwargs: object) -> RemoteConfig:
    """Return a minimal RemoteConfig for testing."""
    defaults: dict[str, object] = {
        "url": "https://nexus.example.com/config",
        "agent_id": "test-agent",
    }
    defaults.update(kwargs)
    return RemoteConfig(**defaults)  # type: ignore[arg-type]


# ──────────────────────────────────────────────────────────────────────────────
# is_field_allowed
# ──────────────────────────────────────────────────────────────────────────────


class TestIsFieldAllowed:
    """Tests for RemoteConfig.is_field_allowed()."""

    def test_no_lists_allows_all_fields(self) -> None:
        remote = _make_remote()
        assert remote.is_field_allowed(RemoteField.MODEL) is True
        assert remote.is_field_allowed(RemoteField.BUDGET) is True
        assert remote.is_field_allowed(RemoteField.IDENTITY) is True

    def test_allow_list_permits_only_listed_fields(self) -> None:
        remote = _make_remote(allow=[RemoteField.MODEL, RemoteField.BUDGET])
        assert remote.is_field_allowed(RemoteField.MODEL) is True
        assert remote.is_field_allowed(RemoteField.BUDGET) is True
        assert remote.is_field_allowed(RemoteField.GUARDRAILS) is False
        assert remote.is_field_allowed(RemoteField.IDENTITY) is False

    def test_deny_list_blocks_listed_fields(self) -> None:
        remote = _make_remote(deny=[RemoteField.IDENTITY, RemoteField.AUDIT_BACKEND])
        assert remote.is_field_allowed(RemoteField.MODEL) is True
        assert remote.is_field_allowed(RemoteField.IDENTITY) is False
        assert remote.is_field_allowed(RemoteField.AUDIT_BACKEND) is False

    def test_deny_list_takes_priority_over_allow_list(self) -> None:
        """A field in both allow and deny should be denied."""
        remote = _make_remote(
            allow=[RemoteField.MODEL, RemoteField.IDENTITY],
            deny=[RemoteField.IDENTITY],
        )
        # MODEL is in allow and not in deny → allowed
        assert remote.is_field_allowed(RemoteField.MODEL) is True
        # IDENTITY is in both → deny wins
        assert remote.is_field_allowed(RemoteField.IDENTITY) is False

    def test_allow_and_deny_do_not_interfere_with_unlisted(self) -> None:
        remote = _make_remote(allow=[RemoteField.MODEL], deny=[RemoteField.IDENTITY])
        # BUDGET is not in allow → not permitted
        assert remote.is_field_allowed(RemoteField.BUDGET) is False


# ──────────────────────────────────────────────────────────────────────────────
# apply
# ──────────────────────────────────────────────────────────────────────────────


class TestApply:
    """Tests for RemoteConfig.apply()."""

    @pytest.mark.asyncio
    async def test_apply_allowed_field_returns_config_version(self) -> None:
        remote = _make_remote(allow=[RemoteField.MODEL])
        version = await remote.apply({"model": "gpt-4o"}, changed_by="admin")

        assert isinstance(version, ConfigVersion)
        assert version.version == 1
        assert version.applied_by == "admin"
        assert "model" in version.fields_changed
        assert version.new_values == {"model": "gpt-4o"}
        assert isinstance(version.rollback_token, str)
        assert len(version.rollback_token) == 36  # UUID4 length

    @pytest.mark.asyncio
    async def test_apply_no_restrictions_accepts_any_field(self) -> None:
        remote = _make_remote()
        version = await remote.apply({"budget": 5.0})
        assert version.version == 1
        assert "budget" in version.fields_changed

    @pytest.mark.asyncio
    async def test_apply_denied_field_raises_config_rejected_error(self) -> None:
        remote = _make_remote(deny=[RemoteField.IDENTITY])
        with pytest.raises(ConfigRejectedError) as exc_info:
            await remote.apply({"identity": "new-id"})
        assert exc_info.value.field == "identity"

    @pytest.mark.asyncio
    async def test_apply_with_failing_validator_raises_config_validation_error(self) -> None:
        validator = RemoteConfigValidator.max_budget(10.0)
        remote = _make_remote(validators=[validator])
        with pytest.raises(ConfigValidationError):
            await remote.apply({"budget": 99.0})

    @pytest.mark.asyncio
    async def test_apply_emits_config_rejected_hook_on_denied_field(self) -> None:
        hooked: list[object] = []

        remote = _make_remote(deny=[RemoteField.IDENTITY])
        remote._fire_fn = lambda hook, _data: hooked.append(hook)  # type: ignore[method-assign]

        with pytest.raises(ConfigRejectedError):
            await remote.apply({"identity": "x"})

        from syrin.enums import Hook

        assert Hook.CONFIG_REJECTED in hooked

    @pytest.mark.asyncio
    async def test_apply_emits_config_applied_hook_on_success(self) -> None:
        hooked: list[object] = []

        remote = _make_remote()
        remote._fire_fn = lambda hook, _data: hooked.append(hook)  # type: ignore[method-assign]

        await remote.apply({"model": "gpt-4o"})

        from syrin.enums import Hook

        assert Hook.CONFIG_APPLIED in hooked

    @pytest.mark.asyncio
    async def test_apply_emits_config_rejected_hook_on_validation_failure(self) -> None:
        hooked: list[object] = []
        validator = RemoteConfigValidator.max_budget(10.0)
        remote = _make_remote(validators=[validator])
        remote._fire_fn = lambda hook, _data: hooked.append(hook)  # type: ignore[method-assign]

        with pytest.raises(ConfigValidationError):
            await remote.apply({"budget": 99.0})

        from syrin.enums import Hook

        assert Hook.CONFIG_REJECTED in hooked

    @pytest.mark.asyncio
    async def test_apply_creates_versioned_history_entries(self) -> None:
        remote = _make_remote()
        await remote.apply({"model": "gpt-4o-mini"})
        await remote.apply({"budget": 2.0})
        await remote.apply({"model": "gpt-4o"})

        assert len(remote.config_history) == 3
        assert remote.config_history[0].version == 1
        assert remote.config_history[1].version == 2
        assert remote.config_history[2].version == 3

    @pytest.mark.asyncio
    async def test_apply_stores_previous_values_in_version(self) -> None:
        remote = _make_remote()
        await remote.apply({"model": "gpt-4o-mini"})
        v2 = await remote.apply({"model": "gpt-4o"})

        assert v2.previous_values == {"model": "gpt-4o-mini"}
        assert v2.new_values == {"model": "gpt-4o"}

    @pytest.mark.asyncio
    async def test_apply_version_numbers_increment(self) -> None:
        remote = _make_remote()
        v1 = await remote.apply({"model": "a"})
        v2 = await remote.apply({"model": "b"})
        assert v1.version == 1
        assert v2.version == 2


# ──────────────────────────────────────────────────────────────────────────────
# rollback
# ──────────────────────────────────────────────────────────────────────────────


class TestRollback:
    """Tests for RemoteConfig.rollback()."""

    @pytest.mark.asyncio
    async def test_rollback_none_reverts_to_previous_version(self) -> None:
        remote = _make_remote()
        await remote.apply({"model": "gpt-4o-mini"})
        await remote.apply({"model": "gpt-4o"})

        rollback_version = await remote.rollback(None)

        assert isinstance(rollback_version, ConfigVersion)
        assert remote._current_values.get("model") == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_rollback_specific_version_reverts_to_that_version(self) -> None:
        remote = _make_remote()
        await remote.apply({"model": "v1"})
        await remote.apply({"model": "v2"})
        await remote.apply({"model": "v3"})

        await remote.rollback(version=1)

        assert remote._current_values.get("model") == "v1"

    @pytest.mark.asyncio
    async def test_rollback_creates_new_history_entry(self) -> None:
        remote = _make_remote()
        await remote.apply({"model": "a"})
        await remote.apply({"model": "b"})

        history_before = len(remote.config_history)
        await remote.rollback(None)

        assert len(remote.config_history) == history_before + 1

    @pytest.mark.asyncio
    async def test_rollback_no_history_raises_value_error(self) -> None:
        remote = _make_remote()
        with pytest.raises(ValueError):
            await remote.rollback(None)

    @pytest.mark.asyncio
    async def test_rollback_unknown_version_raises_value_error(self) -> None:
        remote = _make_remote()
        await remote.apply({"model": "a"})
        with pytest.raises(ValueError):
            await remote.rollback(version=999)

    @pytest.mark.asyncio
    async def test_rollback_emits_config_rollback_hook(self) -> None:
        hooked: list[object] = []
        remote = _make_remote()
        remote._fire_fn = lambda hook, _data: hooked.append(hook)  # type: ignore[method-assign]

        await remote.apply({"model": "a"})
        await remote.apply({"model": "b"})
        await remote.rollback(None)

        from syrin.enums import Hook

        assert Hook.CONFIG_ROLLBACK in hooked


# ──────────────────────────────────────────────────────────────────────────────
# get_history
# ──────────────────────────────────────────────────────────────────────────────


class TestGetHistory:
    """Tests for RemoteConfig.get_history()."""

    @pytest.mark.asyncio
    async def test_get_history_returns_last_n_entries(self) -> None:
        remote = _make_remote()
        for i in range(5):
            await remote.apply({f"field{i}": i})

        history = await remote.get_history(last_n=3)
        assert len(history) == 3
        assert history[-1].version == 5  # Most recent last
        assert history[0].version == 3

    @pytest.mark.asyncio
    async def test_get_history_returns_all_when_last_n_exceeds_history(self) -> None:
        remote = _make_remote()
        await remote.apply({"model": "a"})

        history = await remote.get_history(last_n=100)
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_get_history_empty_before_any_apply(self) -> None:
        remote = _make_remote()
        history = await remote.get_history()
        assert history == []


# ──────────────────────────────────────────────────────────────────────────────
# ConfigVersion fields
# ──────────────────────────────────────────────────────────────────────────────


class TestConfigVersionFields:
    """Tests that ConfigVersion has all required fields with correct types."""

    @pytest.mark.asyncio
    async def test_config_version_has_all_required_fields(self) -> None:
        from datetime import datetime

        remote = _make_remote()
        version = await remote.apply({"model": "gpt-4o"}, changed_by="user@test.com")

        assert isinstance(version.version, int)
        assert isinstance(version.applied_at, datetime)
        assert isinstance(version.applied_by, str)
        assert isinstance(version.fields_changed, list)
        assert isinstance(version.previous_values, dict)
        assert isinstance(version.new_values, dict)
        assert isinstance(version.rollback_token, str)

    @pytest.mark.asyncio
    async def test_config_version_rollback_token_is_uuid4_format(self) -> None:
        import re

        remote = _make_remote()
        version = await remote.apply({"model": "gpt-4o"})
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        )
        assert uuid_pattern.match(version.rollback_token)
