"""RemoteCommandConfig — options for remote command handling."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RemoteCommandConfig:
    """Configuration for how the control plane processes remote commands.

    Pass an instance to :class:`~syrin.remote_config.RemoteConfig` to
    customise command security and audit behaviour.

    Attributes:
        require_signed_commands: When ``True`` (default), all incoming
            commands must carry a valid Ed25519 signature.  Unsigned commands
            are rejected and logged.
        kill_requires_confirmation: When ``True`` (default), a KILL command
            requires a two-step confirmation to prevent accidental termination.
        audit_all_commands: When ``True`` (default), every command attempt
            (accepted or rejected) is written to the audit trail.

    Example:
        >>> cfg = RemoteCommandConfig(kill_requires_confirmation=False)
        >>> remote = RemoteConfig(url="...", agent_id="x", command_config=cfg)
    """

    require_signed_commands: bool = field(default=True)
    kill_requires_confirmation: bool = field(default=True)
    audit_all_commands: bool = field(default=True)
