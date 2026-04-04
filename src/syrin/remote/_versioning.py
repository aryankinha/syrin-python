"""VersionedConfig — config versioning and rollback with hook support."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from syrin.enums import Hook


class RollbackError(Exception):
    """Raised when rollback is attempted but no prior version exists.

    Attributes:
        current_version: The version that was active when rollback was attempted.
    """

    def __init__(self, current_version: int) -> None:
        """Initialise with the current (lowest) version.

        Args:
            current_version: Version number that could not be rolled back from.
        """
        self.current_version = current_version
        super().__init__(f"Cannot rollback: already at version {current_version} (no prior state)")


@dataclass
class ConfigSnapshot:
    """A point-in-time snapshot of config values.

    Attributes:
        version: The version number when this snapshot was taken.
        values: Config path-to-value mapping at this version.
    """

    version: int
    values: dict[str, object]


class VersionedConfig:
    """Tracks config changes with full version history and rollback support.

    Each call to :meth:`push` creates a snapshot of the *previous* state
    before applying the new values. :meth:`rollback` reverts to the most
    recent snapshot, firing ``Hook.CONFIG_ROLLBACK`` when a ``fire_fn`` is
    provided.

    Example:
        >>> vc = VersionedConfig()
        >>> vc.push({"budget.max_cost": 5.0})
        1
        >>> vc.push({"budget.max_cost": 10.0})
        2
        >>> snap = vc.rollback()
        >>> snap.version
        1
        >>> vc.current_values["budget.max_cost"]
        5.0
    """

    def __init__(
        self,
        fire_fn: Callable[[Hook, dict[str, object]], None] | None = None,
    ) -> None:
        """Initialise at version 0 with empty state.

        Args:
            fire_fn: Optional hook-firing callback ``(Hook, dict) -> None``.
        """
        self._fire_fn = fire_fn
        self._version: int = 0
        self._current_values: dict[str, object] = {}
        # Internal sentinel for the initial (v0) state — not exposed via history.
        # After each push the new snapshot is appended; rollback pops from this list.
        self._snapshots: list[ConfigSnapshot] = [ConfigSnapshot(version=0, values={})]
        # Tracks whether the initial sentinel has been "pushed past" — if _version == 0,
        # history is empty (only the sentinel exists, which is internal).

    def push(self, changes: dict[str, object]) -> int:
        """Apply changes and increment the version counter.

        The current state is merged with *changes* (new values override existing
        ones). A snapshot of the *current* values is saved before applying.

        Args:
            changes: Mapping of config paths to new values.

        Returns:
            The new version number after applying the changes.
        """
        new_values = dict(self._current_values)
        new_values.update(changes)
        self._version += 1
        self._current_values = new_values
        self._snapshots.append(ConfigSnapshot(version=self._version, values=dict(new_values)))
        return self._version

    def rollback(self) -> ConfigSnapshot:
        """Revert to the previous version.

        Fires ``Hook.CONFIG_ROLLBACK`` with ``{from_version, to_version}``
        when a ``fire_fn`` was provided.

        Returns:
            The :class:`ConfigSnapshot` that is now active after rollback.

        Raises:
            RollbackError: If currently at version 0 (no prior state).
        """
        if self._version == 0:
            raise RollbackError(self._version)

        from_version = self._version
        # Remove the latest snapshot (current version)
        self._snapshots.pop()
        # The new current snapshot is the one before it
        target = self._snapshots[-1]
        self._version = target.version
        self._current_values = dict(target.values)

        if self._fire_fn is not None:
            from syrin.enums import Hook

            self._fire_fn(
                Hook.CONFIG_ROLLBACK,
                {"from_version": from_version, "to_version": self._version},
            )

        return target

    @property
    def current_version(self) -> int:
        """Current version number. Starts at 0; increments on each :meth:`push`.

        Returns:
            Integer version counter.
        """
        return self._version

    @property
    def current_values(self) -> dict[str, object]:
        """Current config path-to-value mapping (copy).

        Returns:
            Shallow copy of the active config values.
        """
        return dict(self._current_values)

    @property
    def history(self) -> list[ConfigSnapshot]:
        """All recorded snapshots from version 1 onwards (excludes the initial v0 sentinel).

        Returns an empty list when no :meth:`push` has been called yet.

        Returns:
            List of :class:`ConfigSnapshot` objects, ordered from oldest to newest.
        """
        # The first element in _snapshots is always the internal v0 sentinel.
        # History exposes only the snapshots produced by push() calls.
        return list(self._snapshots[1:])
