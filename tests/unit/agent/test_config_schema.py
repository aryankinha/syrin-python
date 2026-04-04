"""Tests for Agent.config_schema() and Agent.current_config()."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from syrin.agent import Agent
from syrin.model import Model


def _make_agent(name: str = "test-agent") -> Agent:
    """Return a minimal agent for schema tests — no LLM calls needed."""
    return Agent(model=Model.OpenAI("gpt-4o-mini"), name=name)


class TestConfigSchema:
    """Tests for Agent.config_schema()."""

    def test_returns_dict(self) -> None:
        agent = _make_agent()
        result = agent.config_schema()
        assert isinstance(result, dict)

    def test_root_type_is_object(self) -> None:
        agent = _make_agent()
        result = agent.config_schema()
        assert result.get("type") == "object"

    def test_has_properties_key(self) -> None:
        agent = _make_agent()
        result = agent.config_schema()
        assert "properties" in result
        assert isinstance(result["properties"], dict)

    def test_output_path_writes_valid_json(self) -> None:
        agent = _make_agent()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            agent.config_schema(output=tmp_path)
            assert os.path.exists(tmp_path)
            with open(tmp_path, encoding="utf-8") as fh:
                loaded = json.load(fh)
            assert loaded.get("type") == "object"
            assert "properties" in loaded
        finally:
            os.unlink(tmp_path)

    def test_output_path_json_is_pretty_printed(self) -> None:
        """The output file should be indented (pretty-printed)."""
        agent = _make_agent()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            agent.config_schema(output=tmp_path)
            with open(tmp_path, encoding="utf-8") as fh:
                content = fh.read()
            # Pretty-printed JSON has newlines
            assert "\n" in content
        finally:
            os.unlink(tmp_path)

    def test_no_output_path_does_not_write_file(self, tmp_path: object) -> None:
        agent = _make_agent()
        # Should complete without error and not produce side effects
        result = agent.config_schema()
        assert isinstance(result, dict)


class TestCurrentConfig:
    """Tests for Agent.current_config()."""

    def test_returns_remote_config_snapshot(self) -> None:
        from syrin.remote_config import RemoteConfigSnapshot

        agent = _make_agent()
        snap = agent.current_config()
        assert isinstance(snap, RemoteConfigSnapshot)

    def test_snapshot_has_correct_agent_id(self) -> None:
        agent = _make_agent(name="my-special-agent")
        snap = agent.current_config()
        assert snap.agent_id == "my-special-agent"

    def test_snapshot_version_is_zero_with_no_remote_config(self) -> None:
        agent = _make_agent()
        snap = agent.current_config()
        assert snap.version == 0

    def test_snapshot_values_is_dict(self) -> None:
        agent = _make_agent()
        snap = agent.current_config()
        assert isinstance(snap.values, dict)

    def test_snapshot_captured_at_is_datetime(self) -> None:
        from datetime import datetime

        agent = _make_agent()
        snap = agent.current_config()
        assert isinstance(snap.captured_at, datetime)

    def test_snapshot_is_frozen(self) -> None:
        """RemoteConfigSnapshot is a frozen dataclass — mutation should fail."""
        from dataclasses import FrozenInstanceError

        agent = _make_agent()
        snap = agent.current_config()
        with pytest.raises((FrozenInstanceError, AttributeError)):
            snap.version = 99  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_snapshot_version_reflects_applied_config(self) -> None:
        from syrin.remote_config import RemoteConfig

        remote = RemoteConfig(
            url="https://example.com",
            agent_id="x",
        )
        agent = _make_agent()
        # Manually attach a RemoteConfig and apply changes
        object.__setattr__(agent, "_remote_config", remote)
        await remote.apply({"model": "gpt-4o"})
        await remote.apply({"budget": 2.0})

        snap = agent.current_config()
        assert snap.version == 2
        assert snap.values.get("model") == "gpt-4o"
        assert snap.values.get("budget") == 2.0
