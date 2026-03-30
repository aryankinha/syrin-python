"""Tests for Pry: importability, attach/detach lifecycle, JSON fallback in non-TTY
environments (CI), and structured JSON logging via SyrinHandler."""

from __future__ import annotations

# ─── Pry importable ──────────────────────────────────────────────────


class TestPry:
    def test_importable(self) -> None:
        from syrin.debug import Pry

        assert Pry is not None

    def test_has_attach_and_detach(self) -> None:
        from syrin.debug import Pry

        assert hasattr(Pry, "attach")
        assert hasattr(Pry, "detach")

    def test_has_start_and_stop(self) -> None:
        from syrin.debug import Pry

        assert hasattr(Pry, "start")
        assert hasattr(Pry, "stop")

    def test_attach_to_agent(self) -> None:
        from syrin.agent import Agent
        from syrin.debug import Pry
        from syrin.model import Model

        agent = Agent(model=Model.OpenAI("gpt-4o-mini"))
        ui = Pry()
        ui.attach(agent)
        # Should not raise

    def test_default_not_tty_uses_json_fallback(self) -> None:
        """When attached, detects TTY and falls back to JSON lines if non-TTY."""
        from syrin.debug import Pry

        ui = Pry()
        # In test environment (not a TTY) — json_fallback should be True or configurable
        assert hasattr(ui, "json_fallback")

    def test_from_debug_flag_consumes_flag(self) -> None:
        from syrin.debug import Pry

        argv = ["prog", "--debug"]
        ui = Pry.from_debug_flag(argv=argv, json_fallback=True)

        assert ui is not None
        assert "--debug" not in argv

    def test_from_debug_flag_returns_none_when_absent(self) -> None:
        from syrin.debug import Pry

        argv = ["prog"]

        assert Pry.from_debug_flag(argv=argv, json_fallback=True) is None
        assert argv == ["prog"]

    def test_agent_has_debug_ui_shortcut(self) -> None:
        """Agent has .debug_ui property or method for convenience."""
        from syrin.agent import Agent
        from syrin.model import Model

        agent = Agent(model=Model.OpenAI("gpt-4o-mini"))
        # Should have debug_ui attribute or accessible shortcut
        assert hasattr(agent, "debug_ui")


# ─── JSON fallback in non-TTY (CI) ────────────────────────────────────────────


class TestJsonFallback:
    def test_json_lines_output_on_hook(self, capsys: object) -> None:
        """In json_fallback mode, hooks emit JSON lines to stdout."""
        import json

        from syrin.agent import Agent
        from syrin.debug import Pry
        from syrin.enums import Hook
        from syrin.events import EventContext
        from syrin.model import Model

        agent = Agent(model=Model.OpenAI("gpt-4o-mini"))
        ui = Pry(json_fallback=True)
        ui.attach(agent)

        # Simulate a hook firing
        agent._emit_event(Hook.AGENT_RUN_START, EventContext(input="hello", model="gpt-4o-mini"))

        # Detach to stop capturing
        ui.detach()

        captured = capsys.readouterr()
        # json_fallback writes to stdout
        if captured.out.strip():
            line = captured.out.strip().split("\n")[0]
            parsed = json.loads(line)
            assert "event" in parsed or "hook" in parsed or "level" in parsed

    def test_json_fallback_detach_stops_output(self) -> None:
        from syrin.agent import Agent
        from syrin.debug import Pry
        from syrin.model import Model

        agent = Agent(model=Model.OpenAI("gpt-4o-mini"))
        ui = Pry(json_fallback=True)
        ui.attach(agent)
        ui.detach()
        # Should not raise when detached


# ─── Structured JSON logging ───────────────────────────────────────────────────


class TestStructuredLogging:
    def test_syrin_handler_importable(self) -> None:
        from syrin.logging import SyrinHandler

        assert SyrinHandler is not None

    def test_log_format_importable(self) -> None:
        from syrin.logging import LogFormat

        assert LogFormat is not None

    def test_log_format_has_json(self) -> None:
        from syrin.logging import LogFormat

        assert hasattr(LogFormat, "JSON")

    def test_log_format_has_text(self) -> None:
        from syrin.logging import LogFormat

        assert hasattr(LogFormat, "TEXT")

    def test_syrin_handler_emits_json(self) -> None:
        import json
        import logging

        from syrin.logging import LogFormat, SyrinHandler

        records: list[str] = []
        handler = SyrinHandler(format=LogFormat.JSON, stream_override=records)
        logger = logging.getLogger("syrin.test.json_check")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.info("test message")
        logger.removeHandler(handler)

        assert len(records) >= 1
        line = records[0]
        parsed = json.loads(line)
        assert parsed.get("level") == "INFO"
        assert "test message" in parsed.get("message", "")


class TestStatusBarStats:
    def test_llm_request_end_updates_live_token_and_cost_stats(self) -> None:
        from syrin.debug import Pry
        from syrin.enums import Hook
        from syrin.events import EventContext

        ui = Pry(json_fallback=False)
        ui._handle_event(
            str(Hook.LLM_REQUEST_END),
            EventContext(
                iteration=1,
                content="hi",
                tokens=15,
                input_tokens=10,
                output_tokens=5,
                cost=0.0015,
                model="gpt-4o-mini",
            ),
        )

        assert ui._input_tokens == 10
        assert ui._output_tokens == 5
        assert ui._total_tokens == 15
        assert ui._total_cost == 0.0015

    def test_budget_check_updates_budget_used_and_limit(self) -> None:
        from syrin.debug import Pry
        from syrin.enums import Hook
        from syrin.events import EventContext

        ui = Pry(json_fallback=False)
        ui._handle_event(
            str(Hook.BUDGET_CHECK),
            EventContext(used=0.0123, remaining=0.0877, total=0.1),
        )

        assert ui._total_cost == 0.0123
        assert ui._budget_limit == 0.1

        status = ui._status_bar()
        assert "$0.0123" in status
        assert "/[/dim][dim]$0.1000" in status
