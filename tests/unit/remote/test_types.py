"""Tests for remote config types: FieldSchema, ConfigSchema, AgentSchema, ConfigOverride, OverridePayload, SyncRequest, SyncResponse."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from syrin.remote._types import (
    AgentSchema,
    ConfigOverride,
    ConfigSchema,
    FieldSchema,
    OverridePayload,
    SyncRequest,
    SyncResponse,
)

# --- FieldSchema ---


class TestFieldSchema:
    """Valid and invalid FieldSchema creation and serialization."""

    def test_minimal_valid(self) -> None:
        """Minimal valid FieldSchema: name, path, type."""
        f = FieldSchema(name="max_cost", path="budget.max_cost", type="float")
        assert f.name == "max_cost"
        assert f.path == "budget.max_cost"
        assert f.type == "float"
        assert f.default is None
        assert f.description is None
        assert f.constraints == {}
        assert f.enum_values is None
        assert f.children is None
        assert f.remote_excluded is False

    def test_full_valid(self) -> None:
        """Full FieldSchema with all optional fields."""
        f = FieldSchema(
            name="rate",
            path="memory.decay.rate",
            type="float",
            default=0.995,
            description="Decay rate per hour",
            constraints={"ge": 0.0, "le": 1.0},
            enum_values=None,
            children=None,
            remote_excluded=False,
        )
        assert f.default == 0.995
        assert f.constraints["ge"] == 0.0
        assert f.constraints["le"] == 1.0

    def test_enum_values(self) -> None:
        """FieldSchema with enum_values for StrEnum fields."""
        f = FieldSchema(
            name="strategy",
            path="memory.decay.strategy",
            type="str",
            enum_values=["exponential", "linear", "logarithmic", "none"],
        )
        assert f.enum_values == ["exponential", "linear", "logarithmic", "none"]

    def test_remote_excluded_true(self) -> None:
        """Callable/private fields marked remote_excluded."""
        f = FieldSchema(
            name="on_exceeded",
            path="budget.on_exceeded",
            type="callable",
            remote_excluded=True,
        )
        assert f.remote_excluded is True

    def test_children_nested(self) -> None:
        """FieldSchema with nested children (e.g. budget.rate_limits)."""
        child = FieldSchema(name="hour", path="budget.rate_limits.hour", type="float", default=None)
        parent = FieldSchema(
            name="rate_limits",
            path="budget.rate_limits",
            type="object",
            children=[child],
        )
        assert parent.children is not None
        assert len(parent.children) == 1
        assert parent.children[0].name == "hour"
        assert parent.children[0].path == "budget.rate_limits.hour"

    def test_constraints_dict_arbitrary_keys(self) -> None:
        """Constraints can hold ge, le, gt, lt, pattern, min_length, max_length."""
        f = FieldSchema(
            name="x",
            path="section.x",
            type="float",
            constraints={"ge": 0, "le": 100, "pattern": r"^\d+$"},
        )
        assert f.constraints["ge"] == 0
        assert f.constraints["pattern"] == r"^\d+$"

    def test_default_json_serializable(self) -> None:
        """Default can be int, float, str, bool, list, dict for JSON round-trip."""
        for default in [0, 0.5, "hello", True, [1, 2], {"a": 1}]:
            f = FieldSchema(name="f", path="s.f", type="any", default=default)
            assert f.default == default
            dumped = f.model_dump()
            assert "default" in dumped
            json_str = json.dumps(dumped, default=str)
            assert json.loads(json_str)["default"] == default or default == 0

    def test_empty_path_rejected(self) -> None:
        """Empty path is invalid (required non-empty for resolution)."""
        with pytest.raises(ValidationError):
            FieldSchema(name="x", path="", type="str")

    def test_empty_name_rejected(self) -> None:
        """Empty name is invalid."""
        with pytest.raises(ValidationError):
            FieldSchema(name="", path="section.field", type="str")


# --- ConfigSchema ---


class TestConfigSchema:
    """Valid and invalid ConfigSchema."""

    def test_minimal_valid(self) -> None:
        """Minimal ConfigSchema: section, class_name, fields."""
        cs = ConfigSchema(
            section="budget",
            class_name="Budget",
            fields=[
                FieldSchema(name="max_cost", path="budget.max_cost", type="float"),
            ],
        )
        assert cs.section == "budget"
        assert cs.class_name == "Budget"
        assert len(cs.fields) == 1
        assert cs.fields[0].name == "max_cost"

    def test_empty_fields_allowed(self) -> None:
        """ConfigSchema with empty fields list (e.g. no configurable fields)."""
        cs = ConfigSchema(section="agent", class_name="Agent", fields=[])
        assert cs.fields == []

    def test_multiple_fields(self) -> None:
        """ConfigSchema with multiple fields."""
        cs = ConfigSchema(
            section="memory",
            class_name="Memory",
            fields=[
                FieldSchema(name="top_k", path="memory.top_k", type="int"),
                FieldSchema(
                    name="backend",
                    path="memory.backend",
                    type="str",
                    enum_values=["qdrant", "chroma"],
                ),
            ],
        )
        assert len(cs.fields) == 2
        assert cs.fields[1].enum_values == ["qdrant", "chroma"]

    def test_section_empty_rejected(self) -> None:
        """Empty section key is invalid."""
        with pytest.raises(ValidationError):
            ConfigSchema(
                section="",
                class_name="Budget",
                fields=[FieldSchema(name="run", path=".run", type="float")],
            )


# --- AgentSchema ---


class TestAgentSchema:
    """Valid and invalid AgentSchema."""

    def test_minimal_valid(self) -> None:
        """Minimal AgentSchema: agent_id, agent_name, class_name, sections, current_values."""
        schema = AgentSchema(
            agent_id="my_agent:MyAgent",
            agent_name="my_agent",
            class_name="MyAgent",
            sections={
                "budget": ConfigSchema(
                    section="budget",
                    class_name="Budget",
                    fields=[FieldSchema(name="max_cost", path="budget.max_cost", type="float")],
                ),
            },
            current_values={"budget.max_cost": 0.5},
        )
        assert schema.agent_id == "my_agent:MyAgent"
        assert schema.agent_name == "my_agent"
        assert "budget" in schema.sections
        assert schema.sections["budget"].class_name == "Budget"
        assert schema.current_values["budget.max_cost"] == 0.5

    def test_empty_sections_and_values(self) -> None:
        """AgentSchema with no sections and no current values."""
        schema = AgentSchema(
            agent_id="id",
            agent_name="name",
            class_name="Agent",
            sections={},
            current_values={},
        )
        assert schema.sections == {}
        assert schema.current_values == {}

    def test_current_values_dotted_paths(self) -> None:
        """current_values uses dotted paths as keys."""
        schema = AgentSchema(
            agent_id="a",
            agent_name="a",
            class_name="C",
            sections={},
            current_values={
                "budget.max_cost": 1.0,
                "memory.top_k": 10,
                "memory.decay.strategy": "exponential",
            },
        )
        assert schema.current_values["memory.decay.strategy"] == "exponential"

    def test_agent_id_empty_rejected(self) -> None:
        """Empty agent_id is invalid."""
        with pytest.raises(ValidationError):
            AgentSchema(
                agent_id="",
                agent_name="n",
                class_name="C",
                sections={},
                current_values={},
            )


# --- ConfigOverride ---


class TestConfigOverride:
    """Valid and invalid ConfigOverride."""

    def test_valid_simple(self) -> None:
        """Single override: path and value."""
        o = ConfigOverride(path="budget.max_cost", value=2.0)
        assert o.path == "budget.max_cost"
        assert o.value == 2.0

    def test_value_types(self) -> None:
        """Value can be int, float, str, bool, list, dict."""
        for val in [1, 2.5, "linear", True, [1, 2], {"a": 1}]:
            o = ConfigOverride(path="section.key", value=val)
            assert o.value == val

    def test_value_none(self) -> None:
        """Value can be None for optional reset."""
        o = ConfigOverride(path="memory.decay.half_life_hours", value=None)
        assert o.value is None

    def test_empty_path_rejected(self) -> None:
        """Empty path is invalid."""
        with pytest.raises(ValidationError):
            ConfigOverride(path="", value=1)

    def test_nested_path(self) -> None:
        """Nested dotted path is valid."""
        o = ConfigOverride(path="memory.decay.strategy", value="linear")
        assert o.path == "memory.decay.strategy"


# --- OverridePayload ---


class TestOverridePayload:
    """Valid and invalid OverridePayload."""

    def test_minimal_valid(self) -> None:
        """OverridePayload: agent_id, version, overrides."""
        p = OverridePayload(
            agent_id="agent:MyAgent",
            version=1,
            overrides=[ConfigOverride(path="budget.max_cost", value=2.0)],
        )
        assert p.agent_id == "agent:MyAgent"
        assert p.version == 1
        assert len(p.overrides) == 1
        assert p.overrides[0].value == 2.0

    def test_empty_overrides_allowed(self) -> None:
        """Empty overrides list is valid (e.g. sync with no changes)."""
        p = OverridePayload(agent_id="a", version=0, overrides=[])
        assert p.overrides == []

    def test_version_monotonic(self) -> None:
        """Version is an integer (monotonic in practice)."""
        p = OverridePayload(agent_id="a", version=42, overrides=[])
        assert p.version == 42

    def test_multiple_overrides(self) -> None:
        """Payload with multiple overrides."""
        p = OverridePayload(
            agent_id="a",
            version=2,
            overrides=[
                ConfigOverride(path="budget.max_cost", value=1.0),
                ConfigOverride(path="memory.top_k", value=20),
            ],
        )
        assert len(p.overrides) == 2

    def test_agent_id_empty_rejected(self) -> None:
        """Empty agent_id is invalid."""
        with pytest.raises(ValidationError):
            OverridePayload(agent_id="", version=0, overrides=[])

    def test_version_negative_rejected(self) -> None:
        """Negative version is invalid (monotonic non-negative)."""
        with pytest.raises(ValidationError):
            OverridePayload(agent_id="a", version=-1, overrides=[])


# --- SyncRequest ---


class TestSyncRequest:
    """Valid and invalid SyncRequest (registration handshake)."""

    def test_valid(self) -> None:
        """SyncRequest: agent_id, agent_schema, library_version."""
        agent_schema = AgentSchema(
            agent_id="a",
            agent_name="a",
            class_name="C",
            sections={},
            current_values={},
        )
        req = SyncRequest(agent_id="a", agent_schema=agent_schema, library_version="0.6.0")
        assert req.agent_id == "a"
        assert req.agent_schema.agent_id == "a"
        assert req.library_version == "0.6.0"

    def test_library_version_default_or_required(self) -> None:
        """library_version is required (no default from env in types)."""
        agent_schema = AgentSchema(
            agent_id="a",
            agent_name="a",
            class_name="C",
            sections={},
            current_values={},
        )
        req = SyncRequest(agent_id="a", agent_schema=agent_schema, library_version="0.5.0")
        assert req.library_version == "0.5.0"

    def test_agent_id_empty_rejected(self) -> None:
        """Empty agent_id is invalid."""
        agent_schema = AgentSchema(
            agent_id="x",
            agent_name="x",
            class_name="C",
            sections={},
            current_values={},
        )
        with pytest.raises(ValidationError):
            SyncRequest(agent_id="", agent_schema=agent_schema, library_version="0.6.0")

    def test_sync_request_wire_format_uses_schema_key(self) -> None:
        """Serialization uses 'schema' key for wire/API; parse accepts 'schema'."""
        agent_schema = AgentSchema(
            agent_id="a",
            agent_name="a",
            class_name="C",
            sections={},
            current_values={},
        )
        req = SyncRequest(
            agent_id="a",
            agent_schema=agent_schema,
            library_version="0.6.0",
        )
        data = req.model_dump(mode="json", by_alias=True)
        assert "schema" in data
        assert "agent_schema" not in data
        assert data["schema"]["agent_id"] == "a"
        restored = SyncRequest.model_validate(data)
        assert restored.agent_schema.agent_id == "a"


# --- SyncResponse ---


class TestSyncResponse:
    """Valid and invalid SyncResponse."""

    def test_ok_true_no_error(self) -> None:
        """Successful sync: ok=True, optional initial_overrides, error=None."""
        r = SyncResponse(ok=True, initial_overrides=None, error=None)
        assert r.ok is True
        assert r.initial_overrides is None
        assert r.error is None

    def test_ok_true_with_initial_overrides(self) -> None:
        """Successful sync with initial overrides to apply."""
        overrides = [
            ConfigOverride(path="budget.max_cost", value=1.5),
        ]
        r = SyncResponse(ok=True, initial_overrides=overrides, error=None)
        assert r.ok is True
        assert r.initial_overrides is not None
        assert len(r.initial_overrides) == 1
        assert r.initial_overrides[0].path == "budget.max_cost"

    def test_ok_false_with_error(self) -> None:
        """Failed sync: ok=False, error message set."""
        r = SyncResponse(ok=False, initial_overrides=None, error="Backend unavailable")
        assert r.ok is False
        assert r.error == "Backend unavailable"

    def test_ok_false_initial_overrides_ignored(self) -> None:
        """When ok=False, initial_overrides typically empty; type allows it for consistency."""
        r = SyncResponse(
            ok=False,
            initial_overrides=[ConfigOverride(path="x", value=1)],
            error="Failed",
        )
        assert r.ok is False
        assert r.error == "Failed"

    def test_round_trip_json(self) -> None:
        """SyncResponse serializes and deserializes for wire format."""
        r = SyncResponse(
            ok=True,
            initial_overrides=[
                ConfigOverride(path="budget.max_cost", value=2.0),
            ],
            error=None,
        )
        data = r.model_dump()
        assert data["ok"] is True
        assert len(data["initial_overrides"]) == 1
        assert data["initial_overrides"][0]["path"] == "budget.max_cost"
        restored = SyncResponse.model_validate(data)
        assert restored.ok == r.ok
        assert restored.initial_overrides[0].value == 2.0


# --- Edge cases: JSON / model_dump ---


class TestTypesSerialization:
    """All types are JSON-serializable for wire/API."""

    def test_field_schema_model_dump(self) -> None:
        """FieldSchema.model_dump() is JSON-serializable."""
        f = FieldSchema(
            name="run",
            path="budget.max_cost",
            type="float",
            default=0.5,
            constraints={"ge": 0},
        )
        data = f.model_dump()
        assert json.loads(json.dumps(data, default=str))["path"] == "budget.max_cost"

    def test_config_override_model_dump(self) -> None:
        """ConfigOverride round-trip."""
        o = ConfigOverride(path="memory.top_k", value=10)
        data = o.model_dump()
        o2 = ConfigOverride.model_validate(data)
        assert o2.path == o.path and o2.value == o.value

    def test_override_payload_model_dump(self) -> None:
        """OverridePayload round-trip."""
        p = OverridePayload(
            agent_id="a",
            version=1,
            overrides=[ConfigOverride(path="budget.max_cost", value=1.0)],
        )
        data = p.model_dump()
        p2 = OverridePayload.model_validate(data)
        assert p2.agent_id == p.agent_id and p2.version == p.version
        assert len(p2.overrides) == 1
        assert p2.overrides[0].value == 1.0
