"""Pluggable transport layer for remote config overrides.

ConfigTransport protocol: register(schema), on_override(agent_id, callback), stop().
Built-in: SSETransport (SaaS), PollingTransport (fallback), ServeTransport (self-hosted routes).
The resolver is transport-agnostic; transports deliver OverridePayload to the callback.
Callbacks may be invoked from a background thread (SSE/polling).
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Protocol

import httpx

from syrin.remote._types import (
    AgentSchema,
    OverridePayload,
    SyncRequest,
    SyncResponse,
)

_log = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.syrin.ai/v1"


def _short_error(status_code: int, text: str | None) -> str:
    """Return a short, log-friendly error string; avoid dumping HTML bodies."""
    if not text or not text.strip():
        return f"HTTP {status_code}"
    s = text.strip()
    if s.upper().startswith("<!DOCTYPE") or s.lower().startswith("<html"):
        # Extract <pre> content if present (e.g. "Cannot POST /path")
        if "<pre>" in s.lower():
            start = s.lower().index("<pre>") + 5
            end = s.lower().index("</pre>", start) if "</pre>" in s.lower() else len(s)
            pre = s[start:end].strip()
            if pre:
                return f"HTTP {status_code}: {pre[:200]}"
        return f"HTTP {status_code}"
    return f"HTTP {status_code}: {(s[:200] + '...') if len(s) > 200 else s}"


_BACKOFF_INITIAL = 1.0
_BACKOFF_MAX = 60.0


def _library_version() -> str:
    try:
        import syrin

        return getattr(syrin, "__version__", "0.6.0")
    except ImportError:
        return "0.6.0"


class ConfigTransport(Protocol):
    """How overrides reach the agent. Pluggable — SSE, serve routes, polling, or custom.

    register() sends schema to the backend (or no-op for local transport).
    on_override() registers a callback that is invoked with OverridePayload when overrides arrive.
    stop() shuts down listeners; idempotent.
    Callbacks may be invoked from a background thread.
    """

    def register(self, schema: AgentSchema) -> SyncResponse: ...
    def on_override(self, agent_id: str, callback: Callable[[OverridePayload], None]) -> None: ...
    def stop(self) -> None: ...


class ServeTransport:
    """In-memory transport for self-hosted config routes.

    register() returns SyncResponse(ok=True). on_override(agent_id, callback) stores
    the callback; route handlers (added in integration) call get_callback(agent_id)(payload).
    No network; used when config is applied via PATCH /agents/{name}/config.
    """

    def __init__(self) -> None:
        self._callbacks: dict[str, Callable[[OverridePayload], None]] = {}
        self._lock = threading.RLock()

    def register(self, schema: AgentSchema) -> SyncResponse:
        """No-op; schema is already in registry. Returns ok=True."""
        return SyncResponse(ok=True, initial_overrides=None, error=None)

    def on_override(self, agent_id: str, callback: Callable[[OverridePayload], None]) -> None:
        """Register callback for this agent_id (replaces any previous)."""
        with self._lock:
            self._callbacks[agent_id] = callback

    def get_callback(self, agent_id: str) -> Callable[[OverridePayload], None] | None:
        """Return the callback for agent_id, or None. Used by PATCH route handler."""
        with self._lock:
            return self._callbacks.get(agent_id)

    def stop(self) -> None:
        """Clear all callbacks. Idempotent."""
        with self._lock:
            self._callbacks.clear()


def _parse_sse_stream(
    stream: httpx.Response,
) -> object:  # Generator[(tuple[str, str], None, None)]
    """Read SSE stream and yield (event, data) for each event. Consumes stream."""
    buffer = b""
    event: str | None = None
    data_lines: list[str] = []
    for chunk in stream.iter_bytes():
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            line_str = line.decode("utf-8", errors="replace").rstrip("\r")
            if line_str == "":
                if event is not None and data_lines:
                    yield event, "\n".join(data_lines)
                event = None
                data_lines = []
                continue
            if line_str.startswith("event:"):
                event = line_str[6:].strip()
            elif line_str.startswith("data:"):
                data_lines.append(line_str[5:].strip())
    if event is not None and data_lines:
        yield event, "\n".join(data_lines)


def _run_sse_loop(
    base_url: str,
    agent_id: str,
    api_key: str | None,
    client: httpx.Client,
    callback: Callable[[OverridePayload], None],
    stopped: threading.Event,
) -> None:
    """Daemon loop: connect to stream, parse SSE, invoke callback on event: override. Reconnect with backoff."""
    backoff = _BACKOFF_INITIAL
    base = base_url.rstrip("/")
    url = f"{base}/agents/{agent_id}/stream"
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    while not stopped.is_set():
        try:
            with client.stream("GET", url, headers=headers, timeout=60.0) as response:
                if response.status_code != 200:
                    _log.warning("SSE stream %s returned %s", url, response.status_code)
                    break
                backoff = _BACKOFF_INITIAL
                for ev, data in _parse_sse_stream(response):  # type: ignore[attr-defined]
                    if stopped.is_set():
                        return
                    if ev == "override" and data:
                        try:
                            payload = OverridePayload.model_validate_json(data)
                            callback(payload)
                        except Exception as e:
                            _log.warning("SSE override parse error: %s", e)
        except Exception as e:
            if stopped.is_set():
                return
            _log.warning("SSE stream error: %s; reconnecting in %.1fs", e, backoff)
        time.sleep(backoff)
        backoff = min(backoff * 2, _BACKOFF_MAX)


class SSETransport:
    """Agent phones home to SaaS API. Register via POST; overrides via SSE stream.

    Uses httpx for POST register and GET stream. Auto-reconnect with exponential backoff (1s–60s).
    Backend down at register: returns SyncResponse(ok=False), no crash.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        api_key: str | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._own_client = client is None
        self._client = client or httpx.Client()
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None
        self._agent_id: str | None = None
        self._callback: Callable[[OverridePayload], None] | None = None

    def register(self, schema: AgentSchema) -> SyncResponse:
        """POST schema to backend; return SyncResponse. On failure return ok=False."""
        url = f"{self._base_url}/agents/{schema.agent_id}/register"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        body = SyncRequest(
            agent_id=schema.agent_id,
            agent_schema=schema,
            library_version=_library_version(),
        ).model_dump(mode="json", by_alias=True)
        try:
            response = self._client.post(url, json=body, headers=headers, timeout=30.0)
            if response.status_code >= 400:
                return SyncResponse(
                    ok=False,
                    initial_overrides=None,
                    error=_short_error(response.status_code, response.text),
                )
            data = response.json()
            return SyncResponse.model_validate(data)
        except Exception as e:
            _log.warning("Register failed: %s", e)
            return SyncResponse(ok=False, initial_overrides=None, error=str(e))

    def on_override(self, agent_id: str, callback: Callable[[OverridePayload], None]) -> None:
        """Start daemon thread that connects to SSE stream and invokes callback. Replaces previous for this agent."""
        self._stopped.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._stopped.clear()
        self._agent_id = agent_id
        self._callback = callback
        self._thread = threading.Thread(
            target=_run_sse_loop,
            args=(self._base_url, agent_id, self._api_key, self._client, callback, self._stopped),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop SSE thread and close client if we own it. Idempotent."""
        self._stopped.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._thread = None
        self._callback = None
        self._agent_id = None
        if self._own_client:
            self._client.close()


def _run_poll_loop(
    base_url: str,
    agent_id: str,
    api_key: str | None,
    poll_interval: float,
    client: httpx.Client,
    callback: Callable[[OverridePayload], None],
    stopped: threading.Event,
) -> None:
    """Daemon loop: GET overrides?since_version=v, parse payload, callback, sleep."""
    base = base_url.rstrip("/")
    last_version = 0
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    while not stopped.is_set():
        try:
            url = f"{base}/agents/{agent_id}/overrides?since_version={last_version}"
            response = client.get(url, headers=headers, timeout=30.0)
            if response.status_code == 200:
                payload = OverridePayload.model_validate_json(response.text)
                callback(payload)
                last_version = payload.version
        except Exception as e:
            _log.debug("Poll overrides error: %s", e)
        for _ in range(int(poll_interval * 10)):
            if stopped.is_set():
                return
            time.sleep(0.1)


class PollingTransport:
    """HTTP polling fallback when SSE is blocked. GET overrides?since_version=v at interval."""

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        api_key: str | None = None,
        poll_interval: float = 30.0,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._poll_interval = max(0.05, poll_interval)
        self._own_client = client is None
        self._client = client or httpx.Client()
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None
        self._agent_id: str | None = None
        self._callback: Callable[[OverridePayload], None] | None = None

    def register(self, schema: AgentSchema) -> SyncResponse:
        """No HTTP register for polling; backend may not require it. Return ok=True."""
        return SyncResponse(ok=True, initial_overrides=None, error=None)

    def on_override(self, agent_id: str, callback: Callable[[OverridePayload], None]) -> None:
        """Start daemon thread that polls overrides and invokes callback. Replaces previous for this agent."""
        self._stopped.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._stopped.clear()
        self._agent_id = agent_id
        self._callback = callback
        self._thread = threading.Thread(
            target=_run_poll_loop,
            args=(
                self._base_url,
                agent_id,
                self._api_key,
                self._poll_interval,
                self._client,
                callback,
                self._stopped,
            ),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop polling thread and close client if we own it. Idempotent."""
        self._stopped.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._thread = None
        self._callback = None
        self._agent_id = None
        if self._own_client:
            self._client.close()
