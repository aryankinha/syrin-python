"""Tests for Pry multi-agent nesting and event filter modes."""

from __future__ import annotations

# ─── Multi-agent nesting ───────────────────────────────────────────────────────


class TestMultiAgentNesting:
    def test_attach_multiple_agents(self) -> None:
        """Pry can attach to more than one agent."""
        from syrin.agent import Agent
        from syrin.debug import Pry
        from syrin.model import Model

        a1 = Agent(model=Model.Anthropic("claude-sonnet-4-6"), name="Parent")
        a2 = Agent(model=Model.Anthropic("claude-sonnet-4-6"), name="Child")
        ui = Pry(json_fallback=True)
        ui.attach(a1)
        ui.attach(a2)
        assert len(ui._agents) == 2

    def test_attach_returns_self_for_chaining(self) -> None:
        """attach() returns self so calls can be chained."""
        from syrin.agent import Agent
        from syrin.debug import Pry
        from syrin.model import Model

        agent = Agent(model=Model.Anthropic("claude-sonnet-4-6"))
        ui = Pry(json_fallback=True)
        result = ui.attach(agent)
        assert result is ui

    def test_nested_agent_events_captured(self) -> None:
        """Events from a second (nested) agent are captured by the UI."""
        import json

        from syrin.agent import Agent
        from syrin.debug import Pry
        from syrin.enums import Hook
        from syrin.events import EventContext
        from syrin.model import Model

        captured: list[str] = []
        ui = Pry(json_fallback=True, stream_override=captured)

        a1 = Agent(model=Model.Anthropic("claude-sonnet-4-6"), name="Parent")
        a2 = Agent(model=Model.Anthropic("claude-sonnet-4-6"), name="Child")
        ui.attach(a1)
        ui.attach(a2)

        # Fire events on both agents via the UI directly
        ui._handle_event(str(Hook.AGENT_RUN_START), EventContext(agent="Parent"))
        ui._handle_event(str(Hook.AGENT_RUN_START), EventContext(agent="Child"))

        assert len(captured) == 2
        for line in captured:
            data = json.loads(line)
            assert "event" in data

    def test_detach_clears_all_agents(self) -> None:
        """detach() removes all agents from the UI."""
        from syrin.agent import Agent
        from syrin.debug import Pry
        from syrin.model import Model

        a1 = Agent(model=Model.Anthropic("claude-sonnet-4-6"))
        a2 = Agent(model=Model.Anthropic("claude-sonnet-4-6"))
        ui = Pry(json_fallback=True)
        ui.attach(a1)
        ui.attach(a2)
        ui.detach()
        assert len(ui._agents) == 0

    def test_nested_json_includes_agent_label(self) -> None:
        """When json_fallback and stream_override set, nested events include agent label."""
        import json

        from syrin.debug import Pry
        from syrin.enums import Hook
        from syrin.events import EventContext

        captured: list[str] = []
        ui = Pry(json_fallback=True, stream_override=captured)
        ui._handle_event(
            str(Hook.SPAWN_START),
            EventContext(parent="Parent", child="Child"),
        )
        assert len(captured) == 1
        data = json.loads(captured[0])
        assert "event" in data

    def test_second_tui_replaces_first_active_session(self, monkeypatch: object) -> None:
        import syrin.debug._ui as ui_mod
        from syrin.debug import Pry

        def _fake_start_rich(self: Pry) -> None:
            self._live = object()

        monkeypatch.setattr(Pry, "_start_rich", _fake_start_rich)

        first = Pry(json_fallback=False)
        second = Pry(json_fallback=False)

        first.start()
        assert ui_mod._ACTIVE_PRY is first

        second.start()

        assert not first._started
        assert ui_mod._ACTIVE_PRY is second
        second.stop()


# ─── Keyboard filter modes ─────────────────────────────────────────────────────


