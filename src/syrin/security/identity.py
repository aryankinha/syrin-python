"""AgentIdentity — Ed25519 cryptographic identity for agents."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    _CRYPTOGRAPHY_AVAILABLE = True
except ImportError:  # pragma: no cover
    _CRYPTOGRAPHY_AVAILABLE = False

from syrin.enums import Hook


@dataclass
class AgentIdentity:
    """Cryptographic identity for an agent using Ed25519 keys.

    Use ``AgentIdentity.generate()`` to create a new identity with a fresh keypair.
    Private key material is **never** included in ``repr()``, ``str()``, or ``to_dict()``.

    Attributes:
        agent_id: Unique identifier for this agent (UUID format).
        public_key_bytes: The Ed25519 public key (32 bytes).

    Example:
        >>> identity = AgentIdentity.generate()
        >>> sig = identity.sign(b"hello")
        >>> assert AgentIdentity.verify(b"hello", sig, identity.public_key_bytes)
    """

    agent_id: str
    public_key_bytes: bytes
    _private_key: object = field(repr=False, compare=False)

    def __repr__(self) -> str:
        """Return safe repr that never exposes private key material."""
        return (
            f"AgentIdentity(agent_id={self.agent_id!r}, "
            f"public_key_bytes=<{len(self.public_key_bytes)} bytes>)"
        )

    def __str__(self) -> str:
        """Return safe string that never exposes private key material."""
        return self.__repr__()

    @classmethod
    def generate(
        cls,
        agent_id: str | None = None,
        _fire_event_fn: Callable[[Hook, dict[str, object]], None] | None = None,
    ) -> AgentIdentity:
        """Generate a new AgentIdentity with a fresh Ed25519 keypair.

        Args:
            agent_id: Optional custom agent identifier. Defaults to a new UUID.
            _fire_event_fn: Optional hook firing callback (reserved for future use).

        Returns:
            A new AgentIdentity with a unique keypair.

        Raises:
            ImportError: If the ``cryptography`` package is not installed.
        """
        if not _CRYPTOGRAPHY_AVAILABLE:
            raise ImportError(  # pragma: no cover
                "Install syrin[security]: pip install cryptography"
            )

        private_key: Ed25519PrivateKey = Ed25519PrivateKey.generate()
        public_key: Ed25519PublicKey = private_key.public_key()
        pub_bytes = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)

        return cls(
            agent_id=agent_id or str(uuid.uuid4()),
            public_key_bytes=pub_bytes,
            _private_key=private_key,
        )

    def sign(self, message: bytes) -> bytes:
        """Sign a message with this identity's private key.

        Ed25519 signing is deterministic — the same key and message always
        produce the same signature.

        Args:
            message: Raw bytes to sign.

        Returns:
            64-byte Ed25519 signature.

        Raises:
            ImportError: If the ``cryptography`` package is not installed.
        """
        if not _CRYPTOGRAPHY_AVAILABLE:
            raise ImportError(  # pragma: no cover
                "Install syrin[security]: pip install cryptography"
            )
        private_key: Ed25519PrivateKey = self._private_key  # type: ignore[assignment]
        return private_key.sign(message)

    @staticmethod
    def verify(
        message: bytes,
        signature: bytes,
        public_key: bytes,
        fire_event_fn: Callable[[Hook, dict[str, object]], None] | None = None,
    ) -> bool:
        """Verify a message signature against a public key.

        Fires ``Hook.IDENTITY_VERIFIED`` on success or ``Hook.SIGNATURE_INVALID``
        on failure.

        Args:
            message: The original message bytes.
            signature: The 64-byte Ed25519 signature to verify.
            public_key: The 32-byte Ed25519 public key bytes.
            fire_event_fn: Optional hook firing callback.

        Returns:
            True if signature is valid for message under the given public key.

        Raises:
            ImportError: If the ``cryptography`` package is not installed.
        """
        if not _CRYPTOGRAPHY_AVAILABLE:
            raise ImportError(  # pragma: no cover
                "Install syrin[security]: pip install cryptography"
            )

        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        try:
            pub_key_obj = Ed25519PublicKey.from_public_bytes(public_key)
            pub_key_obj.verify(signature, message)
            if fire_event_fn is not None:
                fire_event_fn(
                    Hook.IDENTITY_VERIFIED,
                    {"agent_public_key_size": len(public_key)},
                )
            return True
        except (InvalidSignature, Exception):
            if fire_event_fn is not None:
                fire_event_fn(
                    Hook.SIGNATURE_INVALID,
                    {"reason": "Signature verification failed"},
                )
            return False

    def to_dict(self) -> dict[str, str]:
        """Serialize identity to a dict (public key only — private key excluded).

        Returns:
            Dictionary with ``agent_id`` and ``public_key_bytes`` (hex-encoded).
            Private key is **never** included.
        """
        return {
            "agent_id": self.agent_id,
            "public_key_bytes": self.public_key_bytes.hex(),
        }
