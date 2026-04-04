"""StateExporter — full JSON snapshot of debugger state on 'e' keypress."""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class ExportSnapshot:
    """Structured snapshot of a Pry debug session.

    Attributes:
        agent_contexts: Per-agent state dicts keyed by agent_id.
        memory: Memory entries captured during the session.
        costs: Per-agent cost summaries keyed by agent_id.
        a2a_log: Ordered list of agent-to-agent message records.
        metadata: Optional session metadata (e.g. timestamp, syrin version).
    """

    agent_contexts: dict[str, dict[str, object]] = field(default_factory=dict)
    memory: list[dict[str, object]] = field(default_factory=list)
    costs: dict[str, float] = field(default_factory=dict)
    a2a_log: list[dict[str, object]] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict for this snapshot."""
        return {
            "agent_contexts": self.agent_contexts,
            "memory": self.memory,
            "costs": self.costs,
            "a2a_log": self.a2a_log,
            "metadata": self.metadata,
        }


class StateExporter:
    """Exports the full Pry session state to a JSON file.

    Use :meth:`build_snapshot` to construct a structured :class:`ExportSnapshot`
    from raw session data, then call :meth:`export` or :meth:`export_snapshot`
    to write it to disk.

    Example::

        exporter = StateExporter()
        snapshot = StateExporter.build_snapshot(
            agent_contexts={"agent-1": {"status": "RUNNING"}},
            memory=[{"id": "m1", "content": "fact"}],
            costs={"agent-1": 0.05},
            a2a_log=[{"from": "agent-1", "to": "agent-2", "msg": "done"}],
        )
        exporter.export_snapshot(snapshot, "/tmp/debug.json")
    """

    # ------------------------------------------------------------------
    # Low-level write — accepts any pre-built dict
    # ------------------------------------------------------------------

    def export(self, state: dict[str, object], path: str) -> str:
        """Write *state* to a JSON file at *path* and return the JSON string.

        The caller is responsible for building *state* with the required keys
        (``agent_contexts``, ``memory``, ``costs``, ``a2a_log``).  For a
        type-safe alternative, use :meth:`export_snapshot`.

        Args:
            state: Full session state dict.
            path: Destination file path.

        Returns:
            The JSON string that was written to *path*.
        """
        payload = json.dumps(state, indent=2, default=str)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(payload)
        return payload

    # ------------------------------------------------------------------
    # High-level API — structured snapshot
    # ------------------------------------------------------------------

    @staticmethod
    def build_snapshot(
        *,
        agent_contexts: dict[str, dict[str, object]] | None = None,
        memory: list[dict[str, object]] | None = None,
        costs: dict[str, float] | None = None,
        a2a_log: list[dict[str, object]] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ExportSnapshot:
        """Construct a :class:`ExportSnapshot` from raw session data.

        Args:
            agent_contexts: Per-agent context dicts keyed by agent_id.
            memory: Memory entries captured during the session.
            costs: Per-agent cumulative cost keyed by agent_id.
            a2a_log: Ordered list of A2A message records.
            metadata: Optional session metadata.

        Returns:
            A populated :class:`ExportSnapshot`.
        """
        return ExportSnapshot(
            agent_contexts=agent_contexts or {},
            memory=memory or [],
            costs=costs or {},
            a2a_log=a2a_log or [],
            metadata=metadata or {},
        )

    def export_snapshot(self, snapshot: ExportSnapshot, path: str) -> str:
        """Write *snapshot* to a JSON file and return the JSON string.

        Args:
            snapshot: The :class:`ExportSnapshot` to serialise.
            path: Destination file path.

        Returns:
            The JSON string that was written to *path*.
        """
        return self.export(snapshot.to_dict(), path)
