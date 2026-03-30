"""Public task package facade.

This package exposes the task decorator used to attach task specifications to
agents. Import from ``syrin.task`` for the task decorator and related task-spec
type support.
"""

from syrin.task._core import TaskSpec, task

__all__ = ["task", "TaskSpec"]

_ = TaskSpec
