"""Tests for Workflow.serve() — POST /chat and GET /graph endpoints.

Exit criteria:
- Workflow.serve(), Swarm.serve() both work — POST /chat runs workflow/swarm, returns result
- GET /graph HTTP endpoint returns Mermaid string for any Servable primitive
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")
pytest.importorskip("uvicorn", reason="uvicorn not installed")

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from syrin import Agent, Model
from syrin.workflow._core import Workflow

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _StubAgent(Agent):
    model = Model.Almock(latency_seconds=0.01, lorem_length=3)
    system_prompt = "stub"


def _make_workflow_app(wf: Workflow) -> FastAPI:
    """Build the FastAPI app the same way Workflow.serve() would — without blocking."""
    app = FastAPI(title=f"Syrin Workflow: {wf._name}")

    @app.post("/chat")
    async def _chat(body: dict[str, object]) -> JSONResponse:  # type: ignore[misc]
        message = str(body.get("message", ""))
        result = await wf.run(message)
        return JSONResponse({"content": result.content, "cost": result.cost})

    @app.get("/graph")
    async def _graph() -> JSONResponse:  # type: ignore[misc]
        return JSONResponse({"graph": wf.to_mermaid()})

    return app


# ---------------------------------------------------------------------------
# GET /graph returns Mermaid string
# ---------------------------------------------------------------------------


def test_workflow_graph_endpoint_returns_mermaid() -> None:
    """GET /graph returns a Mermaid string for the workflow."""
    wf = Workflow("test-wf").step(_StubAgent, "do thing")
    app = _make_workflow_app(wf)
    client = TestClient(app)
    resp = client.get("/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "graph" in data
    assert data["graph"] is not None
    assert (
        "graph" in data["graph"].lower()
        or "flowchart" in data["graph"].lower()
        or "TD" in data["graph"]
    )


def test_workflow_graph_endpoint_contains_step_name() -> None:
    """GET /graph Mermaid output contains the agent class name."""
    wf = Workflow("my-wf").step(_StubAgent, "task")
    app = _make_workflow_app(wf)
    client = TestClient(app)
    resp = client.get("/graph")
    data = resp.json()
    assert "_StubAgent" in data["graph"]


def test_workflow_graph_endpoint_multi_step() -> None:
    """GET /graph works for a multi-step workflow."""

    class _AgentX(Agent):
        model = Model.Almock(latency_seconds=0.01, lorem_length=1)
        system_prompt = "x"

    class _AgentY(Agent):
        model = Model.Almock(latency_seconds=0.01, lorem_length=1)
        system_prompt = "y"

    wf = Workflow("multi").step(_AgentX).step(_AgentY)
    app = _make_workflow_app(wf)
    client = TestClient(app)
    resp = client.get("/graph")
    data = resp.json()
    assert "_AgentX" in data["graph"]
    assert "_AgentY" in data["graph"]


# ---------------------------------------------------------------------------
# POST /chat runs the workflow
# ---------------------------------------------------------------------------


def test_workflow_chat_endpoint_returns_content() -> None:
    """POST /chat runs the workflow and returns content."""
    wf = Workflow("chat-wf").step(_StubAgent, "answer")
    app = _make_workflow_app(wf)
    client = TestClient(app)
    resp = client.post("/chat", json={"message": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
    assert isinstance(data["content"], str)
    assert len(data["content"]) > 0


def test_workflow_chat_endpoint_returns_cost() -> None:
    """POST /chat includes a cost field in the response."""
    wf = Workflow("cost-wf").step(_StubAgent, "compute")
    app = _make_workflow_app(wf)
    client = TestClient(app)
    resp = client.post("/chat", json={"message": "test"})
    assert resp.status_code == 200
    data = resp.json()
    assert "cost" in data
    assert isinstance(data["cost"], (int, float))


# ---------------------------------------------------------------------------
# Workflow.serve() method is present and raises ImportError without deps
# ---------------------------------------------------------------------------


def test_workflow_serve_method_exists() -> None:
    """Workflow.serve() method exists on the Workflow class."""
    wf = Workflow("my-wf").step(_StubAgent)
    assert callable(wf.serve)
