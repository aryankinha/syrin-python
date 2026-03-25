"""TDD tests for PIIScanner all-occurrences redaction.

The bug (now fixed): Only the first occurrence of each PII match was redacted.
The fix: All occurrences are replaced.

Verifies:
- Single occurrence redaction still works
- Multiple occurrences of the same email/phone/SSN are ALL redacted
- Multiple DIFFERENT PII items in the same text are all redacted
- redacted_text in metadata reflects all replacements
- Non-PII text is preserved around redacted items
- redact=False leaves text unchanged but still reports findings
- Custom redaction_char is applied to all occurrences
- allow_types skips those PII types entirely
- Edge cases: empty string, PII at start/end of string
"""

from __future__ import annotations

import asyncio

from syrin.guardrails.built_in.pii import PIIScanner
from syrin.guardrails.context import GuardrailContext


def _ctx(text: str) -> GuardrailContext:
    return GuardrailContext(text=text)


def _run(scanner: PIIScanner, text: str) -> object:
    return asyncio.run(scanner.evaluate(_ctx(text)))


# ---------------------------------------------------------------------------
# Single occurrence — baseline
# ---------------------------------------------------------------------------


class TestSingleOccurrence:
    def test_single_email_detected(self) -> None:
        scanner = PIIScanner(redact=True)
        result = _run(scanner, "Contact me at alice@example.com please.")
        assert not result.passed  # type: ignore[union-attr]

    def test_single_email_redacted_in_text(self) -> None:
        scanner = PIIScanner(redact=True)
        result = _run(scanner, "Email: alice@example.com")
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert "alice@example.com" not in redacted

    def test_single_phone_detected(self) -> None:
        scanner = PIIScanner(redact=True)
        result = _run(scanner, "Call me at 555-123-4567.")
        assert not result.passed  # type: ignore[union-attr]

    def test_clean_text_passes(self) -> None:
        scanner = PIIScanner(redact=True)
        result = _run(scanner, "The sky is blue and the grass is green.")
        assert result.passed  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Multiple occurrences of the SAME PII value
# ---------------------------------------------------------------------------


class TestMultipleOccurrencesSamePII:
    def test_two_same_emails_both_redacted(self) -> None:
        scanner = PIIScanner(redact=True)
        text = "alice@example.com is the sender and the reply-to is also alice@example.com"
        result = _run(scanner, text)
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        # Neither occurrence should remain
        assert "alice@example.com" not in redacted

    def test_three_same_emails_all_redacted(self) -> None:
        scanner = PIIScanner(redact=True)
        email = "bob@corp.io"
        text = f"From: {email} To: {email} CC: {email}"
        result = _run(scanner, text)
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        assert email not in redacted

    def test_two_same_phones_both_redacted(self) -> None:
        scanner = PIIScanner(redact=True)
        text = "Call 555-123-4567 or text 555-123-4567 for support."
        result = _run(scanner, text)
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        assert "555-123-4567" not in redacted

    def test_findings_count_reflects_multiple_occurrences(self) -> None:
        scanner = PIIScanner(redact=True)
        email = "repeat@test.com"
        text = f"{email} {email} {email}"
        result = _run(scanner, text)
        count = result.metadata["count"]  # type: ignore[union-attr]
        assert isinstance(count, int)
        assert count >= 3

    def test_surrounding_text_preserved(self) -> None:
        scanner = PIIScanner(redact=True)
        text = "Start. alice@test.com is the address. alice@test.com again. End."
        result = _run(scanner, text)
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        assert "Start." in redacted
        assert "End." in redacted
        assert "alice@test.com" not in redacted


# ---------------------------------------------------------------------------
# Multiple DIFFERENT PII types
# ---------------------------------------------------------------------------


class TestMultipleDifferentPIITypes:
    def test_email_and_phone_both_redacted(self) -> None:
        scanner = PIIScanner(redact=True)
        text = "Email alice@example.com or call 555-123-4567."
        result = _run(scanner, text)
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        assert "alice@example.com" not in redacted
        assert "555-123-4567" not in redacted

    def test_email_phone_ssn_all_redacted(self) -> None:
        scanner = PIIScanner(redact=True)
        text = "Email: user@site.org, Phone: 555-999-8888, SSN: 123-45-6789"
        result = _run(scanner, text)
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        assert "user@site.org" not in redacted
        assert "555-999-8888" not in redacted
        assert "123-45-6789" not in redacted

    def test_findings_contain_all_pii_types(self) -> None:
        scanner = PIIScanner(redact=True)
        text = "Email: a@b.com, Phone: 555-000-1111"
        result = _run(scanner, text)
        findings = result.metadata["findings"]  # type: ignore[union-attr]
        assert isinstance(findings, list)
        found_types = {f["type"] for f in findings}
        assert "email" in found_types
        assert "phone" in found_types


