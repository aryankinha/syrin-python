"""Tests for PIIGuardrail — Phase 7 TDD (write tests first, red → green)."""

from __future__ import annotations

from syrin.enums import Hook
from syrin.security.pii import PIIAction, PIIEntityType, PIIGuardrail

# ---------------------------------------------------------------------------
# P7-T1-1: Construction
# ---------------------------------------------------------------------------


def test_pii_guardrail_constructs_with_detect_list() -> None:
    """PIIGuardrail(detect=[PIIEntityType.SSN]) constructs without error."""
    guard = PIIGuardrail(detect=[PIIEntityType.SSN])
    assert guard is not None


def test_pii_guardrail_constructs_defaults() -> None:
    """PIIGuardrail() with no args constructs (detects all, action=REDACT)."""
    guard = PIIGuardrail()
    assert guard is not None


# ---------------------------------------------------------------------------
# P7-T1-2: SSN detection
# ---------------------------------------------------------------------------


def test_ssn_detected() -> None:
    """SSN '123-45-6789' is found by PIIGuardrail configured for SSN."""
    guard = PIIGuardrail(detect=[PIIEntityType.SSN], action=PIIAction.REDACT)
    result = guard.scan("My SSN is 123-45-6789")
    assert result.found is True
    assert any(f.entity_type == PIIEntityType.SSN for f in result.findings)


# ---------------------------------------------------------------------------
# P7-T1-3: REDACT action
# ---------------------------------------------------------------------------


def test_action_redact_replaces_pii_with_placeholder() -> None:
    """REDACT action → redacted_text = 'My SSN is [REDACTED]'."""
    guard = PIIGuardrail(detect=[PIIEntityType.SSN], action=PIIAction.REDACT)
    result = guard.scan("My SSN is 123-45-6789")
    assert result.redacted_text is not None
    assert "[REDACTED]" in result.redacted_text
    assert "123-45-6789" not in result.redacted_text


# ---------------------------------------------------------------------------
# P7-T1-4: REJECT action
# ---------------------------------------------------------------------------


def test_action_reject_sets_should_block() -> None:
    """REJECT action → PIIScanResult.should_block = True."""
    guard = PIIGuardrail(detect=[PIIEntityType.SSN], action=PIIAction.REJECT)
    result = guard.scan("My SSN is 123-45-6789")
    assert result.should_block is True


# ---------------------------------------------------------------------------
# P7-T1-5: AUDIT action
# ---------------------------------------------------------------------------


def test_action_audit_does_not_block_but_creates_audit_entry() -> None:
    """AUDIT → should_block=False, audit_entries populated."""
    guard = PIIGuardrail(detect=[PIIEntityType.SSN], action=PIIAction.AUDIT)
    result = guard.scan("My SSN is 123-45-6789")
    assert result.should_block is False
    assert len(result.audit_entries) > 0


# ---------------------------------------------------------------------------
# P7-T1-6: Email detection
# ---------------------------------------------------------------------------


def test_email_detected() -> None:
    """Email address detected in 'Contact john@example.com'."""
    guard = PIIGuardrail(detect=[PIIEntityType.EMAIL], action=PIIAction.REDACT)
    result = guard.scan("Contact john@example.com")
    assert result.found is True
    assert any(f.entity_type == PIIEntityType.EMAIL for f in result.findings)


# ---------------------------------------------------------------------------
# P7-T1-7: Phone detection
# ---------------------------------------------------------------------------


def test_phone_detected() -> None:
    """Phone number detected in 'Call 555-123-4567'."""
    guard = PIIGuardrail(detect=[PIIEntityType.PHONE], action=PIIAction.REDACT)
    result = guard.scan("Call 555-123-4567")
    assert result.found is True
    assert any(f.entity_type == PIIEntityType.PHONE for f in result.findings)


# ---------------------------------------------------------------------------
# P7-T1-8: Credit card detection (Luhn valid)
# ---------------------------------------------------------------------------


def test_credit_card_detected() -> None:
    """Credit card number with valid Luhn detected."""
    # 4532015112830366 is a valid Luhn number
    guard = PIIGuardrail(detect=[PIIEntityType.CREDIT_CARD], action=PIIAction.REDACT)
    result = guard.scan("Pay with card 4532015112830366")
    assert result.found is True
    assert any(f.entity_type == PIIEntityType.CREDIT_CARD for f in result.findings)


# ---------------------------------------------------------------------------
# P7-T1-9: IP address detection
# ---------------------------------------------------------------------------


def test_ip_address_detected() -> None:
    """IPv4 address detected in 'Server at 192.168.1.1'."""
    guard = PIIGuardrail(detect=[PIIEntityType.IP_ADDRESS], action=PIIAction.REDACT)
    result = guard.scan("Server at 192.168.1.1")
    assert result.found is True
    assert any(f.entity_type == PIIEntityType.IP_ADDRESS for f in result.findings)


# ---------------------------------------------------------------------------
# P7-T1-10: Entity type filter
# ---------------------------------------------------------------------------


