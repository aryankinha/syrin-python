"""Tests for CLI REPL (ServeProtocol.CLI)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from syrin.agent import Agent
from syrin.enums import ServeProtocol
from syrin.model import Model
from syrin.serve.cli import run_cli_repl
from syrin.serve.config import ServeConfig


class _TestAgent(Agent):
    name = "test-agent"
    description = "Test agent"
    model = Model.Almock()
    system_prompt = "You are helpful."


def test_cli_repl_one_turn_then_exit(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI REPL runs one turn and exits on EOF."""
    agent = _TestAgent()
    config = ServeConfig(protocol=ServeProtocol.CLI)
    with patch("builtins.input", side_effect=["Hi", EOFError]):
        run_cli_repl(agent, config)
    out, err = capsys.readouterr()
    assert "[Syrin] test-agent agent ready" in out
    assert "Cost:" in out or "Tokens:" in out
    assert "Bye." in out


def test_cli_repl_empty_input_skipped(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI REPL skips empty input and continues."""
    agent = _TestAgent()
    config = ServeConfig()
    with patch("builtins.input", side_effect=["", "", "Hello", EOFError]):
        run_cli_repl(agent, config)
    out, _ = capsys.readouterr()
    assert "Hello" in out or "Cost:" in out  # Agent ran on "Hello"
    assert "Bye." in out


def test_agent_serve_cli_runs_repl(capsys: pytest.CaptureFixture[str]) -> None:
    """agent.serve(protocol=CLI) runs the REPL."""
    agent = _TestAgent()
    with patch("builtins.input", side_effect=["Test", EOFError]):
        agent.serve(protocol=ServeProtocol.CLI)
    out, _ = capsys.readouterr()
    assert "[Syrin]" in out
    assert "Bye." in out
