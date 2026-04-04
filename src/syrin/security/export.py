"""SafeExporter — exports data with PII fields redacted."""

from __future__ import annotations

_REDACTED = "[REDACTED]"


class SafeExporter:
    """Exports data with PII fields redacted.

    Checks dict keys against a known set of PII field names and replaces
    their values with ``[REDACTED]`` in the output copy. The original dict
    is never mutated.

    Example:
        >>> result = SafeExporter.export({"ssn": "123-45-6789", "name": "Alice"})
        >>> assert result["ssn"] == "[REDACTED]"
        >>> assert result["name"] == "Alice"
    """

    PII_FIELD_NAMES: frozenset[str] = frozenset(
        {
            "ssn",
            "social_security",
            "credit_card",
            "cc_number",
            "password",
            "secret",
            "token",
        }
    )

    @staticmethod
    def export(data: dict[str, object]) -> dict[str, object]:
        """Return a copy of data with PII field values replaced by [REDACTED].

        Only exact key matches (case-sensitive) against ``PII_FIELD_NAMES``
        are redacted. All other fields are preserved unchanged.

        Args:
            data: Source dictionary to export.

        Returns:
            A new dictionary with PII field values replaced by ``[REDACTED]``.
            The original ``data`` dict is not modified.
        """
        result: dict[str, object] = {}
        for key, value in data.items():
            if key in SafeExporter.PII_FIELD_NAMES:
                result[key] = _REDACTED
            else:
                result[key] = value
        return result
