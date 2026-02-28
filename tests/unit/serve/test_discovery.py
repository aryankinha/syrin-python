"""Tests for Agent Discovery — Agent Card and /.well-known/agent.json."""

from __future__ import annotations

import pytest

from syrin import Agent
from syrin.serve.config import ServeConfig
from syrin.serve.discovery import (
    build_agent_card_json,
    should_enable_discovery,
)
from syrin.serve.http import build_router


def _almock() -> Agent:
    from syrin.model import Model

    return Agent(model=Model.Almock(), name="test-agent", description="Test agent")


def test_build_agent_card_json_has_required_fields() -> None:
    """Agent Card has name, description, url, version, provider, skills."""
    agent = _almock()
    card = build_agent_card_json(agent, base_url="http://localhost:8000")
    assert card["name"] == "test-agent"
    assert card["description"] == "Test agent"
    assert card["url"] == "http://localhost:8000"
    assert "version" in card
    assert "provider" in card
    assert "skills" in card
    assert "capabilities" in card
    assert "authentication" in card


def test_agent_card_includes_tools_as_skills() -> None:
    """Agent tools become skills in Agent Card."""

    from syrin import tool

    @tool
    def search(query: str) -> str:
        return f"Results: {query}"

    agent = _almock()
    agent._tools = [search]
    card = build_agent_card_json(agent)
    assert len(card["skills"]) == 1
    assert card["skills"][0]["id"] == "search"


def test_should_enable_discovery_true_when_agent_has_name() -> None:
    """enable_discovery auto: on when agent has non-empty name."""
    agent = _almock()
    config = ServeConfig(enable_discovery=None)
    assert should_enable_discovery(agent, config) is True


def test_should_enable_discovery_false_when_disabled() -> None:
    """enable_discovery=False forces off."""
    agent = _almock()
    config = ServeConfig(enable_discovery=False)
    assert should_enable_discovery(agent, config) is False


def test_should_enable_discovery_true_when_explicit() -> None:
    """enable_discovery=True forces on."""
    agent = _almock()
    config = ServeConfig(enable_discovery=True)
    assert should_enable_discovery(agent, config) is True


@pytest.mark.asyncio
async def test_well_known_agent_json_route_when_discovery_on() -> None:
    """GET /.well-known/agent.json returns Agent Card when discovery enabled."""
    agent = _almock()
    config = ServeConfig(enable_discovery=True)
    router = build_router(agent, config)
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.get("/.well-known/agent.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test-agent"
    assert data["description"] == "Test agent"


@pytest.mark.asyncio
async def test_well_known_agent_json_not_added_when_discovery_off() -> None:
    """When enable_discovery=False, GET /.well-known/agent.json returns 404."""
    agent = _almock()
    config = ServeConfig(enable_discovery=False)
    router = build_router(agent, config)
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    resp = client.get("/.well-known/agent.json")
    # Route not registered when discovery off → 404
    assert resp.status_code == 404
