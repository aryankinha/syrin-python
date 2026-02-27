"""Tests for serve-related hooks (SERVE_REQUEST_START, SERVE_REQUEST_END)."""

from syrin.audit.handler import _HOOK_TO_AUDIT_EVENT
from syrin.enums import AuditEventType, Hook


def test_serve_request_start_hook_exists() -> None:
    """Hook.SERVE_REQUEST_START exists with expected value."""
    assert Hook.SERVE_REQUEST_START == "serve.request.start"


def test_serve_request_end_hook_exists() -> None:
    """Hook.SERVE_REQUEST_END exists with expected value."""
    assert Hook.SERVE_REQUEST_END == "serve.request.end"


def test_serve_hooks_mapped_to_audit_events() -> None:
    """Serve hooks are mapped to audit event types."""
    assert _HOOK_TO_AUDIT_EVENT[Hook.SERVE_REQUEST_START] == AuditEventType.SERVE_REQUEST_START
    assert _HOOK_TO_AUDIT_EVENT[Hook.SERVE_REQUEST_END] == AuditEventType.SERVE_REQUEST_END


def test_audit_event_type_serve_values() -> None:
    """AuditEventType has SERVE_REQUEST_START and SERVE_REQUEST_END."""
    assert AuditEventType.SERVE_REQUEST_START == "serve_request_start"
    assert AuditEventType.SERVE_REQUEST_END == "serve_request_end"
