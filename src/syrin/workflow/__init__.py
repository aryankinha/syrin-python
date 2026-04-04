"""syrin.workflow — Declarative multi-agent workflow orchestration.

A :class:`Workflow` strings together agents into a typed execution graph with
four step kinds: sequential, parallel, branch, and dynamic.  It supports
lifecycle control (play/pause/resume/cancel), live graph visualisation, and a
complete hook system so every transition is observable.

Quickstart::

    from syrin.workflow import Workflow, HandoffContext
    from syrin import Budget

    wf = (
        Workflow("research-pipeline")
        .step(PlannerAgent)
        .parallel([RedditAgent, HNAgent, ArxivAgent])
        .step(SummarizerAgent)
    )

    result = await wf.run("Summarise AI trends in 2026")
    print(result.content)

Lifecycle control::

    handle = wf.play("Research AI agents")
    await asyncio.sleep(1)
    await wf.pause()
    await wf.resume()
    result = await handle.wait()
"""

from syrin.budget._estimate import EstimationReport
from syrin.enums import PauseMode, WorkflowStatus
from syrin.workflow._context import HandoffContext
from syrin.workflow._core import Workflow
from syrin.workflow._lifecycle import RunHandle
from syrin.workflow._step import (
    BranchStep,
    DynamicStep,
    ParallelStep,
    SequentialStep,
    WorkflowStep,
)
from syrin.workflow.exceptions import (
    DynamicFanoutError,
    WorkflowCancelledError,
    WorkflowError,
    WorkflowNotRunnable,
    WorkflowStepError,
)

__all__ = [
    "EstimationReport",
    "Workflow",
    "HandoffContext",
    "RunHandle",
    "PauseMode",
    "WorkflowStatus",
    "WorkflowStep",
    "SequentialStep",
    "ParallelStep",
    "BranchStep",
    "DynamicStep",
    "WorkflowError",
    "WorkflowNotRunnable",
    "WorkflowStepError",
    "WorkflowCancelledError",
    "DynamicFanoutError",
]
