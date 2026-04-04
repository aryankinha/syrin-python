"""Tests for RemoteCommand and CommandProcessor (P8-T4)."""

from __future__ import annotations

import time

import pytest

from syrin.enums import Hook
from syrin.remote._command import (
    CommandAuditEntry,
    CommandProcessor,
    CommandResult,
    RemoteCommand,
)


class TestRemoteCommandEnum:
    def test_remote_command_is_strenum(self) -> None:
        from enum import StrEnum

        assert issubclass(RemoteCommand, StrEnum)

    def test_has_required_values(self) -> None:
        assert RemoteCommand.PAUSE == "pause"
        assert RemoteCommand.RESUME == "resume"
        assert RemoteCommand.KILL == "kill"
        assert RemoteCommand.ROLLBACK == "rollback"
        assert RemoteCommand.UPDATE_CONFIG == "update_config"


class TestCommandProcessorInit:
    def test_constructs_without_error(self) -> None:
        processor = CommandProcessor(agent_id="agent-1")
        assert processor is not None

    def test_initial_status_is_running(self) -> None:
        processor = CommandProcessor(agent_id="agent-1")
        assert processor.status == "running"


class TestCommandProcessorPauseResume:
    def test_pause_returns_success(self) -> None:
        processor = CommandProcessor(agent_id="agent-1")
        result = processor.execute(RemoteCommand.PAUSE)
        assert isinstance(result, CommandResult)
        assert result.success is True

    def test_pause_sets_status_paused(self) -> None:
        processor = CommandProcessor(agent_id="agent-1")
        processor.execute(RemoteCommand.PAUSE)
        assert processor.status == "paused"

    def test_resume_when_paused_sets_status_running(self) -> None:
        processor = CommandProcessor(agent_id="agent-1")
        processor.execute(RemoteCommand.PAUSE)
        processor.execute(RemoteCommand.RESUME)
        assert processor.status == "running"


class TestCommandProcessorKill:
    def test_kill_sets_status_killed(self) -> None:
        processor = CommandProcessor(agent_id="agent-1")
        result = processor.execute(RemoteCommand.KILL)
        assert result.success is True
        assert processor.status == "killed"


class TestCommandProcessorKillWithConfirmation:
    def test_first_kill_does_not_kill_immediately(self) -> None:
        processor = CommandProcessor(agent_id="agent-1", kill_requires_confirmation=True)
        result = processor.execute(RemoteCommand.KILL)
        assert processor.status != "killed"
        # first KILL arms but does not execute
        assert result.success is False or processor.status == "running"

    def test_second_kill_within_window_completes_kill(self) -> None:
        processor = CommandProcessor(
            agent_id="agent-1",
            kill_requires_confirmation=True,
            confirmation_window_seconds=30.0,
        )
        processor.execute(RemoteCommand.KILL)
        result = processor.execute(RemoteCommand.KILL)
        assert result.success is True
        assert processor.status == "killed"

    def test_kill_after_window_expires_rearms(self) -> None:
        processor = CommandProcessor(
            agent_id="agent-1",
            kill_requires_confirmation=True,
            confirmation_window_seconds=0.0,  # immediate expiry
        )
        processor.execute(RemoteCommand.KILL)
        # Force window to expire
        time.sleep(0.01)
        # Next KILL should re-arm (not kill)
        processor.execute(RemoteCommand.KILL)
        assert processor.status != "killed"


class TestCommandProcessorSignedCommands:
    def test_unsigned_command_rejected_when_require_signed(self) -> None:
        fired: list[tuple[Hook, dict[str, object]]] = []

        def fn(hook: Hook, payload: dict[str, object]) -> None:
            fired.append((hook, payload))

        processor = CommandProcessor(
            agent_id="agent-1",
            require_signed_commands=True,
            fire_fn=fn,
        )
        result = processor.execute(RemoteCommand.PAUSE)
        assert result.success is False
        assert result.reason == "unsigned"
        assert any(h == Hook.COMMAND_REJECTED for h, _ in fired)

    def test_signed_command_with_valid_identity_executes(self) -> None:
        fired: list[tuple[Hook, dict[str, object]]] = []

        def fn(hook: Hook, payload: dict[str, object]) -> None:
            fired.append((hook, payload))

        try:
            from syrin.security.identity import AgentIdentity

            identity = AgentIdentity.generate()
            processor = CommandProcessor(
                agent_id="agent-1",
                require_signed_commands=True,
                fire_fn=fn,
            )
            message = RemoteCommand.PAUSE.encode()
            sig = identity.sign(message)
            result = processor.execute(
                RemoteCommand.PAUSE,
                signature=sig,
                public_key=identity.public_key_bytes,
            )
            assert result.success is True
            assert any(h == Hook.COMMAND_EXECUTED for h, _ in fired)
        except ImportError:
            pytest.skip("cryptography package not available")


class TestCommandProcessorAuditLog:
    def test_executed_commands_appear_in_audit_log(self) -> None:
        processor = CommandProcessor(agent_id="agent-1")
        processor.execute(RemoteCommand.PAUSE, actor_id="admin")
        processor.execute(RemoteCommand.RESUME, actor_id="admin")
        log = processor.audit_log()
        assert len(log) == 2

    def test_audit_entry_has_required_fields(self) -> None:
        processor = CommandProcessor(agent_id="agent-1")
        processor.execute(RemoteCommand.PAUSE, actor_id="admin-1")
        log = processor.audit_log()
        entry = log[0]
        assert isinstance(entry, CommandAuditEntry)
        assert entry.command == RemoteCommand.PAUSE
        assert isinstance(entry.timestamp, str)
        assert entry.actor_id == "admin-1"
        assert isinstance(entry.success, bool)
        assert isinstance(entry.reason, str)


class TestCommandProcessorIsolation:
    def test_two_processors_are_independent(self) -> None:
        p1 = CommandProcessor(agent_id="agent-1")
        p2 = CommandProcessor(agent_id="agent-2")
        p1.execute(RemoteCommand.PAUSE)
        assert p1.status == "paused"
        assert p2.status == "running"

    def test_audit_logs_are_independent(self) -> None:
        p1 = CommandProcessor(agent_id="agent-1")
        p2 = CommandProcessor(agent_id="agent-2")
        p1.execute(RemoteCommand.PAUSE)
        assert len(p1.audit_log()) == 1
        assert len(p2.audit_log()) == 0