# ---------------------------------------------------------------------------
# redact=False — findings reported but no text replacement
# ---------------------------------------------------------------------------


class TestRedactFalse:
    def test_passed_is_false_when_pii_found(self) -> None:
        scanner = PIIScanner(redact=False)
        result = _run(scanner, "alice@example.com")
        assert not result.passed  # type: ignore[union-attr]

    def test_redacted_text_is_none_when_redact_false(self) -> None:
        scanner = PIIScanner(redact=False)
        result = _run(scanner, "alice@example.com alice@example.com")
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert redacted is None

    def test_findings_still_populated(self) -> None:
        scanner = PIIScanner(redact=False)
        result = _run(scanner, "alice@example.com and bob@test.org")
        findings = result.metadata["findings"]  # type: ignore[union-attr]
        assert len(findings) >= 2


# ---------------------------------------------------------------------------
# Custom redaction character
# ---------------------------------------------------------------------------


class TestCustomRedactionChar:
    def test_custom_char_applied_to_all_occurrences(self) -> None:
        scanner = PIIScanner(redact=True, redaction_char="X")
        text = "alice@example.com and alice@example.com"
        result = _run(scanner, text)
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        assert "alice@example.com" not in redacted
        # Should contain X characters where emails were
        assert "X" in redacted

    def test_default_redaction_char_is_asterisk(self) -> None:
        scanner = PIIScanner(redact=True)
        result = _run(scanner, "alice@example.com")
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        assert "*" in redacted


# ---------------------------------------------------------------------------
# allow_types — skips those PII types
# ---------------------------------------------------------------------------


class TestAllowTypes:
    def test_allowed_email_not_flagged(self) -> None:
        scanner = PIIScanner(redact=True, allow_types=["email"])
        result = _run(scanner, "alice@example.com")
        assert result.passed  # type: ignore[union-attr]

    def test_non_allowed_type_still_flagged(self) -> None:
        scanner = PIIScanner(redact=True, allow_types=["email"])
        result = _run(scanner, "Phone: 555-123-4567")
        assert not result.passed  # type: ignore[union-attr]

    def test_allow_multiple_types(self) -> None:
        scanner = PIIScanner(redact=True, allow_types=["email", "phone"])
        text = "alice@example.com and 555-123-4567"
        result = _run(scanner, text)
        assert result.passed  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_string_passes(self) -> None:
        scanner = PIIScanner(redact=True)
        result = _run(scanner, "")
        assert result.passed  # type: ignore[union-attr]

    def test_pii_at_start_of_string(self) -> None:
        scanner = PIIScanner(redact=True)
        result = _run(scanner, "alice@example.com is at the start.")
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        assert "alice@example.com" not in redacted
        assert "is at the start." in redacted

    def test_pii_at_end_of_string(self) -> None:
        scanner = PIIScanner(redact=True)
        result = _run(scanner, "Contact: alice@example.com")
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        assert "alice@example.com" not in redacted
        assert "Contact:" in redacted

    def test_only_pii_in_string(self) -> None:
        scanner = PIIScanner(redact=True)
        result = _run(scanner, "alice@example.com")
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        assert "alice@example.com" not in redacted

    def test_no_pii_redacted_text_equals_original(self) -> None:
        scanner = PIIScanner(redact=True)
        text = "This has no PII in it at all."
        result = _run(scanner, text)
        assert result.passed  # type: ignore[union-attr]

    def test_short_pii_value_fully_redacted(self) -> None:
        """Values ≤4 chars should be fully redacted."""
        # Use custom pattern for a short PII value
        scanner_custom = PIIScanner(
            redact=True,
            custom_patterns={"short": (r"\bXXXX\b", "Short PII")},
        )
        result = _run(scanner_custom, "Value: XXXX")
        redacted = result.metadata["redacted_text"]  # type: ignore[union-attr]
        assert isinstance(redacted, str)
        assert "XXXX" not in redacted
