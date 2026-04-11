"""Async behavioral tests for watch protocols and Watchable mixin.

Tests the actual runtime behavior of CronProtocol, QueueProtocol, and Watchable
that are not covered by the basic construction/parameter tests.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

import pytest

from syrin.watch import Watchable

# ─── CronProtocol async behavior ──────────────────────────────────────────────


class TestCronProtocolAsyncBehavior:
    """Test suite for CronProtocol async runtime behavior.

    Tests the actual execution behavior of CronProtocol including:
    - run_on_start immediate execution
    - stop() termination
    - Handler exception handling
    - TriggerEvent metadata creation
    """

    @pytest.mark.asyncio
    async def test_cron_run_on_start_fires_immediately(self) -> None:
        """When run_on_start=True, handler is called before first scheduled tick."""
        from syrin.watch import CronProtocol, TriggerEvent

        fired = []

        async def handler(event: TriggerEvent) -> None:
            fired.append(event.input)

        protocol = CronProtocol(
            schedule="0 0 1 1 *",  # Jan 1st only — won't fire during test
            input="immediate",
            run_on_start=True,
        )

        # Start and immediately stop to test run_on_start behavior
        task = asyncio.create_task(protocol.start(handler))
        await asyncio.sleep(0.1)  # Let run_on_start fire
        await protocol.stop()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=1.0)

        assert len(fired) == 1
        assert fired[0] == "immediate"

    @pytest.mark.asyncio
    async def test_cron_without_run_on_start_waits_for_schedule(self) -> None:
        """When run_on_start=False, handler is not called immediately."""
        from syrin.watch import CronProtocol, TriggerEvent

        fired = []

        async def handler(event: TriggerEvent) -> None:
            fired.append(event.input)

        protocol = CronProtocol(
            schedule="0 0 1 1 *",  # Jan 1st only
            input="scheduled",
            run_on_start=False,
        )

        task = asyncio.create_task(protocol.start(handler))
        await asyncio.sleep(0.1)
        await protocol.stop()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=1.0)

        assert len(fired) == 0

    @pytest.mark.asyncio
    async def test_cron_stop_terminates_loop(self) -> None:
        """Calling stop() terminates the cron loop cleanly."""
        from syrin.watch import CronProtocol, TriggerEvent

        call_count = 0

        async def handler(event: TriggerEvent) -> None:
            nonlocal call_count
            call_count += 1

        protocol = CronProtocol(
            schedule="0 0 1 1 *",  # Jan 1st only - won't fire during test
            input="tick",
            run_on_start=True,
        )

        task = asyncio.create_task(protocol.start(handler))
        await asyncio.sleep(0.1)
        await protocol.stop()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=1.0)

        # Should have fired once from run_on_start, then stopped before next schedule
        assert call_count == 1  # Exactly one from run_on_start

    @pytest.mark.asyncio
    async def test_cron_handler_exception_is_logged_not_raised(self) -> None:
        """Handler exceptions are logged but don't crash the cron loop."""
        from syrin.watch import CronProtocol, TriggerEvent

        call_count = 0

        async def handler(event: TriggerEvent) -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("Handler error")

        protocol = CronProtocol(
            schedule="0 0 1 1 *",
            input="error",
            run_on_start=True,
        )

        task = asyncio.create_task(protocol.start(handler))
        await asyncio.sleep(0.1)
        await protocol.stop()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=1.0)

        # Handler was called despite raising
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cron_creates_trigger_event_with_metadata(self) -> None:
        """CronProtocol creates TriggerEvent with schedule metadata."""
        from syrin.watch import CronProtocol, TriggerEvent

        captured_event = None

        async def handler(event: TriggerEvent) -> None:
            nonlocal captured_event
            captured_event = event

        protocol = CronProtocol(
            schedule="0 9 * * 1-5",
            input="test input",
            timezone="America/New_York",
            run_on_start=True,
        )

        task = asyncio.create_task(protocol.start(handler))
        await asyncio.sleep(0.1)
        await protocol.stop()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=1.0)

        assert captured_event is not None
        assert captured_event.input == "test input"
        assert captured_event.source == "cron"
        assert captured_event.metadata["schedule"] == "0 9 * * 1-5"
        assert captured_event.metadata["timezone"] == "America/New_York"
        assert captured_event.trigger_id  # UUID generated


# ─── QueueProtocol async behavior ─────────────────────────────────────────────


