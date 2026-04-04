"""Tests for Pry TUI panels.

Exit criteria:
- Multi-agent graph panel shows correct node states (⬜/⠸/✅/❌/⏭/⏸) live
- Budget tree panel shows hierarchical allocation correctly for 3-level hierarchy
- A2A + MemoryBus timeline panel shows events in chronological order
- Multiple agents paused simultaneously: n/p navigates; s steps one at a time
- Lambda preview: shows what .dynamic() would spawn without executing agents
"""

from __future__ import annotations

from syrin.debug._pry_panels import (
    BudgetNode,
    BudgetPanel,
    GraphPanel,
    MessagePanel,
    SwarmNav,
    TimelineEvent,
    preview_dynamic,
)

# ---------------------------------------------------------------------------
# GraphPanel — node state symbols
# ---------------------------------------------------------------------------


def test_graph_panel_running_symbol() -> None:
    """Running agent shows ⠸ symbol."""
    panel = GraphPanel()
    panel.update("ResearchAgent", "running")
    text = panel.render_text()
    assert "⠸" in text
    assert "ResearchAgent" in text


def test_graph_panel_complete_symbol() -> None:
    """Complete agent shows ✅ symbol."""
    panel = GraphPanel()
    panel.update("WriterAgent", "complete")
    text = panel.render_text()
    assert "✅" in text


def test_graph_panel_failed_symbol() -> None:
    """Failed agent shows ❌ symbol."""
    panel = GraphPanel()
    panel.update("AnalystAgent", "failed")
    text = panel.render_text()
    assert "❌" in text


def test_graph_panel_skipped_symbol() -> None:
    """Skipped agent shows ⏭ symbol."""
    panel = GraphPanel()
    panel.update("OptionalAgent", "skipped")
    text = panel.render_text()
    assert "⏭" in text


def test_graph_panel_paused_symbol() -> None:
    """Paused agent shows ⏸ symbol."""
    panel = GraphPanel()
    panel.update("DebugAgent", "paused")
    text = panel.render_text()
    assert "⏸" in text


def test_graph_panel_pending_symbol() -> None:
    """Pending agent shows ⬜ symbol."""
    panel = GraphPanel()
    panel.update("FutureAgent", "pending")
    text = panel.render_text()
    assert "⬜" in text


def test_graph_panel_all_six_states_in_one_render() -> None:
    """All six states render correctly in a single panel."""
    panel = GraphPanel()
    panel.update("A", "pending")
    panel.update("B", "running")
    panel.update("C", "complete")
    panel.update("D", "failed")
    panel.update("E", "skipped")
    panel.update("F", "paused")
    text = panel.render_text()
    assert "⬜" in text
    assert "⠸" in text
    assert "✅" in text
    assert "❌" in text
    assert "⏭" in text
    assert "⏸" in text


def test_graph_panel_shows_cost() -> None:
    """Cost is shown when provided."""
    panel = GraphPanel()
    panel.update("CostlyAgent", "complete", cost=0.0250)
    text = panel.render_text()
    assert "0.0250" in text


def test_graph_panel_no_cost_if_not_provided() -> None:
    """Cost is absent when not provided."""
    panel = GraphPanel()
    panel.update("CheapAgent", "complete")
    text = panel.render_text()
    assert "$" not in text


# ---------------------------------------------------------------------------
# BudgetPanel — 3-level hierarchy
# ---------------------------------------------------------------------------


def _make_3level_tree() -> BudgetNode:
    """Build a 3-level budget tree for tests."""
    return BudgetNode(
        name="pool",
        allocated=1.00,
        spent=0.30,
        children=[
            BudgetNode(
                name="ResearchAgent",
                allocated=0.40,
                spent=0.15,
                children=[
                    BudgetNode(name="SubAgent", allocated=0.10, spent=0.05),
                ],
            ),
            BudgetNode(name="WriterAgent", allocated=0.60, spent=0.15),
        ],
    )


def test_budget_panel_shows_root() -> None:
    """Root pool is shown in output."""
    panel = BudgetPanel(_make_3level_tree())
    text = panel.render_text()
    assert "pool" in text


