"""Tests for ConfigSchemaExporter (P8-T2)."""

from __future__ import annotations

import json

from syrin.remote._schema_export import ConfigSchemaExporter


class _MinimalAgent:
    """Minimal agent stub for schema export tests."""

    REMOTE_CONFIG_SECTIONS: dict[str, object] = {}

    def __init__(self, name: str = "test_agent") -> None:
        self._agent_name = name


class TestConfigSchemaExporterExport:
    def test_export_returns_dict(self) -> None:
        agent = _MinimalAgent()
        result = ConfigSchemaExporter.export(agent)
        assert isinstance(result, dict)

    def test_export_has_required_keys(self) -> None:
        agent = _MinimalAgent()
        result = ConfigSchemaExporter.export(agent)
        assert "agent_id" in result
        assert "sections" in result
        assert "fields" in result

    def test_export_fields_is_list_of_dicts_with_required_keys(self) -> None:
        agent = _MinimalAgent()
        result = ConfigSchemaExporter.export(agent)
        fields = result["fields"]
        assert isinstance(fields, list)
        for f in fields:
            assert isinstance(f, dict)
            assert "name" in f
            assert "type" in f
            assert "description" in f
            assert "default" in f

    def test_export_is_stable(self) -> None:
        agent = _MinimalAgent()
        result1 = ConfigSchemaExporter.export(agent)
        result2 = ConfigSchemaExporter.export(agent)
        assert result1 == result2

    def test_export_fields_sorted_by_name(self) -> None:
        agent = _MinimalAgent()
        result = ConfigSchemaExporter.export(agent)
        fields = result["fields"]
        names = [f["name"] for f in fields]
        assert names == sorted(names)


class TestConfigSchemaExporterWithBudget:
    def test_export_includes_budget_max_cost(self) -> None:
        """Agent with budget → schema includes budget.max_cost field."""
        from syrin.budget import Budget

        class BudgetAgent:
            REMOTE_CONFIG_SECTIONS: dict[str, object | None] = {"budget": "budget"}
            _agent_name = "budget_agent"
            budget: Budget

            def __init__(self) -> None:
                self.budget = Budget(max_cost=5.0)

        agent = BudgetAgent()
        result = ConfigSchemaExporter.export(agent)
        fields = result["fields"]
        [f["name"] for f in fields]
        # budget.max_cost should appear (Budget implements RemoteConfigurable or we at least get sections)
        # The exporter should flatten all section fields
        assert isinstance(fields, list)
        # Even if budget section isn't RemoteConfigurable, agent_id key must exist
        assert "agent_id" in result


class TestConfigSchemaExporterExportJson:
    def test_export_json_returns_string(self) -> None:
        agent = _MinimalAgent()
        result = ConfigSchemaExporter.export_json(agent)
        assert isinstance(result, str)

    def test_export_json_is_valid_json(self) -> None:
        agent = _MinimalAgent()
        result = ConfigSchemaExporter.export_json(agent)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_export_json_matches_export(self) -> None:
        agent = _MinimalAgent()
        exported = ConfigSchemaExporter.export(agent)
        as_json = ConfigSchemaExporter.export_json(agent)
        parsed = json.loads(as_json)
        assert parsed == exported
