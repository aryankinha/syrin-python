"""Tests for ServeProtocol enum."""

from __future__ import annotations

from syrin.enums import ServeProtocol


def test_serve_protocol_values() -> None:
    """ServeProtocol has CLI, HTTP, STDIO."""
    assert ServeProtocol.CLI == "cli"
    assert ServeProtocol.HTTP == "http"
    assert ServeProtocol.STDIO == "stdio"


def test_serve_protocol_is_strenum() -> None:
    """ServeProtocol values are strings."""
    assert isinstance(ServeProtocol.CLI.value, str)
    assert isinstance(ServeProtocol.HTTP.value, str)
    assert isinstance(ServeProtocol.STDIO.value, str)


def test_serve_protocol_members() -> None:
    """ServeProtocol has exactly 3 members."""
    members = list(ServeProtocol)
    assert len(members) == 3
    assert ServeProtocol.CLI in members
    assert ServeProtocol.HTTP in members
    assert ServeProtocol.STDIO in members
