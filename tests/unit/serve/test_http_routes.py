"""Tests for HTTP routes (/chat, /stream, /health, /ready, /budget, /describe)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from starlette.testclient import TestClient

from syrin.agent import Agent
from syrin.model import Model
from syrin.serve.config import ServeConfig
from syrin.serve.http import build_router


class _TestAgent(Agent):
    """Test agent using Almock (no real API calls)."""

    name = "test-agent"
    description = "Test agent"
    model = Model.Almock()


def test_build_router_returns_router() -> None:
    """build_router returns a FastAPI APIRouter."""
    agent = _TestAgent()
    config = ServeConfig()
    router = build_router(agent, config)
    assert router is not None
    assert hasattr(router, "routes")


def test_health_returns_ok() -> None:
    """GET /health returns {status: ok}."""
    agent = _TestAgent()
    config = ServeConfig()
    router = build_router(agent, config)
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_returns_ready() -> None:
    """GET /ready returns {ready: true}."""
    agent = _TestAgent()
    config = ServeConfig()
    router = build_router(agent, config)
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"ready": True}


def test_budget_no_budget_returns_404() -> None:
    """GET /budget returns 404 when agent has no budget."""
    agent = _TestAgent()
    config = ServeConfig()
    router = build_router(agent, config)
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/budget")
    assert r.status_code == 404
    assert "error" in r.json()


def test_describe_returns_agent_info() -> None:
    """GET /describe returns name, description, tools."""
    agent = _TestAgent()
    config = ServeConfig()
    router = build_router(agent, config)
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/describe")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "test-agent"
    assert data["description"] == "Test agent"
    assert isinstance(data["tools"], list)
    assert data["budget"] is None


def test_chat_missing_message_returns_400() -> None:
    """POST /chat with empty body returns 400."""
    agent = _TestAgent()
    config = ServeConfig()
    router = build_router(agent, config)
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.post("/chat", json={})
    assert r.status_code == 400


def test_chat_with_message() -> None:
    """POST /chat with message returns content (Almock returns Lorem ipsum)."""
    agent = _TestAgent()
    config = ServeConfig()
    router = build_router(agent, config)
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.post("/chat", json={"message": "Hi"})
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    assert isinstance(data["content"], str)
    assert len(data["content"]) > 0
    assert "cost" in data
    assert "tokens" in data


def test_route_prefix_applied() -> None:
    """route_prefix is applied to all routes."""
    agent = _TestAgent()
    config = ServeConfig(route_prefix="/api/v1")
    router = build_router(agent, config)
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
