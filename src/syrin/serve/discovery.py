"""Agent Discovery — A2A Agent Card generation and /.well-known/agent.json."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from syrin.agent import Agent


@dataclass
class AgentCardProvider:
    """Provider metadata for Agent Card (organization, url)."""

    organization: str = "Syrin"
    url: str = "https://github.com/Syrin-Labs/syrin-python"


@dataclass
class AgentCardAuth:
    """Authentication metadata for Agent Card."""

    schemes: list[str] = field(default_factory=lambda: ["bearer"])
    oauth_url: str | None = None


@dataclass
class AgentCard:
    """A2A Agent Card — mirrors A2A spec for discovery.

    Use AgentCard.from_agent(agent) to auto-generate from agent metadata.
    Override fields via agent_card = AgentCard(provider=..., authentication=...).
    """

    name: str = ""
    description: str = ""
    url: str = ""
    version: str = "0.4.0"
    provider: AgentCardProvider | None = None
    capabilities: dict[str, Any] = field(
        default_factory=lambda: {"streaming": True, "pushNotifications": False}
    )
    authentication: AgentCardAuth | None = None
    skills: list[dict[str, Any]] = field(default_factory=list)
    default_input_modes: list[str] = field(default_factory=lambda: ["application/json"])
    default_output_modes: list[str] = field(default_factory=lambda: ["application/json"])

    @classmethod
    def from_agent(
        cls,
        agent: Agent,
        *,
        base_url: str = "http://localhost:8000",
        version: str = "0.4.0",
        provider: AgentCardProvider | None = None,
        authentication: AgentCardAuth | None = None,
    ) -> AgentCard:
        """Build Agent Card from agent metadata and tools."""
        tools = getattr(agent, "tools", None) or []
        skills: list[dict[str, Any]] = []
        for t in tools:
            desc = getattr(t, "description", None) or ""
            skills.append(
                {
                    "id": getattr(t, "name", "unknown"),
                    "name": (getattr(t, "name", "unknown") or "unknown").replace("_", " ").title(),
                    "description": desc,
                    "inputModes": ["application/json"],
                    "outputModes": ["application/json"],
                }
            )
        return cls(
            name=getattr(agent, "name", "") or "",
            description=getattr(agent, "description", "") or "",
            url=base_url.rstrip("/"),
            version=version,
            provider=provider or AgentCardProvider(),
            authentication=authentication or AgentCardAuth(),
            skills=skills,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict for /.well-known/agent.json."""
        out: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "provider": (
                {"organization": self.provider.organization, "url": self.provider.url}
                if self.provider
                else {"organization": "Syrin", "url": "https://github.com/Syrin-Labs/syrin-python"}
            ),
            "capabilities": self.capabilities,
            "authentication": (
                {"schemes": self.authentication.schemes}
                | (
                    {"oauth_url": self.authentication.oauth_url}
                    if self.authentication.oauth_url
                    else {}
                )
                if self.authentication
                else {"schemes": ["bearer"]}
            ),
            "skills": self.skills,
            "defaultInputModes": self.default_input_modes,
            "defaultOutputModes": self.default_output_modes,
        }
        return out


def build_agent_card_json(agent: Agent, base_url: str = "http://localhost:8000") -> dict[str, Any]:
    """Build A2A Agent Card JSON from agent. Uses agent.agent_card override for provider/auth if set."""
    base_card = AgentCard.from_agent(agent, base_url=base_url)
    override = getattr(agent.__class__, "agent_card", None)
    if isinstance(override, AgentCard):
        # Merge: override provider, auth, capabilities; base keeps name, description, skills, url
        out = base_card.to_dict()
        if override.provider:
            out["provider"] = {
                "organization": override.provider.organization,
                "url": override.provider.url,
            }
        if override.authentication:
            auth: dict[str, Any] = {"schemes": override.authentication.schemes}
            if override.authentication.oauth_url:
                auth["oauth_url"] = override.authentication.oauth_url
            out["authentication"] = auth
        if override.capabilities:
            out["capabilities"] = {**out.get("capabilities", {}), **override.capabilities}
        return out
    return base_card.to_dict()


def should_enable_discovery(agent: Agent, config: Any) -> bool:
    """Return True if discovery should be enabled (enable_discovery + agent has name)."""
    enable = getattr(config, "enable_discovery", None)
    if enable is False:
        return False
    if enable is True:
        return True
    # None = auto: on when agent has non-empty name
    name = getattr(agent, "name", None)
    return bool(name and isinstance(name, str) and name.strip())
