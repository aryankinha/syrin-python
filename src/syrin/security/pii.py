"""PIIGuardrail — regex-based PII scanner with configurable action and hook firing."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from re import Pattern

from syrin.enums import Hook


class PIIEntityType(StrEnum):
    """PII entity types that can be detected.

    Attributes:
        SSN: US Social Security Number (XXX-XX-XXXX).
        EMAIL: Email address.
        PHONE: US phone number.
        CREDIT_CARD: Credit card number (Luhn-validated).
        IP_ADDRESS: IPv4 address.
    """

    SSN = "ssn"
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"


class PIIAction(StrEnum):
    """Action to take when PII is detected.

    Attributes:
        REDACT: Replace PII with [REDACTED] placeholder.
        REJECT: Block the content entirely (should_block=True).
        AUDIT: Log the finding without modifying content.
    """

    REDACT = "redact"
    REJECT = "reject"
    AUDIT = "audit"


@dataclass
class PIIFinding:
    """A single detected PII occurrence.

    Attributes:
        entity_type: The type of PII detected.
        original: The original matched text.
        start: Character index of match start.
        end: Character index of match end.
    """

    entity_type: PIIEntityType
    original: str
    start: int
    end: int


@dataclass
class PIIScanResult:
    """Result of scanning text for PII.

    Attributes:
        found: True if any PII was detected.
        findings: All detected PII occurrences.
        redacted_text: Text with PII replaced by [REDACTED] (only when action=REDACT).
        should_block: True when action=REJECT and PII was found.
        audit_entries: Audit entries created (only when action=AUDIT).
    """

    found: bool
    findings: list[PIIFinding]
    redacted_text: str | None
    should_block: bool
    audit_entries: list[str] = field(default_factory=list)


def _luhn_valid(number: str) -> bool:
    """Return True if number passes the Luhn check (credit card validation).

    Args:
        number: String containing only digits.

    Returns:
        True if Luhn checksum is valid.
    """
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _valid_ip(match: str) -> bool:
    """Return True if all four octets are in 0-255 (IP address validation).

    Args:
        match: Candidate IP address string.

    Returns:
        True if all octets are valid.
    """
    parts = match.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


# Raw patterns keyed by entity type
_RAW_PATTERNS: dict[PIIEntityType, str] = {
    PIIEntityType.EMAIL: r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    PIIEntityType.PHONE: r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
    PIIEntityType.SSN: r"\b\d{3}-\d{2}-\d{4}\b",
    PIIEntityType.CREDIT_CARD: r"\b(?:\d{4}[-.\s]?){3}\d{4}\b",
    PIIEntityType.IP_ADDRESS: r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
}


class PIIMemoryRejectedError(ValueError):
    """Raised when ``PIIGuardrail(on_memory=PIIAction.REJECT)`` blocks a memory write.

    Attributes:
        findings: The PII findings that triggered the rejection.
    """

    def __init__(self, message: str, findings: list[PIIFinding]) -> None:
        super().__init__(message)
        self.findings = findings


class PIIGuardrail:
    """Regex-based PII scanner with configurable action and hook firing.

    Does NOT make LLM calls. Pattern-only detection.
    Does NOT inherit from Guardrail base (standalone scanner).

    Args:
        detect: List of entity types to detect. ``None`` detects all types.
        action: Action to take when PII is found. Defaults to REDACT.
        fire_event_fn: Optional callback to fire lifecycle hooks.

    Example:
        >>> guard = PIIGuardrail(detect=[PIIEntityType.SSN], action=PIIAction.REDACT)
        >>> result = guard.scan("My SSN is 123-45-6789")
        >>> assert result.found
        >>> assert "[REDACTED]" in (result.redacted_text or "")
    """

    def __init__(
        self,
        detect: list[PIIEntityType] | None = None,
        action: PIIAction = PIIAction.REDACT,
        fire_event_fn: Callable[[Hook, dict[str, object]], None] | None = None,
        on_memory: PIIAction | None = None,
    ) -> None:
        """Initialize PIIGuardrail.

        Args:
            detect: Entity types to detect. None = detect all.
            action: Action to take on detected PII in text scanning.
            fire_event_fn: Optional hook firing callback.
            on_memory: Action to take when PII is found in a memory write.
                ``PIIAction.REJECT`` blocks the write and raises
                :class:`PIIMemoryRejectedError`. ``None`` (default) disables
                memory write checking.
        """
        self._action = action
        self._fire_event_fn = fire_event_fn
        self._on_memory = on_memory
        active_types = detect if detect is not None else list(PIIEntityType)
        self._patterns: dict[PIIEntityType, Pattern[str]] = {
            et: re.compile(_RAW_PATTERNS[et]) for et in active_types
        }

    def check_memory_write(self, content: str) -> None:
        """Check whether *content* is safe to write to memory.

        Scans *content* for PII and applies the ``on_memory`` action.
        Has no effect when ``on_memory`` is ``None``.

        Args:
            content: Text that would be written to persistent memory.

        Raises:
            PIIMemoryRejectedError: When ``on_memory=PIIAction.REJECT`` and
                PII is detected in *content*.
        """
        if self._on_memory is None:
            return
        result = self.scan(content)
        if not result.found:
            return
        if self._on_memory == PIIAction.REJECT:
            raise PIIMemoryRejectedError(
                f"Memory write blocked: PII detected ({len(result.findings)} finding(s)). "
                "Remove PII before writing to memory.",
                findings=result.findings,
            )

    def scan(self, text: str) -> PIIScanResult:
        """Scan text for PII and take configured action.

        Fires hooks: PII_DETECTED (when found), then PII_REDACTED / PII_BLOCKED /
        PII_AUDIT depending on action.

        Args:
            text: Input text to scan.

        Returns:
            PIIScanResult with findings and action results.
        """
        findings: list[PIIFinding] = []

        for entity_type, pattern in self._patterns.items():
            for m in pattern.finditer(text):
                matched = m.group(0)
                if entity_type == PIIEntityType.CREDIT_CARD and not _luhn_valid(matched):
                    continue
                if entity_type == PIIEntityType.IP_ADDRESS and not _valid_ip(matched):
                    continue
                findings.append(
                    PIIFinding(
                        entity_type=entity_type,
                        original=matched,
                        start=m.start(),
                        end=m.end(),
                    )
                )

        found = bool(findings)

        if not found:
            return PIIScanResult(
                found=False,
                findings=[],
                redacted_text=text if self._action == PIIAction.REDACT else None,
                should_block=False,
                audit_entries=[],
            )

        # Fire PII_DETECTED
        if self._fire_event_fn is not None:
            self._fire_event_fn(
                Hook.PII_DETECTED,
                {
                    "count": len(findings),
                    "entity_types": [f.entity_type for f in findings],
                },
            )

        redacted_text: str | None = None
        should_block = False
        audit_entries: list[str] = []

        if self._action == PIIAction.REDACT:
            redacted = text
            for finding in findings:
                redacted = redacted.replace(finding.original, "[REDACTED]")
            redacted_text = redacted
            if self._fire_event_fn is not None:
                self._fire_event_fn(Hook.PII_REDACTED, {"redacted_count": len(findings)})

        elif self._action == PIIAction.REJECT:
            should_block = True
            if self._fire_event_fn is not None:
                self._fire_event_fn(Hook.PII_BLOCKED, {"blocked_count": len(findings)})

        elif self._action == PIIAction.AUDIT:
            for f in findings:
                audit_entries.append(f"PII detected: {f.entity_type} at [{f.start}:{f.end}]")
            if self._fire_event_fn is not None:
                self._fire_event_fn(Hook.PII_AUDIT, {"audit_count": len(audit_entries)})

        return PIIScanResult(
            found=found,
            findings=findings,
            redacted_text=redacted_text,
            should_block=should_block,
            audit_entries=audit_entries,
        )
