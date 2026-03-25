"""Agent Discovery — A2A Agent Card generation and /.well-known/agent-card.json."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# A2A Agent Card path — https://{agent-server-domain}/.well-known/agent-card.json
AGENT_CARD_PATH = "/.well-known/agent-card.json"

if TYPE_CHECKING:
    from syrin.agent import Agent


@dataclass
class AgentCardProvider:
    """Provider metadata for Agent Card (organization, url).

    Attributes:
        organization: Organization name.
        url: Organization URL.
    """

    organization: str = "Syrin"
    url: str = "https://github.com/Syrin-Labs/syrin-python"


@dataclass
class AgentCardAuth:
    """Authentication metadata for Agent Card.

    Attributes:
        schemes: Auth schemes (e.g. bearer).
        oauth_url: OAuth URL if applicable.
    """

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
    capabilities: dict[str, object] = field(
        default_factory=lambda: {"streaming": True, "pushNotifications": False}
    )
    authentication: AgentCardAuth | None = None
    skills: list[dict[str, object]] = field(default_factory=list)
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
        skills: list[dict[str, object]] = []
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

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-serializable dict for /.well-known/agent-card.json."""
        out: dict[str, object] = {
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


def build_agent_card_json(
    agent: Agent, base_url: str = "http://localhost:8000"
) -> dict[str, object]:
    """Build A2A Agent Card JSON from agent for /.well-known/agent-card.json.

    Uses AgentCard.from_agent(); if agent has agent_card class attr, merges overrides.
    Auto-populates name, description, url, skills from tools.

    Args:
        agent: Agent to build card for.
        base_url: Base URL for the agent (default localhost:8000).

    Returns:
        JSON-serializable dict for /.well-known/agent-card.json.
    """
    base_card = AgentCard.from_agent(agent, base_url=base_url)
    override = getattr(agent.__class__, "agent_card", None)
    if not isinstance(override, AgentCard):
        return base_card.to_dict()
    out = base_card.to_dict()
    if override.name:
        out["name"] = override.name
    if override.description:
        out["description"] = override.description
    if override.url:
        out["url"] = override.url
    if override.version:
        out["version"] = override.version
    if override.skills:
        out["skills"] = override.skills
    if override.provider:
        out["provider"] = {
            "organization": override.provider.organization,
            "url": override.provider.url,
        }
    if override.authentication:
        auth: dict[str, object] = {"schemes": override.authentication.schemes}
        if override.authentication.oauth_url:
            auth["oauth_url"] = override.authentication.oauth_url
        out["authentication"] = auth
    if override.capabilities:
        out["capabilities"] = {**out.get("capabilities", {}), **override.capabilities}  # type: ignore[dict-item]
    if override.default_input_modes:
        out["defaultInputModes"] = override.default_input_modes
    if override.default_output_modes:
        out["defaultOutputModes"] = override.default_output_modes
    return out


def should_enable_discovery(agent: Agent, config: object) -> bool:
    """Return True if discovery (/.well-known/agent-card.json) should be enabled.

    True when config.enable_discovery is True, or when None (auto) and agent has name.
    False when config.enable_discovery is False.
    """
    enable = getattr(config, "enable_discovery", None)
    if enable is False:
        return False
    if enable is True:
        return True
    # None = auto: on when agent has non-empty name
    name = getattr(agent, "name", None)
    return bool(name and isinstance(name, str) and name.strip())
