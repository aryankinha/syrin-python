"""Tests for remote config transports: ConfigTransport protocol, SSETransport, PollingTransport, ServeTransport."""

from __future__ import annotations

import json
import time

import httpx

from syrin.remote._transport import (
    ConfigTransport,
    PollingTransport,
    ServeTransport,
    SSETransport,
)
from syrin.remote._types import (
    AgentSchema,
    ConfigOverride,
    ConfigSchema,
    OverridePayload,
    SyncResponse,
)


def _minimal_schema(agent_id: str = "test:Agent") -> AgentSchema:
    """Minimal AgentSchema for transport tests."""
    return AgentSchema(
        agent_id=agent_id,
        agent_name="test",
        class_name="Agent",
        sections={"budget": ConfigSchema(section="budget", class_name="Budget", fields=[])},
        current_values={},
    )


def _override_payload(agent_id: str, version: int = 1) -> OverridePayload:
    """OverridePayload for tests."""
    return OverridePayload(
        agent_id=agent_id,
        version=version,
        overrides=[ConfigOverride(path="budget.max_cost", value=2.0)],
    )


# --- ConfigTransport protocol ---


class TestConfigTransportProtocol:
    """ConfigTransport protocol: register, on_override, stop."""

    def test_serve_transport_implements_protocol(self) -> None:
        """ServeTransport implements ConfigTransport (register, on_override, stop)."""
        t: ConfigTransport = ServeTransport()
        assert hasattr(t, "register")
        assert hasattr(t, "on_override")
        assert hasattr(t, "stop")
        schema = _minimal_schema()
        resp = t.register(schema)
        assert resp is not None
        assert hasattr(resp, "ok")
        t.on_override("id", lambda _: None)
        t.stop()

    def test_protocol_register_returns_sync_response(self) -> None:
        """register(schema) returns SyncResponse-like (ok, initial_overrides, error)."""
        t = ServeTransport()
        schema = _minimal_schema()
        resp = t.register(schema)
        assert hasattr(resp, "ok")
        assert hasattr(resp, "initial_overrides")
        assert hasattr(resp, "error")
        t.stop()


# --- ServeTransport ---


class TestServeTransport:
    """ServeTransport: in-memory; register no-op, on_override stores callback, stop clears."""

    def test_register_returns_ok(self) -> None:
        """ServeTransport.register(schema) returns SyncResponse(ok=True)."""
        t = ServeTransport()
        schema = _minimal_schema()
        resp = t.register(schema)
        assert resp.ok is True
        assert resp.initial_overrides is None
        assert resp.error is None
        t.stop()

    def test_on_override_stores_callback_get_callback_returns_it(self) -> None:
        """on_override(agent_id, callback) then get_callback(agent_id) returns same callback."""
        t = ServeTransport()
        received: list[OverridePayload] = []

        def cb(p: OverridePayload) -> None:
            received.append(p)

        t.on_override("agent1:Agent", cb)
        assert t.get_callback("agent1:Agent") is cb
        payload = _override_payload("agent1:Agent")
        t.get_callback("agent1:Agent")(payload)
        assert len(received) == 1
        assert received[0].agent_id == "agent1:Agent"
        t.stop()

    def test_get_callback_unknown_agent_returns_none(self) -> None:
        """get_callback(unknown agent_id) returns None."""
        t = ServeTransport()
        t.on_override("a:A", lambda _: None)
        assert t.get_callback("other:Agent") is None
        t.stop()

    def test_stop_clears_callbacks(self) -> None:
        """After stop(), get_callback(agent_id) returns None."""
        t = ServeTransport()
        t.on_override("x:X", lambda _: None)
        t.stop()
        assert t.get_callback("x:X") is None

    def test_on_override_replaces_previous_callback(self) -> None:
        """Calling on_override twice for same agent_id replaces callback."""
        t = ServeTransport()
        first: list[int] = []
        second: list[int] = []
        t.on_override("id:A", lambda _: first.append(1))
        t.on_override("id:A", lambda _: second.append(1))
        payload = _override_payload("id:A")
        t.get_callback("id:A")(payload)
        assert len(first) == 0
        assert len(second) == 1
        t.stop()


# --- SSETransport (with mock) ---


