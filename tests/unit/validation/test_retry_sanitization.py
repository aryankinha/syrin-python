"""Retry prompt sanitization: control character and injection stripping.

Tests that:
- get_retry_prompt strips null bytes and control characters from error_message
- Unicode direction overrides are stripped
- ANSI escape sequences are stripped
- Legitimate error messages are preserved intact
"""

from __future__ import annotations

from syrin.validation import get_retry_prompt


class _FakeModel:
    @classmethod
    def model_json_schema(cls) -> dict:
        return {"type": "object", "properties": {}}


class TestRetryPromptSanitization:
    def test_null_bytes_stripped(self) -> None:
        """NUL bytes in error_message must not appear in retry prompt."""
        error = "Invalid field\x00 injected"
        prompt = get_retry_prompt(_FakeModel, error)  # type: ignore[arg-type]
        assert "\x00" not in prompt, "NUL byte should be stripped from retry prompt"

    def test_control_characters_stripped(self) -> None:
        """ASCII control chars (SOH, STX, BEL, etc.) must be stripped."""
        error = "Error\x01\x02\x07\x1b[33mcolored\x1b[0m"
        prompt = get_retry_prompt(_FakeModel, error)  # type: ignore[arg-type]
        assert "\x01" not in prompt
        assert "\x02" not in prompt
        assert "\x07" not in prompt

    def test_ansi_escape_stripped(self) -> None:
        """ANSI escape sequences must be stripped (potential terminal injection)."""
        error = "\x1b[31mRed text\x1b[0m is not valid JSON"
        prompt = get_retry_prompt(_FakeModel, error)  # type: ignore[arg-type]
        assert "\x1b" not in prompt, "ESC (ANSI start) must be stripped"

    def test_unicode_direction_override_stripped(self) -> None:
        """Unicode RLO/LRO direction override must be stripped."""
        # U+202E = RIGHT-TO-LEFT OVERRIDE
        error = "Error \u202e with direction override"
        prompt = get_retry_prompt(_FakeModel, error)  # type: ignore[arg-type]
        assert "\u202e" not in prompt

    def test_normal_error_message_preserved(self) -> None:
        """Normal alphanumeric error messages must not be corrupted."""
        error = "field 'name' is required but missing"
        prompt = get_retry_prompt(_FakeModel, error)  # type: ignore[arg-type]
        # The error text should appear in the prompt
        assert "name" in prompt
        assert "required" in prompt

    def test_newlines_in_error_preserved(self) -> None:
        """Newlines within error message are acceptable (not control chars)."""
        error = "Error on line 1\nError on line 2"
        prompt = get_retry_prompt(_FakeModel, error)  # type: ignore[arg-type]
        # The content should still be present
        assert "Error on line 1" in prompt
