"""Exceptions raised by the Workflow system."""

from __future__ import annotations


class WorkflowError(Exception):
    """Base exception for all workflow errors."""


class WorkflowNotRunnable(WorkflowError):
    """Raised when ``run()`` or ``play()`` is called on a workflow with no steps.

    Example::

        wf = Workflow("empty")
        try:
            await wf.run("task")
        except WorkflowNotRunnable:
            print("Add steps with .step(), .parallel(), etc.")
    """


class WorkflowStepError(WorkflowError):
    """Raised when a workflow step raises an unhandled exception.

    Attributes:
        step_index: Zero-based index of the step that failed.
        cause: The underlying exception.

    Example::

        try:
            await wf.run("task")
        except WorkflowStepError as exc:
            print(f"Step {exc.step_index} failed: {exc.cause}")
    """

    def __init__(self, step_index: int, cause: BaseException) -> None:
        """Initialise WorkflowStepError.

        Args:
            step_index: Zero-based index of the failed step.
            cause: The underlying exception that caused the failure.
        """
        self.step_index = step_index
        self.cause = cause
        super().__init__(f"Workflow step {step_index} failed: {cause!r}")


class WorkflowCancelledError(WorkflowError):
    """Raised when ``resume()`` is called after the workflow has been cancelled.

    Example::

        handle = wf.play("task")
        await wf.cancel()
        try:
            await wf.resume()
        except WorkflowCancelledError:
            print("Cannot resume a cancelled workflow")
    """


class DynamicFanoutError(WorkflowError):
    """Raised when a :class:`~syrin.workflow._step.DynamicStep` factory
    returns an invalid number of agents.

    This is raised when:

    - The factory returns zero agents (empty list is invalid).
    - The factory returns more than ``max_agents`` agents.

    Attributes:
        actual: Number of agents the factory returned.
        maximum: The configured ``max_agents`` limit, or ``None`` if the empty
            list case triggered the error.

    Example::

        step = DynamicStep(fn=lambda ctx: [], max_agents=5)
        # Raises DynamicFanoutError: fn returned 0 agents (minimum is 1)
    """

    def __init__(self, actual: int, maximum: int | None = None) -> None:
        """Initialise DynamicFanoutError.

        Args:
            actual: Number of agents returned by the factory.
            maximum: Configured ``max_agents`` limit, or ``None`` for the empty
                list case.
        """
        self.actual = actual
        self.maximum = maximum
        if actual == 0:
            msg = "DynamicStep fn returned 0 agents — minimum is 1."
        else:
            msg = f"DynamicStep fn returned {actual} agents, but max_agents={maximum}."
        super().__init__(msg)