class TestSSETransport:
    """SSETransport: register POST, SSE stream, backend down resilience."""

    def test_register_success_returns_sync_response(self) -> None:
        """When mock returns 200 + SyncResponse JSON, register() returns SyncResponse(ok=True)."""
        sync_body = SyncResponse(ok=True, initial_overrides=None, error=None).model_dump_json()

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and "/register" in str(request.url):
                return httpx.Response(200, content=sync_body.encode())
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        t = SSETransport(base_url="https://test.invalid/v1", api_key="sk-test", client=client)
        schema = _minimal_schema("sse_agent:Agent")
        resp = t.register(schema)
        assert resp.ok is True
        t.stop()

    def test_register_backend_down_returns_ok_false(self) -> None:
        """When register POST fails (5xx or connection), returns SyncResponse(ok=False)."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, content=b'{"error": "unavailable"}')

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        t = SSETransport(base_url="https://test.invalid/v1", api_key="sk-test", client=client)
        schema = _minimal_schema()
        resp = t.register(schema)
        assert resp.ok is False
        assert resp.error is not None
        t.stop()

    def test_register_sends_sync_request_body(self) -> None:
        """register() sends POST body with agent_id, schema, library_version."""
        captured: list[bytes] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST" and "/register" in str(request.url):
                captured.append(request.content)
                return httpx.Response(
                    200,
                    content=SyncResponse(ok=True, initial_overrides=None, error=None)
                    .model_dump_json()
                    .encode(),
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        t = SSETransport(base_url="https://test.invalid/v1", api_key=None, client=client)
        schema = _minimal_schema("my_agent:MyAgent")
        t.register(schema)
        assert len(captured) == 1
        body = json.loads(captured[0].decode())
        assert body.get("agent_id") == "my_agent:MyAgent"
        assert "schema" in body
        assert "library_version" in body
        t.stop()

    def test_sse_event_override_invokes_callback(self) -> None:
        """When SSE stream sends event: override and data: OverridePayload JSON, callback is invoked."""
        payload = _override_payload("sse_agent:Agent", version=2)
        payload_json = payload.model_dump_json()
        # SSE format: event line, data line, blank line
        sse_content = f"event: override\ndata: {payload_json}\n\n".encode()

        def handler(request: httpx.Request) -> httpx.Response:
            if "/stream" in str(request.url):
                return httpx.Response(200, content=sse_content)
            if "/register" in str(request.url):
                return httpx.Response(
                    200,
                    content=SyncResponse(ok=True, initial_overrides=None, error=None)
                    .model_dump_json()
                    .encode(),
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        t = SSETransport(base_url="https://test.invalid/v1", api_key="sk-x", client=client)
        received: list[OverridePayload] = []

        def cb(p: OverridePayload) -> None:
            received.append(p)

        schema = _minimal_schema("sse_agent:Agent")
        t.register(schema)
        t.on_override("sse_agent:Agent", cb)
        # Give daemon thread a moment to run
        time.sleep(0.25)
        t.stop()
        assert len(received) >= 1
        assert received[0].agent_id == "sse_agent:Agent"
        assert received[0].version == 2

    def test_sse_stream_disconnect_does_not_crash_stop_succeeds(self) -> None:
        """When SSE stream closes or errors, transport handles it and stop() still works (reconnect loop)."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            if "/register" in str(request.url):
                return httpx.Response(
                    200,
                    content=SyncResponse(ok=True, initial_overrides=None, error=None)
                    .model_dump_json()
                    .encode(),
                )
            if "/stream" in str(request.url):
                call_count += 1
                # First (and only) call: return 200 then "connection" ends when iterator is consumed
                payload = _override_payload("reconnect_agent:Agent").model_dump_json()
                chunk = f"event: override\ndata: {payload}\n\n".encode()
                return httpx.Response(200, content=chunk)
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        t = SSETransport(base_url="https://reconnect.invalid/v1", api_key="sk-x", client=client)
        received: list[OverridePayload] = []
        t.on_override("reconnect_agent:Agent", lambda p: received.append(p))
        time.sleep(0.3)
        t.stop()
        assert call_count >= 1


# --- PollingTransport ---


class TestPollingTransport:
    """PollingTransport: GET overrides, callback invoked, stop() stops loop."""

    def test_polling_invokes_callback_with_payload(self) -> None:
        """When GET returns OverridePayload JSON, callback is invoked."""
        payload = _override_payload("poll_agent:Agent", version=3)
        payload_json = payload.model_dump_json()
        get_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal get_count
            if "overrides" in str(request.url):
                get_count += 1
                return httpx.Response(200, content=payload_json.encode())
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        t = PollingTransport(
            base_url="https://poll.invalid/v1",
            api_key="sk-poll",
            poll_interval=0.1,
            client=client,
        )
        received: list[OverridePayload] = []

        def cb(p: OverridePayload) -> None:
            received.append(p)

        t.on_override("poll_agent:Agent", cb)
        time.sleep(0.35)
        t.stop()
        assert len(received) >= 1
        assert received[0].version == 3
        assert get_count >= 1

    def test_stop_stops_polling(self) -> None:
        """After stop(), no further GETs (callback not called again)."""
        payload = _override_payload("stop_agent:Agent")
        get_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal get_count
            get_count += 1
            return httpx.Response(200, content=payload.model_dump_json().encode())

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        t = PollingTransport(
            base_url="https://stop.invalid/v1",
            poll_interval=0.05,
            client=client,
        )
        received: list[OverridePayload] = []

        def cb(p: OverridePayload) -> None:
            received.append(p)

        t.on_override("stop_agent:Agent", cb)
        time.sleep(0.08)
        t.stop()
        count_after_stop = len(received)
        time.sleep(0.2)
        assert len(received) == count_after_stop

    def test_polling_handles_empty_overrides(self) -> None:
        """GET returning payload with empty overrides still invokes callback."""
        payload = OverridePayload(agent_id="e:Agent", version=0, overrides=[])
        get_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal get_count
            get_count += 1
            return httpx.Response(200, content=payload.model_dump_json().encode())

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        t = PollingTransport(base_url="https://e.invalid/v1", poll_interval=0.1, client=client)
        received: list[OverridePayload] = []

        def cb(p: OverridePayload) -> None:
            received.append(p)

        t.on_override("e:Agent", cb)
        time.sleep(0.25)
        t.stop()
        assert len(received) >= 1
        assert received[0].overrides == []


# --- Edge: stop idempotent ---


class TestTransportStopIdempotent:
    """stop() is idempotent on all transports."""

    def test_serve_transport_stop_twice_no_error(self) -> None:
        t = ServeTransport()
        t.stop()
        t.stop()

    def test_sse_transport_stop_before_register_no_error(self) -> None:
        client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(404)))
        t = SSETransport(base_url="https://x.invalid/v1", client=client)
        t.stop()
