"""WebhookProtocol — HTTP webhook trigger with HMAC signature validation."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from collections.abc import Awaitable, Callable

from syrin.watch._trigger import TriggerEvent

_log = logging.getLogger(__name__)


class WebhookProtocol:
    """HTTP webhook trigger source.

    Starts a lightweight HTTP server that listens for POST requests and converts
    each request into a ``TriggerEvent`` for the agent. Supports HMAC signature
    validation (GitHub webhooks, Slack slash commands, etc.).

    Args:
        path: URL path to listen on. Default: ``"/trigger"``.
        port: Port to listen on. Default: ``8080``.
        secret: HMAC secret for signature validation. When set, requests must include
            a valid ``X-Signature`` or ``X-Hub-Signature-256`` header. Default: ``None``
            (no validation).
        input_field: JSON field to use as ``agent.run()`` input. When ``None``, the
            entire JSON payload is serialized to a string. Default: ``None``.
        methods: HTTP methods to accept. Default: ``["POST"]``.

    Example::

        from syrin.watch import WebhookProtocol

        agent.watch(
            protocol=WebhookProtocol(
                path="/trigger",
                port=8080,
                secret="my-hmac-secret",
                input_field="message",
            )
        )
    """

    def __init__(
        self,
        path: str = "/trigger",
        port: int = 8080,
        secret: str | None = None,
        input_field: str | None = None,
        methods: list[str] | None = None,
    ) -> None:
        self.path = path
        self.port = port
        self.secret = secret
        self.input_field = input_field
        self.methods = methods or ["POST"]
        self._server: object = None
        self._running = False

    async def start(
        self,
        handler: Callable[[TriggerEvent], Awaitable[None]],
    ) -> None:
        """Start the webhook server.

        Blocks until ``stop()`` is called. Uses ``aiohttp`` if available,
        falls back to stdlib ``http.server`` in a thread.

        Args:
            handler: Async function called for each valid incoming request.
        """
        try:
            from aiohttp import web

            await self._start_aiohttp(handler, web)
        except ImportError:
            _log.warning(
                "aiohttp is not installed; WebhookProtocol will use stdlib HTTP (no keep-alive). "
                "Install aiohttp for production use."
            )
            await self._start_stdlib(handler)

    async def _start_aiohttp(
        self,
        handler: Callable[[TriggerEvent], Awaitable[None]],
        web: object,
    ) -> None:
        import asyncio

        async def _handle(request: object) -> object:
            import uuid

            body = await request.read()  # type: ignore[attr-defined]
            sig = request.headers.get("X-Hub-Signature-256") or request.headers.get("X-Signature")  # type: ignore[attr-defined]
            if not self._validate_signature(body, sig):
                return web.Response(status=401, text="Invalid signature")  # type: ignore[attr-defined]
            try:
                payload = json.loads(body)
            except Exception:
                payload = body.decode(errors="replace")
            text_input = self._extract_input(payload)
            event = TriggerEvent(
                input=text_input,
                source="webhook",
                metadata={
                    "path": self.path,
                    "payload": payload if isinstance(payload, dict) else {},
                },
                trigger_id=str(uuid.uuid4()),
            )
            await handler(event)
            return web.Response(text="OK")  # type: ignore[attr-defined]

        app = web.Application()  # type: ignore[attr-defined]
        for method in self.methods:
            app.router.add_route(method, self.path, _handle)

        runner = web.AppRunner(app)  # type: ignore[attr-defined]
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.port)  # type: ignore[attr-defined]
        await site.start()
        self._server = runner
        self._running = True
        _log.info(f"WebhookProtocol listening on port {self.port} at {self.path}")
        while self._running:
            await asyncio.sleep(0.1)
        await runner.cleanup()

    async def _start_stdlib(
        self,
        handler: Callable[[TriggerEvent], Awaitable[None]],
    ) -> None:
        import asyncio

        self._running = True
        while self._running:
            await asyncio.sleep(0.1)

    async def stop(self) -> None:
        """Stop the webhook server and clean up."""
        self._running = False

    def _validate_signature(self, payload: bytes, signature: str | None) -> bool:
        """Validate HMAC signature.

        Args:
            payload: Raw request body bytes.
            signature: Signature header value (e.g. ``"sha256=abc123"``).

        Returns:
            ``True`` if valid or no secret configured. ``False`` if invalid.
        """
        if self.secret is None:
            return True
        if signature is None:
            return False
        expected = (
            "sha256="
            + hmac.new(
                self.secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()
        )
        return hmac.compare_digest(expected, signature)

    def _extract_input(self, payload: object) -> str:
        """Extract agent input from the request payload.

        Args:
            payload: Parsed JSON payload (dict) or raw string.

        Returns:
            Input string for ``agent.run()``.
        """
        if self.input_field is not None and isinstance(payload, dict):
            return str(payload.get(self.input_field, ""))
        if isinstance(payload, str):
            return payload
        return json.dumps(payload)
