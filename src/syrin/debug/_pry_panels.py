"""Pry TUI panels — GraphPanel, BudgetPanel, MessagePanel, SwarmNav."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Status symbols (matches plan exit criteria)
# ---------------------------------------------------------------------------

_STATUS_SYMBOL: dict[str, str] = {
    "pending": "⬜",
    "running": "⠸",
    "complete": "✅",
    "failed": "❌",
    "skipped": "⏭",
    "paused": "⏸",
}


def _status_sym(status: str) -> str:
    return _STATUS_SYMBOL.get(status.lower(), "⬜")


# ---------------------------------------------------------------------------
# GraphPanel
# ---------------------------------------------------------------------------


class GraphPanel:
    """Live workflow/swarm graph panel.

    Shows node status (pending/running/complete/failed/skipped/paused)
    and per-agent cost.

    Attributes:
        agent_states: Mapping of agent name → status string.
        agent_costs: Optional mapping of agent name → cost so far.

    Example::

        panel = GraphPanel()
        panel.update("ResearchAgent", "running")
        panel.update("WriterAgent", "complete", cost=0.02)
        text = panel.render_text()
        assert "⠸" in text   # running symbol
        assert "✅" in text   # complete symbol
    """

    def __init__(self) -> None:
        """Initialise an empty GraphPanel."""
        self.agent_states: dict[str, str] = {}
        self.agent_costs: dict[str, float] = {}

    def update(self, agent: str, status: str, cost: float | None = None) -> None:
        """Update an agent's status (and optionally cost).

        Args:
            agent: Agent name.
            status: One of ``pending``, ``running``, ``complete``,
                ``failed``, ``skipped``, or ``paused``.
            cost: Current cost incurred by this agent, if known.
        """
        self.agent_states[agent] = status
        if cost is not None:
            self.agent_costs[agent] = cost

    def render_text(self) -> str:
        """Render graph as a plain-text string (status symbol + agent name + cost).

        Returns:
            Multi-line string with one agent per line.

        Example::

            graph = GraphPanel()
            graph.update("A", "running")
            graph.update("B", "complete", cost=0.01)
            text = graph.render_text()
            # ⠸ A
            # ✅ B  $0.0100
        """
        lines: list[str] = []
        for name, status in self.agent_states.items():
            sym = _status_sym(status)
            cost = self.agent_costs.get(name)
            cost_str = f"  ${cost:.4f}" if cost is not None else ""
            lines.append(f"{sym} {name}{cost_str}")
        return "\n".join(lines)

    def render(self) -> Any:  # type: ignore[explicit-any]
        """Render as Rich ``Text`` object for embedding in a Live layout.

        Returns:
            ``rich.text.Text`` instance.
        """
        try:
            from rich.text import Text  # noqa: PLC0415
        except ImportError:
            return self.render_text()

        t = Text()
        for name, status in self.agent_states.items():
            sym = _status_sym(status)
            cost = self.agent_costs.get(name)
            cost_str = f"  ${cost:.4f}" if cost is not None else ""
            t.append(f"{sym} {name}{cost_str}\n")
        return t


# ---------------------------------------------------------------------------
# BudgetPanel
# ---------------------------------------------------------------------------


@dataclass
class BudgetNode:
    """One node in the hierarchical budget tree.

    Attributes:
        name: Agent or pool name.
        allocated: Budget allocated to this node (USD).
        spent: Amount spent so far (USD).
        children: Child nodes (sub-agents spawned by this agent).
    """

    name: str
    allocated: float
    spent: float
    children: list[BudgetNode] = field(default_factory=list)


class BudgetPanel:
    """Hierarchical budget tree panel.

    Shows pool, per-agent allocated, per-agent spent, and spawned children.

    Attributes:
        root: Root :class:`BudgetNode` of the tree (usually the swarm pool).

    Example::

        root = BudgetNode("pool", allocated=1.00, spent=0.30, children=[
            BudgetNode("ResearchAgent", allocated=0.40, spent=0.15, children=[
                BudgetNode("SubAgent", allocated=0.10, spent=0.05),
            ]),
            BudgetNode("WriterAgent", allocated=0.60, spent=0.15),
        ])
        panel = BudgetPanel(root)
        text = panel.render_text()
        assert "pool" in text
        assert "ResearchAgent" in text
        assert "SubAgent" in text
    """

    def __init__(self, root: BudgetNode | None = None) -> None:
        """Initialise BudgetPanel.

        Args:
            root: Root budget node (optional; set later via :attr:`root`).
        """
        self.root = root

    def render_text(self, node: BudgetNode | None = None, depth: int = 0) -> str:
        """Render the budget tree as indented plain text.

        Args:
            node: Node to render (defaults to :attr:`root`).
            depth: Indentation level.

        Returns:
            Multi-line indented string.

        Example::

            panel = BudgetPanel(root)
            print(panel.render_text())
            # pool  alloc=$1.0000  spent=$0.3000
            #   ResearchAgent  alloc=$0.4000  spent=$0.1500
            #     SubAgent  alloc=$0.1000  spent=$0.0500
            #   WriterAgent  alloc=$0.6000  spent=$0.1500
        """
        if node is None:
            node = self.root
        if node is None:
            return ""
        indent = "  " * depth
        lines = [f"{indent}{node.name}  alloc=${node.allocated:.4f}  spent=${node.spent:.4f}"]
        for child in node.children:
            lines.append(self.render_text(child, depth + 1))
        return "\n".join(lines)

    def render(self) -> Any:  # type: ignore[explicit-any]
        """Render as Rich ``Text`` object for embedding in a Live layout.

        Returns:
            ``rich.text.Text`` instance, or plain string if rich unavailable.
        """
        text = self.render_text()
        try:
            from rich.text import Text  # noqa: PLC0415

            return Text(text)
        except ImportError:
            return text


# ---------------------------------------------------------------------------
# MessagePanel (A2A + MemoryBus timeline)
# ---------------------------------------------------------------------------


@dataclass
class TimelineEvent:
    """One event in the A2A / MemoryBus timeline.

    Attributes:
        ts: Monotonic timestamp (seconds).
        kind: Event kind string (e.g. ``"a2a"`` or ``"membus"``).
        agent: Agent name that produced the event.
        summary: One-line event summary.
    """

    ts: float
    kind: str
    agent: str
    summary: str


class MessagePanel:
    """A2A message timeline + MemoryBus event panel.

    Shows chronological A2A messages and MemoryBus publish/subscribe events.

    Events are stored in a bounded deque (default 200) and always displayed
    in ascending timestamp order.

    Attributes:
        events: Deque of :class:`TimelineEvent` objects.

    Example::

        panel = MessagePanel()
        panel.add_event(TimelineEvent(ts=1.0, kind="a2a", agent="A", summary="Hello B"))
        panel.add_event(TimelineEvent(ts=2.0, kind="membus", agent="B", summary="research.complete"))
        text = panel.render_text()
        assert text.index("Hello B") < text.index("research.complete")
    """

    def __init__(self, maxlen: int = 200) -> None:
        """Initialise MessagePanel.

        Args:
            maxlen: Maximum number of events to retain.
        """
        self.events: deque[TimelineEvent] = deque(maxlen=maxlen)

    def add_event(self, event: TimelineEvent) -> None:
        """Append an event to the timeline.

        Args:
            event: :class:`TimelineEvent` to add.
        """
        self.events.append(event)

    def render_text(self) -> str:
        """Render timeline as plain text in ascending timestamp order.

        Returns:
            Multi-line string; one event per line.

        Example::

            # t=1.000  [a2a]  A → Hello B
            # t=2.000  [membus]  B → research.complete
        """
        sorted_events = sorted(self.events, key=lambda e: e.ts)
        lines = [f"t={e.ts:.3f}  [{e.kind}]  {e.agent} → {e.summary}" for e in sorted_events]
        return "\n".join(lines)

    def render(self) -> Any:  # type: ignore[explicit-any]
        """Render as Rich ``Text`` object.

        Returns:
            ``rich.text.Text`` instance, or plain string if rich unavailable.
        """
        text = self.render_text()
        try:
            from rich.text import Text  # noqa: PLC0415

            return Text(text)
        except ImportError:
            return text


# ---------------------------------------------------------------------------
# SwarmNav — multi-agent keyboard navigation for simultaneous paused agents
# ---------------------------------------------------------------------------


class SwarmNav:
    """Navigation controller for the multi-agent Pry TUI.

    Tracks which agents are currently paused and which one is focused.
    Keyboard shortcuts ``n``/``p`` cycle focus; ``s`` steps the focused agent.

    Attributes:
        paused_agents: Ordered list of paused agent names.
        focused_index: Index into :attr:`paused_agents` for the focused agent.

    Example::

        nav = SwarmNav()
        nav.add_paused("A")
        nav.add_paused("B")
        nav.add_paused("C")
        assert nav.focused_agent() == "A"
        nav.navigate_next()
        assert nav.focused_agent() == "B"
        nav.navigate_prev()
        assert nav.focused_agent() == "A"
    """

    def __init__(self) -> None:
        """Initialise an empty SwarmNav."""
        self.paused_agents: list[str] = []
        self.focused_index: int = 0

    def add_paused(self, agent: str) -> None:
        """Register an agent as paused.

        Args:
            agent: Agent name.
        """
        if agent not in self.paused_agents:
            self.paused_agents.append(agent)

    def remove_paused(self, agent: str) -> None:
        """Unregister an agent (e.g. after it resumes).

        Args:
            agent: Agent name.
        """
        if agent in self.paused_agents:
            idx = self.paused_agents.index(agent)
            self.paused_agents.remove(agent)
            if self.focused_index >= len(self.paused_agents) and self.paused_agents:
                self.focused_index = len(self.paused_agents) - 1
            elif not self.paused_agents:
                self.focused_index = 0
            elif idx < self.focused_index:
                self.focused_index -= 1

    def focused_agent(self) -> str | None:
        """Return the currently focused agent name, or ``None`` if no agents paused.

        Returns:
            Agent name string, or ``None``.
        """
        if not self.paused_agents:
            return None
        return self.paused_agents[self.focused_index]

    def navigate_next(self) -> str | None:
        """Focus the next paused agent (wraps around).

        Returns:
            The newly focused agent name.
        """
        if not self.paused_agents:
            return None
        self.focused_index = (self.focused_index + 1) % len(self.paused_agents)
        return self.focused_agent()

    def navigate_prev(self) -> str | None:
        """Focus the previous paused agent (wraps around).

        Returns:
            The newly focused agent name.
        """
        if not self.paused_agents:
            return None
        self.focused_index = (self.focused_index - 1) % len(self.paused_agents)
        return self.focused_agent()

    def step_focused(self) -> str | None:
        """Return the focused agent name for a step action, then remove it from the paused list.

        The caller is responsible for actually triggering the step.

        Returns:
            The agent name that was stepped, or ``None`` if no agents paused.
        """
        agent = self.focused_agent()
        if agent:
            self.remove_paused(agent)
        return agent


# ---------------------------------------------------------------------------
# Lambda preview for .dynamic() steps
# ---------------------------------------------------------------------------


def preview_dynamic(
    lambda_fn: Callable[[object], object],
    context_content: str,
    max_agents: int | None = None,
) -> list[dict[str, object]]:
    """Execute a `.dynamic()` lambda in preview mode without spawning agents.

    The lambda is called with a minimal :class:`~syrin.workflow._step.HandoffContext`
    built from *context_content*.  The result is returned as a list of dicts
    describing what *would* be spawned.

    Args:
        lambda_fn: The lambda from :meth:`~syrin.workflow.Workflow.dynamic`.
        context_content: The content string to pass as ``ctx.content``.
        max_agents: Optional cap; if ``len(result) > max_agents`` a preview
            note is added but no error is raised (preview is non-destructive).

    Returns:
        List of dicts with ``"task"`` and/or ``"input"`` keys as produced by
        the lambda.

    Example::

        items = preview_dynamic(lambda ctx: [{"task": t} for t in ctx.content.split(",")],
                                "a,b,c")
        assert len(items) == 3
        assert items[0]["task"] == "a"
    """

    # Build a minimal HandoffContext-like object
    class _FakeCtx:
        def __init__(self, content: str) -> None:
            self.content = content
            self.history: list[Any] = []  # type: ignore[explicit-any]
            self.metadata: dict[str, Any] = {}  # type: ignore[explicit-any]

    from typing import cast  # noqa: PLC0415

    ctx = _FakeCtx(context_content)
    raw_result = lambda_fn(ctx)
    if isinstance(raw_result, list):
        result: list[object] = raw_result
    else:
        result = list(cast("Iterable[object]", raw_result))

    preview: list[dict[str, object]] = []
    for item in result:
        if isinstance(item, dict):
            preview.append(item)
        else:
            preview.append({"input": str(item)})

    # Annotate if over cap
    if max_agents is not None and len(preview) > max_agents:
        for entry in preview:
            entry["_preview_over_cap"] = True

    return preview