class TestFilterModes:
    def test_syrindebuiui_has_filter_mode(self) -> None:
        """Pry exposes a filter_mode attribute."""
        from syrin.debug import Pry

        ui = Pry(json_fallback=True)
        assert hasattr(ui, "filter_mode")

    def test_default_filter_mode_is_all(self) -> None:
        """Default filter_mode is 'all' (show everything)."""
        from syrin.debug import Pry

        ui = Pry(json_fallback=True)
        assert ui.filter_mode == "all"

    def test_set_filter_mode_errors(self) -> None:
        """set_filter('errors') changes filter_mode to 'errors'."""
        from syrin.debug import Pry

        ui = Pry(json_fallback=True)
        ui.set_filter("errors")
        assert ui.filter_mode == "errors"

    def test_set_filter_mode_tools(self) -> None:
        """set_filter('tools') changes filter_mode to 'tools'."""
        from syrin.debug import Pry

        ui = Pry(json_fallback=True)
        ui.set_filter("tools")
        assert ui.filter_mode == "tools"

    def test_set_filter_mode_memory(self) -> None:
        """set_filter('memory') changes filter_mode to 'memory'."""
        from syrin.debug import Pry

        ui = Pry(json_fallback=True)
        ui.set_filter("memory")
        assert ui.filter_mode == "memory"

    def test_set_filter_mode_all(self) -> None:
        """set_filter('all') resets filter_mode to 'all'."""
        from syrin.debug import Pry

        ui = Pry(json_fallback=True)
        ui.set_filter("tools")
        ui.set_filter("all")
        assert ui.filter_mode == "all"

    def test_filter_suppresses_non_matching_events(self) -> None:
        """In 'errors' mode, tool events are not emitted."""
        from syrin.debug import Pry
        from syrin.enums import Hook
        from syrin.events import EventContext

        captured: list[str] = []
        ui = Pry(json_fallback=True, stream_override=captured)
        ui.set_filter("errors")

        # Tool call start — should be filtered out
        ui._handle_event(str(Hook.TOOL_CALL_START), EventContext())
        # Error — should pass through
        ui._handle_event(str(Hook.TOOL_ERROR), EventContext())

        assert len(captured) == 1

    def test_filter_passes_matching_events(self) -> None:
        """In 'tools' mode, tool events pass through."""
        import json

        from syrin.debug import Pry
        from syrin.enums import Hook
        from syrin.events import EventContext

        captured: list[str] = []
        ui = Pry(json_fallback=True, stream_override=captured)
        ui.set_filter("tools")

        ui._handle_event(str(Hook.TOOL_CALL_START), EventContext())
        ui._handle_event(str(Hook.TOOL_CALL_END), EventContext())

        assert len(captured) == 2
        for line in captured:
            data = json.loads(line)
            assert "tool" in data["event"].lower()

    def test_pause_stops_event_emission(self) -> None:
        """pause() stops event emission; resume() re-enables it."""
        from syrin.debug import Pry
        from syrin.enums import Hook
        from syrin.events import EventContext

        captured: list[str] = []
        ui = Pry(json_fallback=True, stream_override=captured)

        ui.pause()
        ui._handle_event(str(Hook.AGENT_RUN_START), EventContext())
        assert len(captured) == 0

        ui.resume()
        ui._handle_event(str(Hook.AGENT_RUN_END), EventContext())
        assert len(captured) == 1

    def test_constructor_accepts_filter_mode(self) -> None:
        """Pry(filter_mode='errors') sets filter on construction."""
        from syrin.debug import Pry

        ui = Pry(json_fallback=True, filter_mode="errors")
        assert ui.filter_mode == "errors"


class TestDetailNavigation:
    def test_escape_exits_stream_detail_mode(self) -> None:
        from syrin.debug import Pry
        from syrin.enums import Hook
        from syrin.events import EventContext

        ui = Pry(json_fallback=False)
        ui._handle_event(str(Hook.AGENT_RUN_START), EventContext(input="hello", model="test-model"))
        ui._handle_key("\r")

        assert ui._mode == "detail"

        ui._handle_key("\x1b")

        assert ui._mode == "browse"

    def test_escape_exits_right_detail_mode(self) -> None:
        from syrin.debug import Pry
        from syrin.enums import Hook
        from syrin.events import EventContext

        ui = Pry(json_fallback=False)
        ui._handle_event(
            str(Hook.TOOL_CALL_START), EventContext(name="search", arguments='{"q":"x"}')
        )
        ui._right_view = "tools"
        ui._focus = "right"
        ui._handle_key("\r")

        assert ui._mode == "right_detail"

        ui._handle_key("\x1b")

        assert ui._mode == "browse"
        assert ui._right_detail_rec is None

    def test_up_down_scroll_right_event_preview(self) -> None:
        from syrin.debug import Pry
        from syrin.enums import Hook
        from syrin.events import EventContext

        ui = Pry(json_fallback=False)
        ui._handle_event(
            str(Hook.LLM_REQUEST_END),
            EventContext(
                iteration=1,
                content="\n".join(f"line {i}" for i in range(30)),
                tokens=30,
                input_tokens=10,
                output_tokens=20,
                cost=0.01,
                model="test-model",
            ),
        )
        ui._focus = "right"
        ui._right_view = "event"

        assert ui._right_preview_scroll == 0

        ui._handle_key("\x1b[A")
        assert ui._right_preview_scroll > 0

        ui._handle_key("\x1b[B")
        assert ui._right_preview_scroll == 0
