"""PII scanner validation: Luhn check for credit cards and IP octet range validation.

Tests that:
- Valid credit card numbers (pass Luhn) are flagged as PII
- Random 16-digit numbers (fail Luhn) are NOT flagged as credit cards
- Valid IPs (all octets 0-255) are flagged as PII
- Invalid IPs (any octet > 255) are NOT flagged as IP addresses
"""

from __future__ import annotations

import pytest

from syrin.guardrails.built_in.pii import PIIScanner
from syrin.guardrails.context import GuardrailContext


def _make_ctx(text: str) -> GuardrailContext:
    ctx = GuardrailContext.__new__(GuardrailContext)
    object.__setattr__(ctx, "text", text)
    return ctx


class TestCreditCardLuhn:
    def _scanner(self) -> PIIScanner:
        return PIIScanner(allow_types=["email", "phone", "ssn", "ip_address"])

    @pytest.mark.asyncio
    async def test_valid_visa_detected(self) -> None:
        """Real Visa test number passes Luhn — must be flagged."""
        # 4532015112830366 is a well-known Luhn-valid Visa test number
        scanner = self._scanner()
        ctx = _make_ctx("Here is my card: 4532015112830366")
        result = await scanner.evaluate(ctx)
        assert not result.passed, "Luhn-valid CC should be flagged"
        types = {f["type"] for f in result.metadata.get("findings", [])}
        assert "credit_card" in types

    @pytest.mark.asyncio
    async def test_random_16_digits_not_detected(self) -> None:
        """Random 16-digit number that fails Luhn should NOT be flagged as CC."""
        scanner = self._scanner()
        # 1234567890123456 fails the Luhn check
        ctx = _make_ctx("Reference number: 1234567890123456")
        result = await scanner.evaluate(ctx)
        cc_findings = [f for f in result.metadata.get("findings", []) if f["type"] == "credit_card"]
        assert not cc_findings, (
            f"Random 16-digit Luhn-invalid number should not be flagged as CC, got: {cc_findings}"
        )

    @pytest.mark.asyncio
    async def test_valid_mastercard_detected(self) -> None:
        """5500005555555559 is a Luhn-valid Mastercard test number."""
        scanner = self._scanner()
        ctx = _make_ctx("Card: 5500005555555559")
        result = await scanner.evaluate(ctx)
        assert not result.passed
        types = {f["type"] for f in result.metadata.get("findings", [])}
        assert "credit_card" in types

    @pytest.mark.asyncio
    async def test_valid_cc_with_separators_detected(self) -> None:
        """4532-0151-1283-0366 (valid CC with dashes) must be detected."""
        scanner = self._scanner()
        ctx = _make_ctx("Card number: 4532-0151-1283-0366")
        result = await scanner.evaluate(ctx)
        assert not result.passed
        types = {f["type"] for f in result.metadata.get("findings", [])}
        assert "credit_card" in types


class TestIPValidation:
    def _scanner(self) -> PIIScanner:
        return PIIScanner(allow_types=["email", "phone", "ssn", "credit_card"])

    @pytest.mark.asyncio
    async def test_valid_ip_detected(self) -> None:
        """192.168.1.1 is a valid IP — must be flagged."""
        scanner = self._scanner()
        ctx = _make_ctx("Server at 192.168.1.1")
        result = await scanner.evaluate(ctx)
        assert not result.passed
        types = {f["type"] for f in result.metadata.get("findings", [])}
        assert "ip_address" in types

    @pytest.mark.asyncio
    async def test_invalid_ip_not_detected(self) -> None:
        """999.999.999.999 is not a valid IP — should NOT be flagged."""
        scanner = self._scanner()
        ctx = _make_ctx("Value: 999.999.999.999")
        result = await scanner.evaluate(ctx)
        ip_findings = [f for f in result.metadata.get("findings", []) if f["type"] == "ip_address"]
        assert not ip_findings, (
            f"Invalid IP 999.999.999.999 should not be flagged, got: {ip_findings}"
        )

    @pytest.mark.asyncio
    async def test_octet_boundary_valid(self) -> None:
        """255.255.255.0 is valid."""
        scanner = self._scanner()
        ctx = _make_ctx("Subnet: 255.255.255.0")
        result = await scanner.evaluate(ctx)
        types = {f["type"] for f in result.metadata.get("findings", [])}
        assert "ip_address" in types

    @pytest.mark.asyncio
    async def test_octet_just_over_boundary_invalid(self) -> None:
        """256.0.0.1 has invalid first octet."""
        scanner = self._scanner()
        ctx = _make_ctx("Address: 256.0.0.1")
        result = await scanner.evaluate(ctx)
        ip_findings = [f for f in result.metadata.get("findings", []) if f["type"] == "ip_address"]
        assert not ip_findings, "256.0.0.1 is invalid IP, should not be flagged"
