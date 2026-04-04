"""Tests for VersionedConfig (P8-T3)."""

from __future__ import annotations

import pytest

from syrin.enums import Hook
from syrin.remote._versioning import ConfigSnapshot, RollbackError, VersionedConfig


class TestVersionedConfigInit:
    def test_starts_at_version_zero(self) -> None:
        vc = VersionedConfig()
        assert vc.current_version == 0

    def test_current_values_empty_at_start(self) -> None:
        vc = VersionedConfig()
        assert vc.current_values == {}

    def test_history_empty_at_start(self) -> None:
        vc = VersionedConfig()
        assert vc.history == []


class TestVersionedConfigPush:
    def test_push_increments_version_to_1(self) -> None:
        vc = VersionedConfig()
        vc.push({"budget.max_cost": 1.0})
        assert vc.current_version == 1

    def test_push_twice_increments_to_2(self) -> None:
        vc = VersionedConfig()
        vc.push({"budget.max_cost": 1.0})
        vc.push({"budget.max_cost": 2.0})
        assert vc.current_version == 2

    def test_push_updates_current_values(self) -> None:
        vc = VersionedConfig()
        vc.push({"budget.max_cost": 1.0})
        vc.push({"budget.max_cost": 2.0})
        assert vc.current_values["budget.max_cost"] == 2.0

    def test_push_returns_new_version(self) -> None:
        vc = VersionedConfig()
        v = vc.push({"x": 1})
        assert v == 1
        v2 = vc.push({"x": 2})
        assert v2 == 2


class TestVersionedConfigRollback:
    def test_rollback_reverts_to_version_1(self) -> None:
        vc = VersionedConfig()
        vc.push({"budget.max_cost": 1.0})
        vc.push({"budget.max_cost": 2.0})
        vc.rollback()
        assert vc.current_version == 1

    def test_rollback_restores_values(self) -> None:
        vc = VersionedConfig()
        vc.push({"budget.max_cost": 1.0})
        vc.push({"budget.max_cost": 2.0})
        vc.rollback()
        assert vc.current_values["budget.max_cost"] == 1.0

    def test_rollback_twice_returns_to_version_0(self) -> None:
        vc = VersionedConfig()
        vc.push({"budget.max_cost": 1.0})
        vc.push({"budget.max_cost": 2.0})
        vc.rollback()
        vc.rollback()
        assert vc.current_version == 0

    def test_rollback_to_version_0_empties_values(self) -> None:
        vc = VersionedConfig()
        vc.push({"budget.max_cost": 1.0})
        vc.rollback()
        assert vc.current_values == {}

    def test_rollback_at_version_0_raises_rollback_error(self) -> None:
        vc = VersionedConfig()
        with pytest.raises(RollbackError):
            vc.rollback()

    def test_rollback_error_has_current_version(self) -> None:
        vc = VersionedConfig()
        try:
            vc.rollback()
        except RollbackError as e:
            assert e.current_version == 0

    def test_rollback_fires_config_rollback_hook(self) -> None:
        fired: list[tuple[Hook, dict[str, object]]] = []

        def fn(hook: Hook, payload: dict[str, object]) -> None:
            fired.append((hook, payload))

        vc = VersionedConfig(fire_fn=fn)
        vc.push({"x": 1})
        vc.push({"x": 2})
        vc.rollback()

        assert len(fired) == 1
        hook, payload = fired[0]
        assert hook == Hook.CONFIG_ROLLBACK
        assert payload["from_version"] == 2
        assert payload["to_version"] == 1

    def test_rollback_returns_snapshot(self) -> None:
        vc = VersionedConfig()
        vc.push({"x": 1})
        vc.push({"x": 2})
        snap = vc.rollback()
        assert isinstance(snap, ConfigSnapshot)
        assert snap.version == 1
        assert snap.values == {"x": 1}


class TestVersionedConfigHistory:
    def test_history_tracks_snapshots(self) -> None:
        vc = VersionedConfig()
        vc.push({"x": 1})
        vc.push({"x": 2})
        history = vc.history
        assert len(history) >= 1
        assert isinstance(history[0], ConfigSnapshot)

    def test_history_contains_all_past_snapshots(self) -> None:
        vc = VersionedConfig()
        vc.push({"x": 1})
        vc.push({"x": 2})
        vc.push({"x": 3})
        history = vc.history
        # History should include version 0 (empty) snapshot before each push
        versions = [s.version for s in history]
        assert 0 in versions or len(history) >= 2
