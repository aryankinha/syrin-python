"""Tests for agent.serve() top-level method."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from syrin.agent import Agent
from syrin.enums import ServeProtocol
from syrin.model import Model
from syrin.serve.config import ServeConfig


class _TestAgent(Agent):
    name = "test-agent"
    description = "Test agent"
    model = Model.Almock()


def test_serve_with_config() -> None:
    """agent.serve(config=ServeConfig(...)) accepts config."""
    agent = _TestAgent()
    config = ServeConfig(protocol=ServeProtocol.HTTP, port=18999)
    # Don't actually run uvicorn - just verify no import/config error
    # We could run in subprocess and kill, but that's heavy for unit test
    from syrin.agent import _create_fastapi_app

    app = _create_fastapi_app(agent, config)
    assert app is not None
    assert hasattr(app, "routes")


def test_serve_with_kwargs() -> None:
    """agent.serve(port=...) accepts kwargs as ServeConfig."""
    from syrin.agent import _create_fastapi_app

    agent = _TestAgent()
    config = ServeConfig(port=18998, route_prefix="/api")
    app = _create_fastapi_app(agent, config)
    assert app is not None
    # Router has routes with prefix applied
    from starlette.testclient import TestClient

    client = TestClient(app)
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