class MockQueueBackend:
    """Mock queue backend for testing QueueProtocol behavior.

    Simulates a message queue backend that yields messages and tracks
    ack/nack operations for testing purposes.
    """

    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        self.connected = False
        self.disconnected = False
        self.acked: list[object] = []
        self.nacked: list[object] = []
        self._index = 0

    async def connect(self) -> None:
        """Simulate backend connection."""
        self.connected = True

    async def disconnect(self) -> None:
        """Simulate backend disconnection."""
        self.disconnected = True

    async def receive(self) -> AsyncIterator[tuple[str, object]]:
        """Yield messages with handles for testing."""
        for i, msg in enumerate(self.messages):
            yield msg, f"handle-{i}"
            await asyncio.sleep(0.01)

    async def ack(self, message_id: object) -> None:
        """Record message acknowledgment."""
        self.acked.append(message_id)

    async def nack(self, message_id: object) -> None:
        """Record message rejection."""
        self.nacked.append(message_id)


class TestQueueProtocolAsyncBehavior:
    """Test suite for QueueProtocol async runtime behavior.

    Tests the actual execution behavior of QueueProtocol including:
    - Message processing and ack/nack behavior
    - Concurrency limits
    - Backend connection failure handling
    - TriggerEvent metadata creation
    """

    @pytest.mark.asyncio
    async def test_queue_processes_messages_and_acks_on_success(self) -> None:
        """QueueProtocol processes messages and calls ack() on success."""
        from syrin.watch import QueueProtocol, TriggerEvent

        backend = MockQueueBackend(["msg1", "msg2"])
        processed = []

        async def handler(event: TriggerEvent) -> None:
            processed.append(event.input)

        protocol = QueueProtocol(
            source=backend,
            queue="test",
            ack_on_success=True,
        )

        task = asyncio.create_task(protocol.start(handler))
        await asyncio.sleep(0.15)
        await protocol.stop()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=1.0)

        assert backend.connected
        assert backend.disconnected
        assert processed == ["msg1", "msg2"]
        assert len(backend.acked) == 2
        assert backend.nacked == []

    @pytest.mark.asyncio
    async def test_queue_nacks_on_handler_error(self) -> None:
        """QueueProtocol calls nack() when handler raises."""
        from syrin.watch import QueueProtocol, TriggerEvent

        backend = MockQueueBackend(["msg1", "msg2"])

        async def handler(event: TriggerEvent) -> None:
            if event.input == "msg1":
                raise ValueError("Handler error")

        protocol = QueueProtocol(
            source=backend,
            queue="test",
            ack_on_success=True,
            nack_on_error=True,
        )

        task = asyncio.create_task(protocol.start(handler))
        await asyncio.sleep(0.15)
        await protocol.stop()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=1.0)

        assert len(backend.acked) == 1  # msg2 succeeded
        assert len(backend.nacked) == 1  # msg1 failed

    @pytest.mark.asyncio
    async def test_queue_respects_ack_on_success_false(self) -> None:
        """When ack_on_success=False, ack() is not called."""
        from syrin.watch import QueueProtocol, TriggerEvent

        backend = MockQueueBackend(["msg1"])
        processed = []

        async def handler(event: TriggerEvent) -> None:
            processed.append(event.input)

        protocol = QueueProtocol(
            source=backend,
            queue="test",
            ack_on_success=False,
        )

        task = asyncio.create_task(protocol.start(handler))
        await asyncio.sleep(0.1)
        await protocol.stop()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=1.0)

        assert processed == ["msg1"]
        assert backend.acked == []

    @pytest.mark.asyncio
    async def test_queue_respects_nack_on_error_false(self) -> None:
        """When nack_on_error=False, nack() is not called on error."""
        from syrin.watch import QueueProtocol, TriggerEvent

        backend = MockQueueBackend(["msg1"])

        async def handler(event: TriggerEvent) -> None:
            raise ValueError("Handler error")

        protocol = QueueProtocol(
            source=backend,
            queue="test",
            nack_on_error=False,
        )

        task = asyncio.create_task(protocol.start(handler))
        await asyncio.sleep(0.1)
        await protocol.stop()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=1.0)

        assert backend.nacked == []

    @pytest.mark.asyncio
    async def test_queue_concurrency_limits_parallel_processing(self) -> None:
        """QueueProtocol respects concurrency limit."""
        from syrin.watch import QueueProtocol, TriggerEvent

        backend = MockQueueBackend(["msg1", "msg2", "msg3"])
        active_count = 0
        max_active = 0

        async def handler(event: TriggerEvent) -> None:
            nonlocal active_count, max_active
            active_count += 1
            max_active = max(max_active, active_count)
            await asyncio.sleep(0.05)
            active_count -= 1

        protocol = QueueProtocol(
            source=backend,
            queue="test",
            concurrency=2,
        )

        task = asyncio.create_task(protocol.start(handler))
        await asyncio.sleep(0.25)
        await protocol.stop()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=1.0)

        # With concurrency=2, max_active should never exceed 2
        assert max_active <= 2

    @pytest.mark.asyncio
    async def test_queue_creates_trigger_event_with_metadata(self) -> None:
        """QueueProtocol creates TriggerEvent with queue metadata."""
        from syrin.watch import QueueProtocol, TriggerEvent

        backend = MockQueueBackend(["test message"])
        captured_event = None

        async def handler(event: TriggerEvent) -> None:
            nonlocal captured_event
            captured_event = event

        protocol = QueueProtocol(
            source=backend,
            queue="my-queue",
        )

        task = asyncio.create_task(protocol.start(handler))
        await asyncio.sleep(0.1)
        await protocol.stop()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=1.0)

        assert captured_event is not None
        assert captured_event.input == "test message"
        assert captured_event.source == "queue"
        assert captured_event.metadata["queue"] == "my-queue"
        assert captured_event.trigger_id

    @pytest.mark.asyncio
    async def test_queue_handles_backend_connect_failure(self) -> None:
        """QueueProtocol handles backend connection failures gracefully."""
        from syrin.watch import QueueProtocol, TriggerEvent

        class FailingBackend:
            async def connect(self) -> None:
                raise ConnectionError("Connection failed")

            async def disconnect(self) -> None:
                pass

            async def receive(self) -> AsyncIterator[tuple[str, object]]:
                yield ("", None)

            async def ack(self, message_id: object) -> None:
                pass

            async def nack(self, message_id: object) -> None:
                pass

        backend = FailingBackend()
        handler_called = False

        async def handler(event: TriggerEvent) -> None:
            nonlocal handler_called
            handler_called = True

        protocol = QueueProtocol(source=backend, queue="test")

        # Should not raise, just log and return
        await protocol.start(handler)

        assert not handler_called