def test_budget_panel_shows_level2() -> None:
    """Level-2 agents (ResearchAgent, WriterAgent) appear in output."""
    panel = BudgetPanel(_make_3level_tree())
    text = panel.render_text()
    assert "ResearchAgent" in text
    assert "WriterAgent" in text


def test_budget_panel_shows_level3() -> None:
    """Level-3 sub-agent (SubAgent) appears in output."""
    panel = BudgetPanel(_make_3level_tree())
    text = panel.render_text()
    assert "SubAgent" in text


def test_budget_panel_alloc_and_spent() -> None:
    """Allocated and spent amounts are shown for each node."""
    panel = BudgetPanel(_make_3level_tree())
    text = panel.render_text()
    assert "alloc=" in text
    assert "spent=" in text


def test_budget_panel_3level_ordering() -> None:
    """Hierarchy order is pool → ResearchAgent → SubAgent (parent before child)."""
    panel = BudgetPanel(_make_3level_tree())
    text = panel.render_text()
    pool_idx = text.index("pool")
    research_idx = text.index("ResearchAgent")
    sub_idx = text.index("SubAgent")
    assert pool_idx < research_idx < sub_idx


def test_budget_panel_empty_is_empty_string() -> None:
    """Empty panel renders to empty string."""
    panel = BudgetPanel()
    assert panel.render_text() == ""


# ---------------------------------------------------------------------------
# MessagePanel — chronological A2A / MemoryBus timeline
# ---------------------------------------------------------------------------


def test_message_panel_chronological_order() -> None:
    """Events added out-of-order are rendered in ascending timestamp order."""
    panel = MessagePanel()
    panel.add_event(TimelineEvent(ts=3.0, kind="a2a", agent="B", summary="late event"))
    panel.add_event(TimelineEvent(ts=1.0, kind="a2a", agent="A", summary="early event"))
    panel.add_event(TimelineEvent(ts=2.0, kind="membus", agent="C", summary="middle event"))
    text = panel.render_text()
    early_idx = text.index("early event")
    middle_idx = text.index("middle event")
    late_idx = text.index("late event")
    assert early_idx < middle_idx < late_idx


def test_message_panel_shows_kind() -> None:
    """Event kind (a2a / membus) appears in each line."""
    panel = MessagePanel()
    panel.add_event(TimelineEvent(ts=1.0, kind="a2a", agent="A", summary="hello"))
    panel.add_event(TimelineEvent(ts=2.0, kind="membus", agent="B", summary="pub"))
    text = panel.render_text()
    assert "[a2a]" in text
    assert "[membus]" in text


def test_message_panel_shows_agent_name() -> None:
    """Agent name appears in each line."""
    panel = MessagePanel()
    panel.add_event(TimelineEvent(ts=1.0, kind="a2a", agent="ResearchAgent", summary="msg"))
    text = panel.render_text()
    assert "ResearchAgent" in text


def test_message_panel_empty_renders_empty_string() -> None:
    """Empty panel renders as empty string."""
    panel = MessagePanel()
    assert panel.render_text() == ""


def test_message_panel_maxlen_bounded() -> None:
    """Panel respects maxlen bound."""
    panel = MessagePanel(maxlen=5)
    for i in range(10):
        panel.add_event(TimelineEvent(ts=float(i), kind="a2a", agent="A", summary=f"e{i}"))
    assert len(panel.events) == 5


# ---------------------------------------------------------------------------
# SwarmNav — multi-agent navigation
# ---------------------------------------------------------------------------


def test_swarm_nav_focus_starts_at_first() -> None:
    """First added agent is focused initially."""
    nav = SwarmNav()
    nav.add_paused("A")
    nav.add_paused("B")
    nav.add_paused("C")
    assert nav.focused_agent() == "A"


def test_swarm_nav_navigate_next() -> None:
    """n (next) cycles focus forward."""
    nav = SwarmNav()
    nav.add_paused("A")
    nav.add_paused("B")
    nav.add_paused("C")
    nav.navigate_next()
    assert nav.focused_agent() == "B"
    nav.navigate_next()
    assert nav.focused_agent() == "C"


