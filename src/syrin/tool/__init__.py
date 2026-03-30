"""Public tool package facade.

This package exposes the tool decorator and tool specification type used by
agents for callable tool integrations. Import from ``syrin.tool`` for the
end-user tool authoring API.
"""

from syrin.tool._core import ToolSpec, tool

__all__ = ["tool", "ToolSpec"]
