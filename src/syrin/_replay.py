"""replay_trace() — replay a JSONL trace file as a list of events."""

from __future__ import annotations

import json


def replay_trace(
    path: str,
    from_step: int | None = None,
) -> list[dict[str, object]]:
    """Read a JSONL trace file and return a list of event dicts.

    Args:
        path: Path to the ``.jsonl`` trace file.
        from_step: If given, return only events whose ``"step"`` value is
            ``>= from_step``.  When no ``"step"`` key is present on an event
            the event index (0-based) is used as the step number.

    Returns:
        A list of event dictionaries parsed from the file.

    Raises:
        FileNotFoundError: If ``path`` does not exist.

    Example::

        from syrin import replay_trace

        events = replay_trace("run.jsonl")
        for e in events:
            print(e["event"])
    """
    with open(path) as fh:
        raw = fh.read()

    events: list[dict[str, object]] = []
    step_index = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data: dict[str, object] = json.loads(line)
        except json.JSONDecodeError:
            continue
        step = data.get("step", step_index)
        if from_step is not None and int(step) < from_step:  # type: ignore[call-overload]
            step_index += 1
            continue
        events.append(data)
        step_index += 1

    return events
