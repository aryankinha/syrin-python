"""Tests for StateExporter — exit criteria: export() returns JSON with all required sections."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from syrin.debug._state_export import ExportSnapshot, StateExporter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snapshot() -> ExportSnapshot:
    return StateExporter.build_snapshot(
        agent_contexts={
            "agent-1": {"status": "RUNNING", "current_task": "summarise"},
            "agent-2": {"status": "IDLE", "current_task": None},
        },
        memory=[
            {"id": "m1", "type": "episodic", "content": "User prefers brevity"},
            {"id": "m2", "type": "semantic", "content": "Paris is in France"},
        ],
        costs={"agent-1": 0.04, "agent-2": 0.01},
        a2a_log=[
            {"from": "agent-1", "to": "agent-2", "msg": "handoff: summarise report"},
            {"from": "agent-2", "to": "agent-1", "msg": "done"},
        ],
        metadata={"version": "0.11.0"},
    )


# ---------------------------------------------------------------------------
# ExportSnapshot.to_dict() contains required sections
# ---------------------------------------------------------------------------


def test_to_dict_has_all_required_sections() -> None:
    """ExportSnapshot.to_dict() includes agent_contexts, memory, costs, a2a_log."""
    snap = _make_snapshot()
    d = snap.to_dict()
    assert "agent_contexts" in d
    assert "memory" in d
    assert "costs" in d
    assert "a2a_log" in d


def test_to_dict_agent_contexts_preserved() -> None:
    """agent_contexts entries are preserved exactly."""
    snap = _make_snapshot()
    d = snap.to_dict()
    assert d["agent_contexts"]["agent-1"]["status"] == "RUNNING"
    assert d["agent_contexts"]["agent-2"]["current_task"] is None


def test_to_dict_memory_entries() -> None:
    """memory list contains correct entries."""
    snap = _make_snapshot()
    d = snap.to_dict()
    ids = [e["id"] for e in d["memory"]]
    assert "m1" in ids
    assert "m2" in ids


def test_to_dict_costs() -> None:
    """costs dict contains correct per-agent costs."""
    snap = _make_snapshot()
    d = snap.to_dict()
    assert d["costs"]["agent-1"] == pytest.approx(0.04)
    assert d["costs"]["agent-2"] == pytest.approx(0.01)


def test_to_dict_a2a_log_order_preserved() -> None:
    """a2a_log preserves insertion order."""
    snap = _make_snapshot()
    d = snap.to_dict()
    assert d["a2a_log"][0]["from"] == "agent-1"
    assert d["a2a_log"][1]["from"] == "agent-2"


# ---------------------------------------------------------------------------
# StateExporter.export_snapshot() writes valid JSON
# ---------------------------------------------------------------------------


def test_export_snapshot_writes_valid_json() -> None:
    """export_snapshot() writes a valid JSON file to disk."""
    snap = _make_snapshot()
    exporter = StateExporter()
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        exporter.export_snapshot(snap, path)
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert "agent_contexts" in data
        assert "memory" in data
        assert "costs" in data
        assert "a2a_log" in data
    finally:
        os.unlink(path)


def test_export_snapshot_returns_json_string() -> None:
    """export_snapshot() returns the JSON string."""
    snap = _make_snapshot()
    exporter = StateExporter()
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        result = exporter.export_snapshot(snap, path)
        parsed = json.loads(result)
        assert parsed["costs"]["agent-1"] == pytest.approx(0.04)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# StateExporter.export() low-level path
# ---------------------------------------------------------------------------


def test_export_low_level_accepts_arbitrary_dict() -> None:
    """export() writes any state dict and returns JSON string."""
    exporter = StateExporter()
    state = {
        "agent_contexts": {"a": {"x": 1}},
        "memory": [],
        "costs": {"a": 0.0},
        "a2a_log": [],
    }
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        result = exporter.export(state, path)
        parsed = json.loads(result)
        assert parsed["agent_contexts"]["a"]["x"] == 1
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# build_snapshot() with empty inputs
# ---------------------------------------------------------------------------


def test_build_snapshot_empty_defaults() -> None:
    """build_snapshot() with no args produces empty-but-valid snapshot."""
    snap = StateExporter.build_snapshot()
    d = snap.to_dict()
    assert d["agent_contexts"] == {}
    assert d["memory"] == []
    assert d["costs"] == {}
    assert d["a2a_log"] == []
