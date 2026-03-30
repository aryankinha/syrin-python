"""Public remote-config package facade.

This package exposes Syrin's remote-configuration contracts, schema extraction,
registry, resolver, transports, and initialization helper. Import from
``syrin.remote`` for the public remote-config API.
"""

from syrin.remote._core import (
    AgentSchema,
    ConfigOverride,
    ConfigRegistry,
    ConfigResolver,
    ConfigSchema,
    ConfigTransport,
    FieldSchema,
    OverridePayload,
    PollingTransport,
    RemoteConfigurable,
    ResolveResult,
    ServeTransport,
    SSETransport,
    SyncRequest,
    SyncResponse,
    extract_agent_schema,
    extract_schema,
    get_registry,
    init,
)

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
