"""Shared event loop for sync wrappers. Avoids set_event_loop to not pollute process state."""

from __future__ import annotations

import asyncio
import logging

_log = logging.getLogger(__name__)

_loop: asyncio.AbstractEventLoop | None = None


def get_loop() -> asyncio.AbstractEventLoop:
    """Get event loop for sync wrappers. Prefers running loop; creates one if needed.

    Does NOT call asyncio.set_event_loop() to avoid corrupting FastAPI/Celery etc.
    """
    global _loop
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        pass
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop
