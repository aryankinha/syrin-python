"""Workflow visualisation utilities.

Provides :func:`visualize`, :func:`to_mermaid`, and :func:`to_dict` for
rendering a workflow's step graph.

Static rendering (before execution)::

    wf.visualize()         # ASCII/rich tree to terminal
    wf.to_mermaid()        # Mermaid diagram string
    wf.to_dict()           # Plain dict with nodes + edges

Live rendering during execution can be enabled with ``show_graph=True`` on
:meth:`~syrin.workflow.Workflow.run`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from syrin.workflow._step import WorkflowStep


def to_dict(steps: list[WorkflowStep]) -> dict[str, object]:
    """Serialise the workflow step graph to a plain dictionary.

    Args:
        steps: Ordered list of :class:`~syrin.workflow._step.WorkflowStep` objects.

    Returns:
        Dict with ``"nodes"`` (list of node dicts) and ``"edges"`` (list of
        edge dicts connecting them in order).

    Example::

        graph = to_dict(wf._steps)
        for node in graph["nodes"]:
            print(node["label"], node["step_type"])
    """
    from syrin.workflow._step import (  # noqa: PLC0415
        BranchStep,
        DynamicStep,
        ParallelStep,
        SequentialStep,
    )

    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []

    for idx, step in enumerate(steps):
        match step:
            case SequentialStep(agent_class=cls, task=task, budget=bgt):
                # cls may be a Workflow instance (duck-typed agent)
                cls_name = getattr(cls, "__name__", None) or getattr(cls, "name", str(cls))
                step_type = "workflow" if hasattr(cls, "_steps") else "sequential"
                node: dict[str, object] = {
                    "id": f"step_{idx}",
                    "label": cls_name,
                    "step_type": step_type,
                    "index": idx,
                }
                if task:
                    node["task"] = task
                if bgt is not None:
                    node["budget"] = bgt.max_cost
                nodes.append(node)

            case ParallelStep(agent_classes=classes, budget=bgt):
                group_id = f"step_{idx}_parallel"
                group_node: dict[str, object] = {
                    "id": group_id,
                    "label": f"parallel({', '.join(c.__name__ for c in classes)})",
                    "step_type": "parallel",
                    "index": idx,
                    "agents": [c.__name__ for c in classes],
                }
                if bgt is not None:
                    group_node["budget"] = bgt.max_cost
                nodes.append(group_node)
                for cls in classes:
                    child_id = f"step_{idx}_{cls.__name__}"
                    nodes.append(
                        {
                            "id": child_id,
                            "label": cls.__name__,
                            "step_type": "parallel_child",
                            "parent": group_id,
                        }
                    )
                    edges.append({"from": group_id, "to": child_id, "type": "parallel"})

            case BranchStep(if_true_class=true_cls, if_false_class=false_cls, budget=bgt):
                branch_id = f"step_{idx}_branch"
                branch_node: dict[str, object] = {
                    "id": branch_id,
                    "label": "◇ branch",
                    "step_type": "branch",
                    "index": idx,
                }
                if bgt is not None:
                    branch_node["budget"] = bgt.max_cost
                nodes.append(branch_node)

                true_id = f"step_{idx}_true"
                false_id = f"step_{idx}_false"
                nodes.append(
                    {"id": true_id, "label": true_cls.__name__, "step_type": "branch_true"}
                )
                nodes.append(
                    {"id": false_id, "label": false_cls.__name__, "step_type": "branch_false"}
                )
                edges.append({"from": branch_id, "to": true_id, "type": "if_true"})
                edges.append({"from": branch_id, "to": false_id, "type": "if_false"})

            case DynamicStep(label=label, max_agents=cap):
                cap_label = str(cap) if cap is not None else "N"
                dyn_node: dict[str, object] = {
                    "id": f"step_{idx}_dynamic",
                    "label": f"◆ {label}(λ)",
                    "step_type": "dynamic",
                    "index": idx,
                    "max_agents": cap_label,
                    "runtime_note": f"{cap_label} agents (runtime)",
                }
                nodes.append(dyn_node)

        # Sequential edge from previous node
        if idx > 0:
            prev_id = _last_output_id(idx - 1, steps)
            curr_id = _first_input_id(idx, steps)
            if prev_id and curr_id:
                edges.append({"from": prev_id, "to": curr_id, "type": "sequential"})

    return {"nodes": nodes, "edges": edges}


def to_mermaid(steps: list[WorkflowStep], direction: str = "TD") -> str:
    """Render the workflow step graph as a Mermaid diagram string.

    Args:
        steps: Ordered list of workflow steps.
        direction: Diagram direction — ``"TD"`` (top-down, default) or
            ``"LR"`` (left-right).

    Returns:
        Mermaid ``graph`` block as a ``str``.  The string starts with
        ``"graph <direction>"`` and uses valid Mermaid syntax.

    Example::

        mermaid = wf.to_mermaid()
        print(mermaid)
        # graph TD
        #     step_0[PlannerAgent]
        #     step_1_parallel{parallel}
        #     ...
    """
    from syrin.workflow._step import (  # noqa: PLC0415
        BranchStep,
        DynamicStep,
        ParallelStep,
        SequentialStep,
    )

    lines = [f"graph {direction}"]

    for idx, step in enumerate(steps):
        match step:
            case SequentialStep(agent_class=cls):
                lines.append(f"    step_{idx}[{cls.__name__}]")
                if idx > 0:
                    prev = _mermaid_output_id(idx - 1, steps)
                    lines.append(f"    {prev} --> step_{idx}")

            case ParallelStep(agent_classes=classes):
                group_id = f"step_{idx}_par"
                lines.append(f"    {group_id}{{parallel}}")
                if idx > 0:
                    prev = _mermaid_output_id(idx - 1, steps)
                    lines.append(f"    {prev} --> {group_id}")
                merge_id = f"step_{idx}_merge"
                lines.append(f"    {merge_id}([merge])")
                for cls in classes:
                    child_id = f"step_{idx}_{cls.__name__}"
                    lines.append(f"    {child_id}[{cls.__name__}]")
                    lines.append(f"    {group_id} --> {child_id}")
                    lines.append(f"    {child_id} --> {merge_id}")

            case BranchStep(if_true_class=true_cls, if_false_class=false_cls):
                branch_id = f"step_{idx}_branch"
                lines.append(f"    {branch_id}{{{{branch}}}}")
                if idx > 0:
                    prev = _mermaid_output_id(idx - 1, steps)
                    lines.append(f"    {prev} --> {branch_id}")
                true_id = f"step_{idx}_true"
                false_id = f"step_{idx}_false"
                merge_id = f"step_{idx}_merge"
                lines.append(f"    {true_id}[{true_cls.__name__}]")
                lines.append(f"    {false_id}[{false_cls.__name__}]")
                lines.append(f"    {merge_id}([merge])")
                lines.append(f"    {branch_id} -->|true| {true_id}")
                lines.append(f"    {branch_id} -->|false| {false_id}")
                lines.append(f"    {true_id} --> {merge_id}")
                lines.append(f"    {false_id} --> {merge_id}")

            case DynamicStep(label=label, max_agents=cap):
                cap_str = str(cap) if cap is not None else "N"
                dyn_id = f"step_{idx}_dynamic"
                lines.append(f"    {dyn_id}[/◆ {label} — {cap_str} agents runtime/]")
                if idx > 0:
                    prev = _mermaid_output_id(idx - 1, steps)
                    lines.append(f"    {prev} --> {dyn_id}")

    return "\n".join(lines)


def visualize(
    steps: list[WorkflowStep],
    name: str = "workflow",
    expand_nested: bool = False,
) -> None:
    """Print a rich ASCII tree of the workflow to stdout.

    Args:
        steps: Ordered list of workflow steps.
        name: Workflow name shown as the tree root.
        expand_nested: When ``True``, sub-workflows are rendered inline with
            their own steps.  When ``False`` (default) they appear as a
            collapsed ``[SubWorkflow]`` block.
    """
    try:
        from rich import print as rprint  # noqa: PLC0415
        from rich.markup import escape as _escape  # noqa: PLC0415
        from rich.tree import Tree  # noqa: PLC0415

        from syrin.workflow._step import (  # noqa: PLC0415
            BranchStep,
            DynamicStep,
            ParallelStep,
            SequentialStep,
        )

        tree = Tree(f"[bold cyan]{name}[/bold cyan]")
        for idx, step in enumerate(steps):
            match step:
                case SequentialStep(agent_class=cls, task=task):
                    # cls may be a Workflow instance (duck-typed nested workflow)
                    cls_name = getattr(cls, "__name__", None) or getattr(cls, "name", str(cls))
                    is_nested_wf = hasattr(cls, "_steps")
                    if is_nested_wf and expand_nested:
                        nested_steps = getattr(cls, "_steps", [])
                        nested_name = str(getattr(cls, "_name", cls_name))
                        sub_branch = tree.add(
                            f"{idx}: [bold cyan]⊞ {_escape(nested_name)}[/bold cyan] [dim](sub-workflow)[/dim]"
                        )
                        for sidx, sub_step in enumerate(nested_steps):
                            match sub_step:
                                case SequentialStep(agent_class=sub_cls, task=sub_task):
                                    sub_label = f"[green]{sub_cls.__name__}[/green]"
                                    if sub_task:
                                        sub_label += f" [dim]task={sub_task!r}[/dim]"
                                    sub_branch.add(f"{sidx}: {sub_label}")
                                case ParallelStep(agent_classes=sub_classes):
                                    sub_par = sub_branch.add(f"{sidx}: [yellow]parallel[/yellow]")
                                    for sc in sub_classes:
                                        sub_par.add(f"[green]{sc.__name__}[/green]")
                                case BranchStep(if_true_class=t, if_false_class=f):
                                    sub_br = sub_branch.add(f"{sidx}: [blue]◇ branch[/blue]")
                                    sub_br.add(f"[green]{t.__name__}[/green] [dim](if true)[/dim]")
                                    sub_br.add(f"[green]{f.__name__}[/green] [dim](if false)[/dim]")
                                case DynamicStep(label=lbl, max_agents=cap):
                                    cap_s = str(cap) if cap is not None else "N"
                                    sub_branch.add(
                                        f"{sidx}: [magenta]◆ {lbl}(λ)[/magenta] [dim]— {cap_s} agents[/dim]"
                                    )
                    elif is_nested_wf:
                        nested_name = str(getattr(cls, "_name", cls_name))
                        tree.add(
                            f"{idx}: [bold cyan]⊞[/bold cyan] [dim]\\[{_escape(nested_name)}][/dim]"
                        )
                    else:
                        label = f"[green]{cls_name}[/green]"
                        if task:
                            label += f" [dim]task={task!r}[/dim]"
                        tree.add(f"{idx}: {label}")

                case ParallelStep(agent_classes=classes):
                    branch = tree.add(f"{idx}: [yellow]parallel[/yellow]")
                    for cls in classes:
                        branch.add(f"[green]{cls.__name__}[/green]")

                case BranchStep(if_true_class=true_cls, if_false_class=false_cls):
                    branch = tree.add(f"{idx}: [blue]◇ branch[/blue]")
                    branch.add(f"[green]{true_cls.__name__}[/green] [dim](if true)[/dim]")
                    branch.add(f"[green]{false_cls.__name__}[/green] [dim](if false)[/dim]")

                case DynamicStep(label=label, max_agents=cap):
                    cap_str = str(cap) if cap is not None else "N"
                    tree.add(
                        f"{idx}: [magenta]◆ {label}(λ)[/magenta] [dim]— {cap_str} agents (runtime)[/dim]"
                    )

        rprint(tree)

    except ImportError:
        # Fallback ASCII when rich is not installed
        print(f"Workflow: {name}")
        for idx, step in enumerate(steps):
            print(f"  {idx}: {type(step).__name__}")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers for building edge IDs
# ──────────────────────────────────────────────────────────────────────────────


def _last_output_id(idx: int, steps: list[WorkflowStep]) -> str | None:
    """Return the output node ID for step at *idx*.

    Args:
        idx: Step index.
        steps: Full step list.

    Returns:
        Node ID string, or ``None`` if unknown.
    """
    from syrin.workflow._step import (  # noqa: PLC0415
        BranchStep,
        DynamicStep,
        ParallelStep,
        SequentialStep,
    )

    step = steps[idx]
    match step:
        case SequentialStep():
            return f"step_{idx}"
        case ParallelStep():
            return f"step_{idx}_parallel"
        case BranchStep():
            return f"step_{idx}_branch"
        case DynamicStep():
            return f"step_{idx}_dynamic"
    return None


def _first_input_id(idx: int, steps: list[WorkflowStep]) -> str | None:
    """Return the input node ID for step at *idx*.

    Args:
        idx: Step index.
        steps: Full step list.

    Returns:
        Node ID string, or ``None`` if unknown.
    """
    from syrin.workflow._step import (  # noqa: PLC0415
        BranchStep,
        DynamicStep,
        ParallelStep,
        SequentialStep,
    )

    step = steps[idx]
    match step:
        case SequentialStep():
            return f"step_{idx}"
        case ParallelStep():
            return f"step_{idx}_parallel"
        case BranchStep():
            return f"step_{idx}_branch"
        case DynamicStep():
            return f"step_{idx}_dynamic"
    return None


def _mermaid_output_id(idx: int, steps: list[WorkflowStep]) -> str:
    """Return the Mermaid node ID that represents the *output* of step *idx*.

    For merge nodes (parallel, branch) returns the merge node ID.  For simple
    sequential or dynamic steps returns the step node ID.

    Args:
        idx: Step index.
        steps: Full step list.

    Returns:
        Mermaid node ID string.
    """
    from syrin.workflow._step import (  # noqa: PLC0415
        BranchStep,
        DynamicStep,
        ParallelStep,
        SequentialStep,
    )

    step = steps[idx]
    match step:
        case SequentialStep():
            return f"step_{idx}"
        case ParallelStep():
            return f"step_{idx}_merge"
        case BranchStep():
            return f"step_{idx}_merge"
        case DynamicStep():
            return f"step_{idx}_dynamic"
    return f"step_{idx}"
