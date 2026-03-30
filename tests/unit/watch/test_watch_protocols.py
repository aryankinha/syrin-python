"""Tests for WebhookProtocol, CronProtocol, and QueueProtocol: construction, default params,
HMAC signature validation, input extraction, and cron scheduling."""

from __future__ import annotations

import pytest

# ─── WebhookProtocol ──────────────────────────────────────────────────────────


class TestWebhookProtocol:
    def test_importable(self) -> None:
        from syrin.watch import WebhookProtocol

        assert WebhookProtocol is not None

    def test_has_start_and_stop(self) -> None:
        from syrin.watch import WebhookProtocol

        assert hasattr(WebhookProtocol, "start")
        assert hasattr(WebhookProtocol, "stop")

    def test_default_params(self) -> None:
        from syrin.watch import WebhookProtocol

        p = WebhookProtocol()
        assert p.path == "/trigger"
        assert p.port == 8080
        assert p.secret is None
        assert p.input_field is None
        assert p.methods == ["POST"]

    def test_custom_params(self) -> None:
        from syrin.watch import WebhookProtocol

        p = WebhookProtocol(path="/webhook", port=9090, secret="abc", input_field="msg")
        assert p.path == "/webhook"
        assert p.port == 9090
        assert p.secret == "abc"
        assert p.input_field == "msg"

    def test_hmac_validate_accepts_no_secret(self) -> None:
        from syrin.watch import WebhookProtocol

        p = WebhookProtocol(secret=None)
        # When no secret, validation should pass (no signature to check)
        assert p._validate_signature(b"payload", None) is True

    def test_hmac_validate_rejects_bad_signature(self) -> None:
        from syrin.watch import WebhookProtocol

        p = WebhookProtocol(secret="mysecret")
        assert p._validate_signature(b"payload", "sha256=bad") is False

    def test_hmac_validate_accepts_good_signature(self) -> None:
        import hashlib
        import hmac

        from syrin.watch import WebhookProtocol

        secret = "mysecret"
        payload = b'{"msg": "hello"}'
        sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        p = WebhookProtocol(secret=secret)
        assert p._validate_signature(payload, sig) is True

    def test_extract_input_from_field(self) -> None:
        from syrin.watch import WebhookProtocol

        p = WebhookProtocol(input_field="message")
        payload = {"message": "run the report", "other": "ignored"}
        assert p._extract_input(payload) == "run the report"

    def test_extract_input_serializes_whole_payload(self) -> None:
        from syrin.watch import WebhookProtocol

        p = WebhookProtocol(input_field=None)
        payload = {"key": "value"}
        result = p._extract_input(payload)
        assert "key" in result
        assert "value" in result


# ─── CronProtocol ─────────────────────────────────────────────────────────────


class TestCronProtocol:
    def test_importable(self) -> None:
        from syrin.watch import CronProtocol

        assert CronProtocol is not None

    def test_has_start_and_stop(self) -> None:
        from syrin.watch import CronProtocol

        assert hasattr(CronProtocol, "start")
        assert hasattr(CronProtocol, "stop")

    def test_default_params(self) -> None:
        from syrin.watch import CronProtocol

        p = CronProtocol(schedule="0 * * * *")
        assert p.schedule == "0 * * * *"
        assert p.input == ""
        assert p.timezone == "UTC"
        assert p.run_on_start is False

    def test_custom_params(self) -> None:
        from syrin.watch import CronProtocol

        p = CronProtocol(
            schedule="0 9 * * 1-5",
            input="Run daily report",
            timezone="America/New_York",
            run_on_start=True,
        )
        assert p.schedule == "0 9 * * 1-5"
        assert p.input == "Run daily report"
        assert p.timezone == "America/New_York"
        assert p.run_on_start is True

    def test_next_run_time_returns_float(self) -> None:
        from syrin.watch import CronProtocol

        p = CronProtocol(schedule="* * * * *")  # every minute
        next_run = p.next_run_time()
        assert isinstance(next_run, float)
        assert next_run > 0

    def test_invalid_schedule_raises(self) -> None:
        from syrin.watch import CronProtocol

        with pytest.raises((ValueError, Exception)):
            p = CronProtocol(schedule="not a valid cron")
            p.next_run_time()  # may fail here


# ─── QueueProtocol ────────────────────────────────────────────────────────────


class TestQueueProtocol:
    def test_importable(self) -> None:
        from syrin.watch import QueueProtocol

        assert QueueProtocol is not None

    def test_has_start_and_stop(self) -> None:
        from syrin.watch import QueueProtocol

        assert hasattr(QueueProtocol, "start")
        assert hasattr(QueueProtocol, "stop")

    def test_default_params(self) -> None:
        from syrin.watch import QueueProtocol

        p = QueueProtocol(source="redis://localhost:6379/0", queue="tasks")
        assert p.source == "redis://localhost:6379/0"
        assert p.queue == "tasks"
        assert p.concurrency == 1
        assert p.ack_on_success is True
        assert p.nack_on_error is True

    def test_custom_params(self) -> None:
        from syrin.watch import QueueProtocol

        p = QueueProtocol(
            source="redis://localhost:6379/0",
            queue="tasks",
            concurrency=3,
            ack_on_success=False,
            nack_on_error=False,
        )
        assert p.concurrency == 3
        assert p.ack_on_success is False
        assert p.nack_on_error is False

    def test_queue_backend_protocol_importable(self) -> None:
        from syrin.watch import QueueBackend

        assert QueueBackend is not None