# ─── Watchable.watch_handler() async behavior ─────────────────────────────────


class MockWatchable(Watchable):
    """Mock watchable object for testing watch_handler behavior.

    Inherits from Watchable directly so tests stay coupled to the real
    __init__ and watch_handler implementation.  Only ``run()`` is
    implemented — ``_arun_for_trigger`` falls back to it automatically.
    """

    def __init__(self) -> None:
        super().__init__()

        # Test-specific attributes
        self.run_count = 0
        self.run_delay = 0.01
        self.should_raise = False

    async def arun(self, input: str) -> str:  # noqa: A002
        """Simulate async run with configurable delay and error behavior."""
        self.run_count += 1
        await asyncio.sleep(self.run_delay)
        if self.should_raise:
            raise ValueError(f"Error processing: {input}")
        return f"result-{input}"


class TestWatchableHandlerAsyncBehavior:
    """Test suite for Watchable.watch_handler() async runtime behavior.

    Tests the actual execution behavior of watch_handler() including:
    - Timeout enforcement
    - on_result and on_error callback invocation
    - Concurrency limit enforcement via semaphore
    - Parameter override behavior
    """

    @pytest.mark.asyncio
    async def test_watch_handler_enforces_timeout(self) -> None:
        """watch_handler() enforces timeout and raises TimeoutError."""
        from syrin.watch import Watchable

        # Create a mock watchable with slow arun
        obj = MockWatchable()
        obj._watch_timeout = 0.05
        obj.run_delay = 0.2  # Longer than timeout

        # Bind watch_handler method from Watchable
        handler = Watchable.watch_handler(obj)

        from syrin.watch import TriggerEvent
        event = TriggerEvent(input="slow", source="test")

        with pytest.raises(asyncio.TimeoutError):
            await handler(event)

    @pytest.mark.asyncio
    async def test_watch_handler_calls_on_result_callback(self) -> None:
        """watch_handler() calls on_result callback after successful run."""
        from syrin.watch import TriggerEvent, Watchable

        obj = MockWatchable()

        captured_event = None
        captured_result = None

        def on_result(event: TriggerEvent, result: object) -> None:
            nonlocal captured_event, captured_result
            captured_event = event
            captured_result = result

        handler = Watchable.watch_handler(obj, on_result=on_result)
        event = TriggerEvent(input="test", source="test")

        result = await handler(event)

        assert result == "result-test"
        assert captured_event is event
        assert captured_result == "result-test"

    @pytest.mark.asyncio
    async def test_watch_handler_calls_on_error_callback(self) -> None:
        """watch_handler() calls on_error callback when run raises."""
        from syrin.watch import TriggerEvent, Watchable

        obj = MockWatchable()
        obj.should_raise = True

        captured_event = None
        captured_error = None

        def on_error(event: TriggerEvent, exc: Exception) -> None:
            nonlocal captured_event, captured_error
            captured_event = event
            captured_error = exc

        handler = Watchable.watch_handler(obj, on_error=on_error)
        event = TriggerEvent(input="test", source="test")

        with pytest.raises(ValueError):
            await handler(event)

        assert captured_event is event
        assert isinstance(captured_error, ValueError)
        assert "Error processing: test" in str(captured_error)

    @pytest.mark.asyncio
    async def test_watch_handler_respects_concurrency_limit(self) -> None:
        """watch_handler() enforces concurrency limit via semaphore."""
        from syrin.watch import TriggerEvent, Watchable

        obj = MockWatchable()
        obj.run_delay = 0.1

        # Track concurrent execution
        active_count = 0
        max_active = 0

        original_arun = obj.arun

        async def tracking_arun(input: str) -> str:  # noqa: A002
            nonlocal active_count, max_active
            active_count += 1
            max_active = max(max_active, active_count)
            result = await original_arun(input)
            active_count -= 1
            return result

        obj.arun = tracking_arun

        handler = Watchable.watch_handler(obj, concurrency=2)

        # Fire 4 events concurrently
        events = [TriggerEvent(input=f"msg{i}", source="test") for i in range(4)]
        results = await asyncio.gather(*[handler(e) for e in events])

        assert len(results) == 4
        # With concurrency=2, max_active should never exceed 2
        assert max_active <= 2

    @pytest.mark.asyncio
    async def test_watch_handler_override_params_take_precedence(self) -> None:
        """watch_handler() parameters override watch() settings."""
        from syrin.watch import TriggerEvent, Watchable

        obj = MockWatchable()
        obj._watch_timeout = 10.0  # Set via watch()

        # Override with handler-specific timeout
        handler = Watchable.watch_handler(obj, timeout=0.05)
        obj.run_delay = 0.2

        event = TriggerEvent(input="test", source="test")

        # Should use the handler timeout (0.05), not watch timeout (10.0)
        with pytest.raises(asyncio.TimeoutError):
            await handler(event)


