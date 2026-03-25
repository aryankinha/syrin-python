"""PII Scanner guardrail."""

from __future__ import annotations

import re
from re import Pattern

from syrin.guardrails.base import Guardrail
from syrin.guardrails.context import GuardrailContext
from syrin.guardrails.decision import GuardrailDecision


class PIIScanner(Guardrail):
    """Guardrail that detects and optionally redacts PII.

    Detects common PII patterns including:
    - Email addresses
    - Phone numbers
    - Social Security Numbers
    - Credit card numbers
    - IP addresses

    Example:
        >>> guardrail = PIIScanner(redact=True)
        >>> result = await guardrail.evaluate(context)
        >>> if result.metadata.get("redacted_text"):
        ...     # Use redacted version
    """

    # PII detection patterns
    PATTERNS = {
        "email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email address"),
        "phone": (
            r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
            "Phone number",
        ),
        "ssn": (r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b", "Social Security Number"),
        "credit_card": (r"\b(?:\d{4}[-.\s]?){3}\d{4}\b", "Credit card number"),
        "ip_address": (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "IP address"),
    }

    def __init__(
        self,
        name: str | None = None,
        redact: bool = False,
        redaction_char: str = "*",
        custom_patterns: dict[str, tuple[str, str]] | None = None,
        allow_types: list[str] | None = None,
    ):
        """Initialize PII scanner.

        Args:
            name: Optional custom name.
            redact: If True, provide redacted text in metadata.
            redaction_char: Character to use for redaction.
            custom_patterns: Additional regex patterns to check.
            allow_types: List of PII types to allow (not block).
        """
        super().__init__(name)
        self.redact = redact
        self.redaction_char = redaction_char
        self.allow_types = set(allow_types or [])

        # Compile patterns
        self._patterns: dict[str, tuple[Pattern[str], str]] = {}

        # Add built-in patterns
        for pii_type, (pattern, description) in self.PATTERNS.items():
            if pii_type not in self.allow_types:
                self._patterns[pii_type] = (re.compile(pattern), description)

        # Add custom patterns
        if custom_patterns:
            for pii_type, (pattern, description) in custom_patterns.items():
                self._patterns[pii_type] = (re.compile(pattern), description)

    async def evaluate(self, context: GuardrailContext) -> GuardrailDecision:
        """Scan text for PII.

        Args:
            context: Guardrail context with text to scan.

        Returns:
            GuardrailDecision with PII detection results.
        """
        text = context.text
        findings = []
        redacted_text = text if self.redact else None

        for pii_type, (pattern, description) in self._patterns.items():
            matches = pattern.findall(text)

            for match in matches:
                finding = {
                    "type": pii_type,
                    "description": description,
                    "value": match if not self.redact else self._redact(match),
                }
                findings.append(finding)

                if self.redact and redacted_text:
                    redacted = self._redact(match)
                    redacted_text = redacted_text.replace(match, redacted)

        if findings:
            return GuardrailDecision(
                passed=False,
                rule="pii_detected",
                reason=f"PII detected: {', '.join({f['type'] for f in findings})}",
                confidence=1.0,
                metadata={
                    "findings": findings,
                    "redacted_text": redacted_text if self.redact else None,
                    "count": len(findings),
                },
                alternatives=[
                    "Remove personal information from your message",
                    "Use anonymized data instead",
                ],
            )

        return GuardrailDecision(
            passed=True,
            rule="pii_check",
            metadata={"pii_types_checked": list(self._patterns.keys())},
        )

    def _redact(self, text: str) -> str:
        """Redact sensitive text.

        Args:
            text: Text to redact.

        Returns:
            Redacted text.
        """
        # Keep first and last character, redact middle
        if len(text) <= 4:
            return self.redaction_char * len(text)

        return text[0] + self.redaction_char * (len(text) - 2) + text[-1]
