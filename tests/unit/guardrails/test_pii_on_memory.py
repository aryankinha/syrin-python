"""Tests for PIIGuardrail with on_memory=PIIAction.REJECT.

Exit criteria:
- PIIGuardrail(on_memory=PIIAction.REJECT) raises PIIMemoryRejectedError
  when check_memory_write() is called with PII content.
- No error when content has no PII.
- on_memory=None disables memory write checking entirely.
"""

from __future__ import annotations

import pytest

from syrin.security.pii import PIIAction, PIIEntityType, PIIGuardrail, PIIMemoryRejectedError


class TestPIIGuardrailOnMemory:
    """PIIGuardrail(on_memory=PIIAction.REJECT) blocks PII writes to memory."""

    def test_rejects_pii_content_on_memory_write(self) -> None:
        """PIIMemoryRejectedError raised when PII detected in memory write."""
        guard = PIIGuardrail(
            detect=[PIIEntityType.SSN],
            on_memory=PIIAction.REJECT,
        )
        with pytest.raises(PIIMemoryRejectedError):
            guard.check_memory_write("User SSN is 123-45-6789")

    def test_no_error_for_clean_content(self) -> None:
        """check_memory_write() does not raise for content without PII."""
        guard = PIIGuardrail(
            detect=[PIIEntityType.SSN],
            on_memory=PIIAction.REJECT,
        )
        # Should not raise
        guard.check_memory_write("User likes cats and dogs")

    def test_on_memory_none_disables_check(self) -> None:
        """check_memory_write() does nothing when on_memory is None."""
        guard = PIIGuardrail(
            detect=[PIIEntityType.SSN],
            on_memory=None,  # disabled
        )
        # Should not raise even for PII content
        guard.check_memory_write("User SSN is 123-45-6789")

    def test_rejected_error_has_findings(self) -> None:
        """PIIMemoryRejectedError includes the PII findings."""
        guard = PIIGuardrail(
            detect=[PIIEntityType.SSN, PIIEntityType.EMAIL],
            on_memory=PIIAction.REJECT,
        )
        with pytest.raises(PIIMemoryRejectedError) as exc_info:
            guard.check_memory_write("SSN: 123-45-6789, email: user@example.com")

        err = exc_info.value
        assert hasattr(err, "findings")
        assert len(err.findings) >= 1

    def test_on_memory_reject_does_not_affect_scan(self) -> None:
        """on_memory does not change scan() behaviour."""
        guard = PIIGuardrail(
            detect=[PIIEntityType.SSN],
            action=PIIAction.REDACT,
            on_memory=PIIAction.REJECT,
        )
        # scan() should still redact (not reject) — on_memory only applies to memory writes
        result = guard.scan("SSN: 123-45-6789")
        assert result.found
        assert result.should_block is False
        assert result.redacted_text is not None
        assert "[REDACTED]" in (result.redacted_text or "")

    def test_on_memory_reject_email_pii(self) -> None:
        """REJECT blocks email PII from being written to memory."""
        guard = PIIGuardrail(
            detect=[PIIEntityType.EMAIL],
            on_memory=PIIAction.REJECT,
        )
        with pytest.raises(PIIMemoryRejectedError):
            guard.check_memory_write("Contact me at alice@example.com")