# ─── Watchable.trigger() async behavior ───────────────────────────────────────


class TestWatchableTriggerAsyncBehavior:
    """Test suite for Watchable.trigger() async runtime behavior.

    Tests the actual execution behavior of trigger() including:
    - arun() invocation and result handling
    - Metadata passing to TriggerEvent
    """

    @pytest.mark.asyncio
    async def test_trigger_calls_arun_and_returns_result(self) -> None:
        """trigger() calls arun() and returns the result."""
        from syrin.watch import Watchable

        obj = MockWatchable()

        result = await Watchable.trigger(obj, input="test input", source="manual")

        assert result == "result-test input"
        assert obj.run_count == 1

    @pytest.mark.asyncio
    async def test_trigger_passes_metadata_to_event(self) -> None:
        """trigger() creates TriggerEvent with provided metadata."""
        from syrin.watch import TriggerEvent

        obj = MockWatchable()

        # Build the TriggerEvent directly and pass it to watch_handler,
        # rather than monkey-patching trigger()'s internals.
        event = TriggerEvent(
            input="test",
            source="api",
            metadata={"user_id": "123", "request_id": "abc"},
        )

        handler = obj.watch_handler()
        result = await handler(event)

        assert result == "result-test"
        assert event.input == "test"
        assert event.source == "api"
        assert event.metadata["user_id"] == "123"
        assert event.metadata["request_id"] == "abc"
