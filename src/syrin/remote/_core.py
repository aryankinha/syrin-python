"""Remote config: types, schema extraction, registry, resolver, transports, init()."""

from __future__ import annotations

import os

from syrin.config import get_config
from syrin.remote._protocol import RemoteConfigurable
from syrin.remote._registry import ConfigRegistry, get_registry
from syrin.remote._resolver import ConfigResolver, ResolveResult
from syrin.remote._schema import extract_agent_schema, extract_schema
from syrin.remote._transport import (
    ConfigTransport,
    PollingTransport,
    ServeTransport,
    SSETransport,
)
from syrin.remote._types import (
    AgentSchema,
    ConfigOverride,
    ConfigSchema,
    FieldSchema,
    OverridePayload,
    SyncRequest,
    SyncResponse,
)

_DEFAULT_BASE_URL = "https://api.syrin.ai/v1"


def init(
    *,
    api_key: str | None = None,
    base_url: str = _DEFAULT_BASE_URL,
    transport: ConfigTransport | None = None,
) -> None:
    """Enable remote config. Call once at startup (e.g. after env check).

    With api_key (or SYRIN_API_KEY env): agent registers with Syrin Cloud and
    receives overrides via SSE. With transport: use a custom ConfigTransport
    (e.g. ServeTransport, PollingTransport). When neither is set, cloud stays disabled.

    Args:
        api_key: Syrin Cloud API key. If None, SYRIN_API_KEY env is used.
            When transport is provided, api_key is stored for reference but not passed
            to the transport (custom transports manage their own auth).
        base_url: Config API base URL. Default https://api.syrin.ai/v1.
        transport: Custom transport. When set, this transport is used; api_key and
            base_url are stored on config for reference but not used by the transport.
    """
    cfg = get_config()
    if transport is not None:
        cfg.cloud_enabled = True
        cfg.cloud_transport = transport
        cfg.cloud_base_url = base_url.rstrip("/")
        if api_key:
            cfg.cloud_api_key = api_key
        return
    key = (api_key or os.environ.get("SYRIN_API_KEY") or "").strip()
    if not key:
        return
    cfg.cloud_enabled = True
    cfg.cloud_api_key = key
    cfg.cloud_base_url = base_url.rstrip("/")
    cfg.cloud_transport = SSETransport(base_url=cfg.cloud_base_url, api_key=key)


__all__ = [
    "AgentSchema",
    "ConfigOverride",
    "ConfigRegistry",
    "ConfigResolver",
    "ConfigSchema",
    "ConfigTransport",
    "extract_agent_schema",
    "extract_schema",
    "FieldSchema",
    "get_registry",
    "init",
    "OverridePayload",
    "PollingTransport",
    "RemoteConfigurable",
    "ResolveResult",
    "ServeTransport",
    "SSETransport",
    "SyncRequest",
    "SyncResponse",
]
