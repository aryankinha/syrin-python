"""syrin.security — Security hardening utilities for AI agents.

Provides:
- ``PIIGuardrail``: Regex-based PII scanner with configurable action and hook firing.
- ``PIIEntityType``: StrEnum of detectable PII entity types.
- ``PIIAction``: StrEnum of actions to take on detected PII.
- ``PIIFinding``: A single detected PII occurrence.
- ``PIIScanResult``: Result of a PII scan.
- ``ToolOutputValidator``: Validates and sanitizes tool output for security threats.
- ``ToolOutputConfig``: Configuration for tool output validation.
- ``ToolOutputResult``: Result of tool output validation.
- ``AgentIdentity``: Ed25519 cryptographic identity for agents.
- ``CanaryTokens``: Per-session canary tokens for injection detection.
- ``SecretCache``: TTL-bounded in-memory secret cache.
- ``SafeExporter``: Exports data with PII fields redacted.
- ``DelimiterFactory``: Creates unpredictable delimiters with random salt.
"""

from __future__ import annotations

from syrin.security.cache import SecretCache
from syrin.security.canary import CanaryTokens
from syrin.security.delimiter import DelimiterFactory
from syrin.security.export import SafeExporter
from syrin.security.identity import AgentIdentity
from syrin.security.pii import (
    PIIAction,
    PIIEntityType,
    PIIFinding,
    PIIGuardrail,
    PIIMemoryRejectedError,
    PIIScanResult,
)
from syrin.security.tool_output import ToolOutputConfig, ToolOutputResult, ToolOutputValidator

__all__ = [
    "AgentIdentity",
    "CanaryTokens",
    "DelimiterFactory",
    "PIIAction",
    "PIIEntityType",
    "PIIFinding",
    "PIIGuardrail",
    "PIIMemoryRejectedError",
    "PIIScanResult",
    "SafeExporter",
    "SecretCache",
    "ToolOutputConfig",
    "ToolOutputResult",
    "ToolOutputValidator",
]
