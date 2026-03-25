"""Agent init hook: register with config registry and transport when cloud is enabled."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from syrin.config import get_config
from syrin.remote._types import OverridePayload

if TYPE_CHECKING:
    from syrin.agent import Agent

_log = logging.getLogger(__name__)


def on_agent_init(agent: Agent) -> None:
    """Called at end of Agent.__init__. Registers agent when cloud_enabled; no-op otherwise.

    Flow when enabled: registry.register(agent) -> transport.register(schema) ->
    apply initial_overrides from SyncResponse -> transport.on_override(agent_id, callback).
    Callback applies incoming OverridePayload via ConfigResolver and emits Hook.REMOTE_CONFIG_*.
    """
    cfg = get_config()
    if not getattr(cfg, "cloud_enabled", False):
        return

    from syrin.remote._registry import get_registry
    from syrin.remote._resolver import ConfigResolver

    registry = get_registry()
    schema = registry.register(agent)
    agent_id = schema.agent_id
    transport = getattr(cfg, "cloud_transport", None)
    if transport is None:
        _log.warning(
            "cloud_enabled but no cloud_transport; skipping transport.register and on_override"
        )
        return

    response = transport.register(schema)
    resolver = ConfigResolver()

    if not response.ok:
        _log.warning(
            "Remote config registration failed (agent=%s). %s Check SYRIN_API_KEY if using Syrin Cloud.",
            agent_id,
            response.error or "Unknown error.",
        )

    if response.ok and response.initial_overrides:
        payload = OverridePayload(
            agent_id=agent_id,
            version=0,
            overrides=response.initial_overrides,
        )
        _apply_payload_and_emit(agent, payload, resolver)

    def callback(payload: OverridePayload) -> None:
        if payload.agent_id != agent_id:
            return
        _apply_payload_and_emit(agent, payload, resolver)

    transport.on_override(agent_id, callback)


def _apply_payload_and_emit(
    agent: object,
    payload: OverridePayload,
    resolver: object,
) -> None:
    """Apply payload via resolver; emit REMOTE_CONFIG_UPDATE or REMOTE_CONFIG_ERROR."""
    from syrin.events import EventContext

    result = resolver.apply_overrides(agent, payload)  # type: ignore[attr-defined]
    emit = getattr(agent, "_emit_event", None)
    if emit is None:
        return
    from syrin.enums import Hook

    if result.accepted:
        emit(
            Hook.REMOTE_CONFIG_UPDATE,
            EventContext(accepted=result.accepted, pending_restart=result.pending_restart),
        )
    if result.rejected:
        emit(
            Hook.REMOTE_CONFIG_ERROR,
            EventContext(rejected=result.rejected),
        )