def test_ssn_filter_does_not_flag_email() -> None:
    """Guard configured for SSN only does not flag email addresses."""
    guard = PIIGuardrail(detect=[PIIEntityType.SSN], action=PIIAction.REDACT)
    result = guard.scan("Contact john@example.com")
    assert result.found is False
    assert all(f.entity_type == PIIEntityType.SSN for f in result.findings)


# ---------------------------------------------------------------------------
# P7-T1-11: PII_DETECTED hook
# ---------------------------------------------------------------------------


def test_fire_event_receives_pii_detected_hook() -> None:
    """fire_event_fn receives PII_DETECTED hook when PII found."""
    events: list[tuple[Hook, dict[str, object]]] = []

    def capture(hook: Hook, ctx: dict[str, object]) -> None:
        events.append((hook, ctx))

    guard = PIIGuardrail(detect=[PIIEntityType.SSN], action=PIIAction.REDACT, fire_event_fn=capture)
    guard.scan("My SSN is 123-45-6789")
    hooks_fired = [e[0] for e in events]
    assert Hook.PII_DETECTED in hooks_fired


# ---------------------------------------------------------------------------
# P7-T1-12: PII_REDACTED hook
# ---------------------------------------------------------------------------


def test_fire_event_receives_pii_redacted_hook() -> None:
    """fire_event_fn receives PII_REDACTED hook when action=REDACT."""
    events: list[tuple[Hook, dict[str, object]]] = []

    def capture(hook: Hook, ctx: dict[str, object]) -> None:
        events.append((hook, ctx))

    guard = PIIGuardrail(detect=[PIIEntityType.SSN], action=PIIAction.REDACT, fire_event_fn=capture)
    guard.scan("My SSN is 123-45-6789")
    hooks_fired = [e[0] for e in events]
    assert Hook.PII_REDACTED in hooks_fired


# ---------------------------------------------------------------------------
# P7-T1-13: PII_BLOCKED hook
# ---------------------------------------------------------------------------


def test_fire_event_receives_pii_blocked_hook() -> None:
    """fire_event_fn receives PII_BLOCKED hook when action=REJECT."""
    events: list[tuple[Hook, dict[str, object]]] = []

    def capture(hook: Hook, ctx: dict[str, object]) -> None:
        events.append((hook, ctx))

    guard = PIIGuardrail(detect=[PIIEntityType.SSN], action=PIIAction.REJECT, fire_event_fn=capture)
    guard.scan("My SSN is 123-45-6789")
    hooks_fired = [e[0] for e in events]
    assert Hook.PII_BLOCKED in hooks_fired


# ---------------------------------------------------------------------------
# P7-T1-14: PII_AUDIT hook
# ---------------------------------------------------------------------------


def test_fire_event_receives_pii_audit_hook() -> None:
    """fire_event_fn receives PII_AUDIT hook when action=AUDIT."""
    events: list[tuple[Hook, dict[str, object]]] = []

    def capture(hook: Hook, ctx: dict[str, object]) -> None:
        events.append((hook, ctx))

    guard = PIIGuardrail(detect=[PIIEntityType.SSN], action=PIIAction.AUDIT, fire_event_fn=capture)
    guard.scan("My SSN is 123-45-6789")
    hooks_fired = [e[0] for e in events]
    assert Hook.PII_AUDIT in hooks_fired


# ---------------------------------------------------------------------------
# P7-T1-15: Clean text — no PII, no hooks
# ---------------------------------------------------------------------------


def test_clean_text_no_pii_no_hooks() -> None:
    """Clean text → found=False, no hooks fired."""
    events: list[tuple[Hook, dict[str, object]]] = []

    def capture(hook: Hook, ctx: dict[str, object]) -> None:
        events.append((hook, ctx))

    guard = PIIGuardrail(fire_event_fn=capture)
    result = guard.scan("The weather is sunny today.")
    assert result.found is False
    assert len(events) == 0


# ---------------------------------------------------------------------------
# P7-T1-extra: PIIFinding has correct fields
# ---------------------------------------------------------------------------


def test_pii_finding_has_correct_fields() -> None:
    """PIIFinding has entity_type, original, start, end."""
    guard = PIIGuardrail(detect=[PIIEntityType.SSN], action=PIIAction.REDACT)
    result = guard.scan("My SSN is 123-45-6789")
    assert result.found
    finding = result.findings[0]
    assert finding.entity_type == PIIEntityType.SSN
    assert "123-45-6789" in finding.original
    assert isinstance(finding.start, int)
    assert isinstance(finding.end, int)
    assert finding.end > finding.start


# ---------------------------------------------------------------------------
# P7-T1-extra: REDACT with no PII → redacted_text equals original
# ---------------------------------------------------------------------------


def test_redact_clean_text_returns_original() -> None:
    """REDACT action on clean text → redacted_text equals input."""
    guard = PIIGuardrail(action=PIIAction.REDACT)
    result = guard.scan("Hello world")
    assert result.found is False
    assert result.redacted_text == "Hello world"