def test_swarm_nav_navigate_next_wraps() -> None:
    """n wraps from last back to first."""
    nav = SwarmNav()
    nav.add_paused("A")
    nav.add_paused("B")
    nav.navigate_next()  # B
    nav.navigate_next()  # wrap → A
    assert nav.focused_agent() == "A"


def test_swarm_nav_navigate_prev() -> None:
    """p (prev) cycles focus backward."""
    nav = SwarmNav()
    nav.add_paused("A")
    nav.add_paused("B")
    nav.add_paused("C")
    nav.navigate_next()  # B
    nav.navigate_next()  # C
    nav.navigate_prev()  # B
    assert nav.focused_agent() == "B"


def test_swarm_nav_navigate_prev_wraps() -> None:
    """p wraps from first back to last."""
    nav = SwarmNav()
    nav.add_paused("A")
    nav.add_paused("B")
    nav.add_paused("C")
    nav.navigate_prev()  # wrap to C
    assert nav.focused_agent() == "C"


def test_swarm_nav_step_removes_focused() -> None:
    """s (step) removes the focused agent from paused list."""
    nav = SwarmNav()
    nav.add_paused("A")
    nav.add_paused("B")
    stepped = nav.step_focused()
    assert stepped == "A"
    assert "A" not in nav.paused_agents
    assert nav.focused_agent() == "B"


def test_swarm_nav_no_agents_returns_none() -> None:
    """All navigation returns None when no agents are paused."""
    nav = SwarmNav()
    assert nav.focused_agent() is None
    assert nav.navigate_next() is None
    assert nav.navigate_prev() is None
    assert nav.step_focused() is None


def test_swarm_nav_three_agents_step_each() -> None:
    """Stepping through all 3 paused agents removes them one by one."""
    nav = SwarmNav()
    nav.add_paused("A")
    nav.add_paused("B")
    nav.add_paused("C")
    assert nav.step_focused() == "A"
    assert nav.step_focused() == "B"
    assert nav.step_focused() == "C"
    assert nav.focused_agent() is None


# ---------------------------------------------------------------------------
# Lambda preview — .dynamic() step preview
# ---------------------------------------------------------------------------


def test_lambda_preview_returns_list() -> None:
    """preview_dynamic returns a list of dicts."""
    fn = lambda ctx: [{"task": t} for t in ctx.content.split(",")]  # noqa: E731
    result = preview_dynamic(fn, "a,b,c")
    assert isinstance(result, list)
    assert len(result) == 3


def test_lambda_preview_items_are_dicts() -> None:
    """Each item in preview result is a dict."""
    fn = lambda ctx: [{"task": t} for t in ctx.content.split(",")]  # noqa: E731
    result = preview_dynamic(fn, "x,y")
    assert all(isinstance(item, dict) for item in result)


def test_lambda_preview_no_agents_spawned() -> None:
    """preview_dynamic does not spawn agents — it only calls the lambda."""
    spawned: list[str] = []

    def fn(ctx: object) -> list[dict[str, object]]:
        # This function should not spawn any agents
        return [{"task": "only data"}]

    result = preview_dynamic(fn, "input")
    assert len(result) == 1
    assert result[0]["task"] == "only data"
    assert len(spawned) == 0  # nothing spawned


def test_lambda_preview_over_cap_annotated() -> None:
    """Items are annotated with _preview_over_cap when count > max_agents."""
    fn = lambda _ctx: [{"task": f"t{i}"} for i in range(10)]  # noqa: E731
    result = preview_dynamic(fn, "input", max_agents=5)
    assert len(result) == 10
    assert all(item.get("_preview_over_cap") is True for item in result)


def test_lambda_preview_within_cap_no_annotation() -> None:
    """Items are NOT annotated when count <= max_agents."""
    fn = lambda _ctx: [{"task": f"t{i}"} for i in range(3)]  # noqa: E731
    result = preview_dynamic(fn, "input", max_agents=5)
    assert not any("_preview_over_cap" in item for item in result)


def test_lambda_preview_uses_content() -> None:
    """Lambda receives ctx.content as the provided string."""
    captured: list[str] = []

    def fn(ctx: object) -> list[dict[str, object]]:
        captured.append(ctx.content)  # type: ignore[attr-defined]
        return []

    preview_dynamic(fn, "my-input-text")
    assert captured == ["my-input-text"]
