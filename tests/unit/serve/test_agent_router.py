"""Tests for AgentRouter — multi-agent HTTP routing."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from starlette.testclient import TestClient

from syrin.agent import Agent
from syrin.model import Model
from syrin.serve import AgentRouter


class _AgentA(Agent):
    name = "agent-a"
    description = "Agent A"
    model = Model.Almock()


class _AgentB(Agent):
    name = "agent-b"
    description = "Agent B"
    model = Model.Almock()


def test_agent_router_requires_at_least_one_agent() -> None:
    """AgentRouter(agents=[]) raises ValueError."""
    with pytest.raises(ValueError, match="at least one agent"):
        AgentRouter(agents=[])


def test_agent_router_requires_unique_names() -> None:
    """AgentRouter with duplicate agent names raises ValueError."""
    a = _AgentA()
    with pytest.raises(ValueError, match="unique"):
        AgentRouter(agents=[a, a])


def test_agent_router_fastapi_router() -> None:
    """AgentRouter.fastapi_router() returns router with per-agent routes."""
    router = AgentRouter(agents=[_AgentA(), _AgentB()])
    r = router.fastapi_router()
    assert r is not None
    assert len(r.routes) >= 12  # 6 per agent


def test_agent_router_routes_per_agent() -> None:
    """Routes are /agent/{name}/chat, /agent/{name}/health, etc."""
    from fastapi import FastAPI

    router = AgentRouter(agents=[_AgentA(), _AgentB()])
    app = FastAPI()
    app.include_router(router.fastapi_router())
    client = TestClient(app)
    r = client.get("/agent/agent-a/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    r2 = client.get("/agent/agent-b/health")
    assert r2.status_code == 200
    assert r2.json() == {"status": "ok"}


def test_agent_router_chat_per_agent() -> None:
    """POST /agent/{name}/chat routes to correct agent."""
    from fastapi import FastAPI

    router = AgentRouter(agents=[_AgentA(), _AgentB()])
    app = FastAPI()
    app.include_router(router.fastapi_router())
    client = TestClient(app)
    r = client.post("/agent/agent-a/chat", json={"message": "Hi"})
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    assert len(data["content"]) > 0


def test_agent_router_with_prefix() -> None:
    """AgentRouter can use custom agent_prefix."""
    from fastapi import FastAPI

    router = AgentRouter(agents=[_AgentA()], agent_prefix="/api/v1/agents")
    app = FastAPI()
    app.include_router(router.fastapi_router())
    client = TestClient(app)
    r = client.get("/api/v1/agents/agent-a/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_agent_router_mount_with_prefix() -> None:
    """Router can be mounted with prefix on existing app."""
    from fastapi import FastAPI

    router = AgentRouter(agents=[_AgentA()])
    app = FastAPI(title="My API")
    app.include_router(router.fastapi_router(), prefix="/api/v1")
    client = TestClient(app)
    r = client.get("/api/v1/agent/agent-a/health")
    assert r.status_code == 200


def test_agent_router_playground_when_enabled() -> None:
    """AgentRouter with enable_playground returns HTML at /playground."""
    from fastapi import FastAPI

    from syrin.serve.config import ServeConfig
    from syrin.serve.playground import add_playground_static_mount

    config = ServeConfig(enable_playground=True)
    router = AgentRouter(agents=[_AgentA(), _AgentB()], config=config)
    app = FastAPI()
    app.include_router(router.fastapi_router())
    add_playground_static_mount(app, "/playground")
    client = TestClient(app)
    r = client.get("/playground")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Syrin Playground" in r.text
    # Config has multiple agents (Next.js renders agent-select client-side)
    cfg = client.get("/playground/config")
    assert cfg.status_code == 200
    assert len(cfg.json()["agents"]) == 2
